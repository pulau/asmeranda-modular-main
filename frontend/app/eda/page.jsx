"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

export default function EdaPage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const datasetId = useWorkflow((s) => s.datasetId);
  const [summary, setSummary] = useState(null);
  const [corr, setCorr] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("summary");
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [recommendations, setRecommendations] = useState(null);

  // Raw Data Pagination State
  const [rawData, setRawData] = useState(null);
  const [dataPage, setDataPage] = useState(1);
  const [dataSize, setDataSize] = useState(10);
  const [dataLoading, setDataLoading] = useState(false);

  // WebSocket Progress State
  const [wsProgress, setWsProgress] = useState(null);
  const [wsStatus, setWsStatus] = useState("disconnected");

  useEffect(() => {
    if (!datasetId) return;
    
    // Connect WebSocket
    const ws = api.connectWebSocket(datasetId, (msg) => {
      if (msg.progress !== undefined) {
        setWsProgress(msg.progress);
      }
    });
    
    ws.onopen = () => setWsStatus("connected");
    ws.onclose = () => setWsStatus("disconnected");

    (async () => {
      try {
        const s = await api.edaSummary(datasetId);
        if (!s.success) throw new Error(s.error);
        setSummary(s);
        const c = await api.edaCorrelation(datasetId);
        if (c.success) setCorr(c);
      } catch (e) {
        setError(e.message);
      }
    })();

    return () => {
      ws.close();
    };
  }, [datasetId]);

  async function fetchRecommendations() {
    try {
      const r = await api.analyzeDataset({ dataset_id: datasetId });
      if (r.success) {
        setRecommendations(r);
        setShowRecommendations(true);
      }
    } catch (e) {
      console.error("Failed to fetch recommendations:", e);
    }
  }

  // Load paginated data when tab switches to "data" or page changes
  useEffect(() => {
    if (tab === "data" && datasetId) {
      setDataLoading(true);
      api.edaPaginatedData(datasetId, dataPage, dataSize)
        .then((res) => {
          if (res.success) setRawData(res);
          else setError(res.error);
        })
        .catch((err) => setError(err.message))
        .finally(() => setDataLoading(false));
    }
  }, [tab, datasetId, dataPage, dataSize]);

  if (!datasetId) {
    return (
      <div>
        <h1>{tr("eda.title")}</h1>
        <p style={{ color: "#dc2626" }}>⚠ Unggah dataset dulu di halaman Data Upload.</p>
      </div>
    );
  }

  return (
    <div>
      <h1>{tr("eda.title")}</h1>
      <p style={{ color: "#64748b" }}>
        Dataset: <code>{datasetId}</code>
      </p>

      {error && (
        <div style={{ padding: 12, background: "#fee2e2", color: "#991b1b", borderRadius: 6 }}>
          {error}
        </div>
      )}

      <button
        onClick={fetchRecommendations}
        style={{
          marginTop: 12,
          padding: "8px 16px",
          background: "#7c3aed",
          color: "#fff",
          border: "none",
          borderRadius: 4,
        }}
      >
        Get AI Recommendations
      </button>

      {showRecommendations && recommendations && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#f0fdf4",
            borderRadius: 6,
            border: "1px solid #16a34a",
          }}
        >
          <h3>AI Recommendations</h3>
          {recommendations.recommendations && recommendations.recommendations.map((rec, i) => (
            <div
              key={i}
              style={{
                marginTop: 8,
                padding: 8,
                background:
                  rec.type === "warning"
                    ? "#fef3c7"
                    : rec.type === "info"
                    ? "#dbeafe"
                    : "#dcfce7",
                borderRadius: 4,
              }}
            >
              <strong>{rec.title}</strong>
              <p style={{ margin: "4px 0 0 0" }}>{rec.description}</p>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
        {["summary", "correlation", "missing", "data"].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "6px 14px",
              background: tab === t ? "#1e40af" : "#e2e8f0",
              color: tab === t ? "#fff" : "#0f172a",
              border: "none",
              borderRadius: 4,
            }}
          >
            {tr(`eda.${t}`)}
          </button>
        ))}
      </div>

      <div style={{ marginTop: 16, background: "#fff", padding: 20, borderRadius: 8 }}>
        {tab === "summary" && summary && (
          <div>
            <p>
              <strong>Shape:</strong> {summary.shape.rows} rows × {summary.shape.columns} columns
            </p>
            <h3>Numerical describe</h3>
            {summary.describe_numeric && Object.keys(summary.describe_numeric).length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Stat</th>
                    {Object.keys(summary.describe_numeric).map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {["count", "mean", "std", "min", "25%", "50%", "75%", "max"].map(
                    (stat) => (
                      <tr key={stat}>
                        <td>
                          <strong>{stat}</strong>
                        </td>
                        {Object.keys(summary.describe_numeric).map((col) => (
                          <td key={col}>
                            {summary.describe_numeric[col][stat] != null
                              ? Number(summary.describe_numeric[col][stat]).toFixed(3)
                              : "-"}
                          </td>
                        ))}
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            ) : (
              <p>No numerical columns.</p>
            )}
          </div>
        )}

        {tab === "correlation" && corr && (
          <div>
            {corr.matrix && corr.columns ? (
              <table>
                <thead>
                  <tr>
                    <th></th>
                    {corr.columns.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {corr.matrix.map((row, i) => (
                    <tr key={i}>
                      <td>
                        <strong>{corr.columns[i]}</strong>
                      </td>
                      {row.map((v, j) => (
                        <td
                          key={j}
                          style={{
                            background: `rgba(59, 130, 246, ${Math.abs(v)})`,
                            color: Math.abs(v) > 0.5 ? "#fff" : "#0f172a",
                          }}
                        >
                          {Number(v).toFixed(2)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>No correlation data.</p>
            )}
          </div>
        )}

        {tab === "missing" && summary && (
          <div>
            <table>
              <thead>
                <tr>
                  <th>Column</th>
                  <th>Missing Count</th>
                  <th>%</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(summary.missing?.counts || {}).map(([col, c]) => (
                  <tr key={col}>
                    <td>{col}</td>
                    <td>{c}</td>
                    <td>{Number(summary.missing.percentages[col] || 0).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === "data" && (
          <div>
            <div className="flex-between mb-4">
              <h3>Raw Data Viewer (Polars Engine)</h3>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: "var(--text-sm)", color: "var(--color-slate-500)" }}>
                  WS: {wsStatus === "connected" ? "🟢 Connected" : "🔴 Disconnected"}
                </span>
                {wsProgress !== null && (
                  <span style={{ fontSize: "var(--text-sm)", fontWeight: "bold", color: "var(--color-primary-600)" }}>
                    Progress: {wsProgress}%
                  </span>
                )}
              </div>
            </div>
            {dataLoading ? (
              <p>Memuat data...</p>
            ) : rawData && rawData.data && rawData.data.length > 0 ? (
              <>
                <div style={{ overflowX: "auto", border: "1px solid #e2e8f0", borderRadius: 8 }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
                    <thead style={{ background: "#f8fafc" }}>
                      <tr>
                        {Object.keys(rawData.data[0]).map(col => (
                          <th key={col} style={{ padding: "8px 12px", textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rawData.data.map((row, idx) => (
                        <tr key={idx} style={{ borderBottom: "1px solid #e2e8f0" }}>
                          {Object.values(row).map((val, vIdx) => (
                            <td key={vIdx} style={{ padding: "8px 12px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "200px" }}>
                              {val !== null ? String(val) : <i>null</i>}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
                  <div style={{ fontSize: "14px", color: "#64748b" }}>
                    Halaman {rawData.page} dari {rawData.total_pages} (Total: {rawData.total_rows} baris)
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button 
                      onClick={() => setDataPage(p => Math.max(1, p - 1))}
                      disabled={rawData.page === 1}
                      style={{ padding: "6px 12px", borderRadius: 4, background: "#e2e8f0", border: "none", cursor: rawData.page === 1 ? "not-allowed" : "pointer" }}
                    >
                      Sebelumnya
                    </button>
                    <button 
                      onClick={() => setDataPage(p => Math.min(rawData.total_pages, p + 1))}
                      disabled={rawData.page === rawData.total_pages}
                      style={{ padding: "6px 12px", borderRadius: 4, background: "#e2e8f0", border: "none", cursor: rawData.page === rawData.total_pages ? "not-allowed" : "pointer" }}
                    >
                      Selanjutnya
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <p>Tidak ada data.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
