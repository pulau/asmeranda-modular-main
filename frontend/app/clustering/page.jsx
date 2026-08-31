"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

const CLUSTERING_METHODS = ["kmeans", "dbscan", "hierarchical", "spectral"];

export default function ClusteringPage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const stateId = useWorkflow((s) => s.stateId);

  const [method, setMethod] = useState("kmeans");
  const [nClusters, setNClusters] = useState(3);
  const [eps, setEps] = useState(0.5);
  const [minSamples, setMinSamples] = useState(5);
  const [maxK, setMaxK] = useState(10);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [optimalKResult, setOptimalKResult] = useState(null);
  const [error, setError] = useState(null);

  if (!stateId) {
    return (
      <div>
        <h1>{tr("clustering.title") || "Clustering Analysis"}</h1>
        <p style={{ color: "#dc2626" }}>
          ⚠ Run preprocessing first.
        </p>
      </div>
    );
  }

  async function runClustering() {
    setBusy(true);
    setError(null);
    setResult(null);

    try {
      const params =
        method === "kmeans" || method === "hierarchical" || method === "spectral"
          ? { n_clusters: Number(nClusters) }
          : { eps: Number(eps), min_samples: Number(minSamples) };

      const r = await api.performClustering({
        state_id: stateId,
        method: method,
        parameters: params,
      });

      if (!r.success) throw new Error(r.error);
      setResult(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function findOptimalK() {
    setBusy(true);
    setError(null);
    setOptimalKResult(null);

    try {
      const r = await api.findOptimalK({
        state_id: stateId,
        method: "kmeans",
        parameters: { max_k: Number(maxK) },
      });

      if (!r.success) throw new Error(r.error);
      setOptimalKResult(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>{tr("clustering.title") || "Clustering Analysis"}</h1>
      <p style={{ color: "#64748b" }}>
        Unsupervised learning for pattern discovery
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          marginTop: 16,
          maxWidth: 720,
        }}
      >
        <label>
          Clustering Method
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            style={{ width: "100%" }}
          >
            {CLUSTERING_METHODS.map((m) => (
              <option key={m} value={m}>
                {m.charAt(0).toUpperCase() + m.slice(1)}
              </option>
            ))}
          </select>
        </label>

        {(method === "kmeans" || method === "hierarchical" || method === "spectral") && (
          <label>
            Number of Clusters
            <input
              type="number"
              min="2"
              max="20"
              value={nClusters}
              onChange={(e) => setNClusters(e.target.value)}
              style={{ width: "100%" }}
            />
          </label>
        )}

        {method === "dbscan" && (
          <>
            <label>
              EPS
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="2.0"
                value={eps}
                onChange={(e) => setEps(e.target.value)}
                style={{ width: "100%" }}
              />
            </label>
            <label>
              Min Samples
              <input
                type="number"
                min="2"
                max="20"
                value={minSamples}
                onChange={(e) => setMinSamples(e.target.value)}
                style={{ width: "100%" }}
              />
            </label>
          </>
        )}
      </div>

      <div
        style={{
          display: "flex",
          gap: 8,
          marginTop: 16,
        }}
      >
        <button
          onClick={runClustering}
          disabled={busy}
          style={{
            padding: "10px 20px",
            background: "#1e40af",
            color: "#fff",
            border: "none",
            borderRadius: 6,
          }}
        >
          {busy ? "Running..." : "Run Clustering"}
        </button>

        {(method === "kmeans" || method === "hierarchical") && (
          <button
            onClick={findOptimalK}
            disabled={busy}
            style={{
              padding: "10px 20px",
              background: "#059669",
              color: "#fff",
              border: "none",
              borderRadius: 6,
            }}
          >
            {busy ? "Analyzing..." : "Find Optimal K"}
          </button>
        )}
      </div>

      {error && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            background: "#fee2e2",
            color: "#991b1b",
            borderRadius: 6,
          }}
        >
          {error}
        </div>
      )}

      {optimalKResult && optimalKResult.success && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#f0fdf4",
            borderRadius: 6,
            border: "1px solid #16a34a",
          }}
        >
          <h3>Optimal K Analysis</h3>
          <p>
            Optimal K (Elbow Method):{" "}
            <strong>{optimalKResult.optimal_k_elbow}</strong>
          </p>
          <p>
            Optimal K (Silhouette):{" "}
            <strong>{optimalKResult.optimal_k_silhouette}</strong>
          </p>
          <div style={{ marginTop: 12 }}>
            <h4>Silhouette Scores by K:</h4>
            <ul>
              {optimalKResult.k_values.map((k, i) => (
                <li key={k}>
                  K={k}: {optimalKResult.silhouette_scores[i]?.toFixed(3)}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {result && result.success && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#dcfce7",
            borderRadius: 6,
            color: "#166534",
          }}
        >
          <h3>Clustering Results</h3>
          <p>Method: {result.method}</p>
          <p>Number of Clusters: {result.metrics.n_clusters}</p>
          <p>
            Silhouette Score:{" "}
            {result.metrics.silhouette_score?.toFixed(3)}
          </p>
          <p>
            Calinski-Harabasz Score:{" "}
            {result.metrics.calinski_harabasz_score?.toFixed(2)}
          </p>
          <p>
            Davies-Bouldin Score:{" "}
            {result.metrics.davies_bouldin_score?.toFixed(3)}
          </p>
          {result.metrics.n_noise > 0 && (
            <p>Noise Points: {result.metrics.n_noise}</p>
          )}
          {result.metrics.cluster_sizes && (
            <div style={{ marginTop: 12 }}>
              <h4>Cluster Sizes:</h4>
              <ul>
                {Object.entries(result.metrics.cluster_sizes).map(
                  ([cluster, size]) => (
                    <li key={cluster}>
                      Cluster {cluster}: {size} samples
                    </li>
                  )
                )}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}