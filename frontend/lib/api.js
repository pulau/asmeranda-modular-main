/**
 * API client untuk Asmeranda backend.
 *
 * - Pakai fetch() native (no axios dependency)
 * - Base path "/api" akan di-rewrite ke backend oleh next.config.js
 * - Untuk upload file, gunakan `apiUpload` (FormData)
 * - Untuk endpoint biasa, gunakan `apiFetch`
 * - Otomatis menyertakan Authorization Bearer header jika token tersedia
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_PATH || "/api/v1";
const TOKEN_KEY = "asmeranda_auth_token";

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export function getAuthToken() {
  if (typeof window !== "undefined") {
    return localStorage.getItem(TOKEN_KEY);
  }
  return null;
}

export function setAuthToken(token) {
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }
}

function getAuthHeaders() {
  const token = getAuthToken();
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function apiFetch(path, options = {}) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
    ...options,
  });
  const text = await res.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }
  if (!res.ok) {
    const detail =
      (payload && (payload.detail || payload.message)) || res.statusText;
    throw new ApiError(detail || "Request gagal", res.status, payload);
  }
  return payload;
}

export async function apiUpload(path, formData, onProgress) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const authHeaders = getAuthHeaders();

  if (typeof onProgress !== "function") {
    const res = await fetch(url, {
      method: "POST",
      body: formData,
      credentials: "include",
      headers: {
        ...authHeaders,
      },
    });
    if (!res.ok) {
      const text = await res.text();
      let payload = null;
      try {
        payload = JSON.parse(text);
      } catch {
        payload = text;
      }
      throw new ApiError(
        (payload && (payload.detail || payload.error)) || res.statusText,
        res.status,
        payload
      );
    }
    return res.json();
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.withCredentials = true;
    for (const [key, value] of Object.entries(authHeaders)) {
      xhr.setRequestHeader(key, value);
    }
    xhr.upload.onprogress = (evt) => {
      if (evt.lengthComputable) {
        onProgress(Math.round((evt.loaded / evt.total) * 100));
      }
    };
    xhr.onload = () => {
      let payload = null;
      try {
        payload = JSON.parse(xhr.responseText);
      } catch {
        payload = xhr.responseText;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress(100);
        resolve(payload);
      } else {
        reject(
          new ApiError(
            (payload && (payload.detail || payload.error)) || xhr.statusText,
            xhr.status,
            payload
          )
        );
      }
    };
    xhr.onerror = () => reject(new ApiError("Network error", 0, null));
    xhr.send(formData);
  });
}

export const api = {
  // Health — endpoint di root (/health), bukan di /api/v1/health
  health: () => fetch("/health").then((r) => r.json()),
  
  // Auth
  auth: {
    login: async (username, password) => {
      const res = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      if (res && res.access_token) {
        setAuthToken(res.access_token);
      }
      return res;
    },
    register: (userData) =>
      apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify(userData),
      }),
    me: () => apiFetch("/auth/me"),
    logout: () => {
      setAuthToken(null);
    },
    getToken: getAuthToken,
    setToken: setAuthToken,
  },

  // Datasets
  listDatasets: () => apiFetch("/datasets"),
  getDataset: (id) => apiFetch(`/datasets/${id}`),
  uploadDataset: (file, onProgress) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiUpload("/datasets", fd, onProgress);
  },
  deleteDataset: (id) =>
    apiFetch(`/datasets/${id}`, { method: "DELETE" }),
  
  // EDA
  edaSummary: (id) => apiFetch(`/eda/${id}/summary`),
  edaCorrelation: (id, columns = "") =>
    apiFetch(
      `/eda/${id}/correlation${columns ? `?columns=${columns}` : ""}`
    ),
  edaPaginatedData: (id, page = 1, size = 50) =>
    apiFetch(`/eda/${id}/data?page=${page}&size=${size}`),
  
  // WebSocket — koneksi langsung ke backend (Next.js tidak bisa proxy WS)
  connectWebSocket: (id, onMessage) => {
    const backendHttp = process.env.NEXT_PUBLIC_API_BASE || 
      (typeof window !== "undefined" 
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : "http://localhost:8000");
    
    const wsUrl = backendHttp
      .replace(/^https:/, "wss:")
      .replace(/^http:/, "ws:") + `/api/v1/ws/${id}`;
    
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (err) {
        console.error("WS Parse Error:", err);
      }
    };
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 30000);
    ws.addEventListener("close", () => clearInterval(pingInterval));
    return ws;
  },
  
  // Preprocessing
  runPreprocessing: (config) =>
    apiFetch("/preprocessing/run", { method: "POST", body: JSON.stringify(config) }),
  
  // Training
  startTraining: (config) =>
    apiFetch("/training/start", { method: "POST", body: JSON.stringify(config) }),
  listModels: () => apiFetch("/training/models"),
  getModel: (id) => apiFetch(`/training/models/${id}`),
  deleteModel: (id) =>
    apiFetch(`/training/models/${id}`, { method: "DELETE" }),
  evaluateModel: (config) =>
    apiFetch("/training/evaluate", { method: "POST", body: JSON.stringify(config) }),
  predictWithModel: (id, data) =>
    apiFetch(`/training/models/${id}/predict`, { 
      method: "POST", 
      body: JSON.stringify({ data }) 
    }),
  downloadModel: (id) => {
    const API_BASE = process.env.NEXT_PUBLIC_API_BASE_PATH || "/api/v1";
    window.open(`${API_BASE}/training/models/${id}/download`, '_blank');
  },
  
  // Clustering (using preprocessing endpoints)
  performClustering: (config) =>
    apiFetch("/preprocessing/cluster", { method: "POST", body: JSON.stringify(config) }),
  findOptimalK: (config) =>
    apiFetch("/preprocessing/optimal-k", { method: "POST", body: JSON.stringify(config) }),
  
  // Optimization (using training endpoints)
  optimizeHyperparameters: (config) =>
    apiFetch("/training/optimize", { method: "POST", body: JSON.stringify(config) }),
  optimizeHyperparametersSync: (config) =>
    apiFetch("/training/optimize-sync", { method: "POST", body: JSON.stringify(config) }),
  
  // Recommendations (using eda endpoints)
  analyzeDataset: (config) =>
    apiFetch("/eda/analyze", { method: "POST", body: JSON.stringify(config) }),
  
  // Interpretation
  runShap: (payload) =>
    apiFetch("/interpretation/shap", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runLime: (payload) =>
    apiFetch("/interpretation/lime", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  
  // Timeseries
  tsDetect: (id, target, date) =>
    apiFetch(
      `/timeseries/${id}/detect?${new URLSearchParams({
        ...(target ? { target_column: target } : {}),
        ...(date ? { date_column: date } : {}),
      }).toString()}`
    ),
  tsForecast: (id, target, horizon = 10, method = "naive") =>
    apiFetch(
      `/timeseries/${id}/forecast?${new URLSearchParams({
        target_column: target,
        horizon: String(horizon),
        method,
      }).toString()}`
    ),
  tsAnomalies: (id, target, contamination = 0.05) =>
    apiFetch(
      `/timeseries/${id}/anomalies?${new URLSearchParams({
        target_column: target,
        contamination: String(contamination),
      }).toString()}`
    ),
};
