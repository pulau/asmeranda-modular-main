"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

export default function RecommendationsPage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const datasetId = useWorkflow((s) => s.datasetId);

  const [recommendations, setRecommendations] = useState(null);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [preprocessingSteps, setPreprocessingSteps] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (datasetId) {
      fetchRecommendations();
    }
  }, [datasetId]);

  async function fetchRecommendations() {
    setBusy(true);
    setError(null);
    setRecommendations(null);

    try {
      const r = await api.analyzeDataset({ dataset_id: datasetId });
      if (!r.success) throw new Error(r.error);
      
      setRecommendations(r.recommendations);
      setDatasetInfo(r.dataset_info);
      setPreprocessingSteps(r.preprocessing_steps);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!datasetId) {
    return (
      <div>
        <h1>{tr("clustering.title") || "AI Recommendations"}</h1>
        <p style={{ color: "#dc2626" }}>
          ⚠ Upload dataset first.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h1>{tr("clustering.title") || "AI-Powered Recommendations"}</h1>
      <p style={{ color: "#64748b" }}>
        Intelligent analysis and suggestions for your dataset
      </p>

      <button
        onClick={fetchRecommendations}
        disabled={busy}
        style={{
          marginTop: 16,
          padding: "10px 20px",
          background: "#1e40af",
          color: "#fff",
          border: "none",
          borderRadius: 6,
        }}
      >
        {busy ? "Analyzing..." : "Analyze Dataset"}
      </button>

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

      {datasetInfo && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#f0fdf4",
            borderRadius: 6,
            border: "1px solid #16a34a",
          }}
        >
          <h3>Dataset Information</h3>
          <p>Rows: {datasetInfo.n_rows}</p>
          <p>Columns: {datasetInfo.n_cols}</p>
          <p>Numerical Columns: {datasetInfo.numerical_cols}</p>
          <p>Categorical Columns: {datasetInfo.categorical_cols}</p>
          <p>Missing Values: {datasetInfo.missing_percentage?.toFixed(2)}%</p>
        </div>
      )}

      {preprocessingSteps && preprocessingSteps.length > 0 && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#f0f9ff",
            borderRadius: 6,
            border: "1px solid #3b82f6",
          }}
        >
          <h3>Recommended Preprocessing Steps</h3>
          <ul>
            {preprocessingSteps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ul>
        </div>
      )}

      {recommendations && recommendations.length > 0 && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#fff",
            borderRadius: 6,
            border: "1px solid #e2e8f0",
          }}
        >
          <h3>AI Recommendations</h3>
          {recommendations.map((rec, i) => (
            <div
              key={i}
              style={{
                marginTop: 12,
                padding: 12,
                background:
                  rec.type === "warning"
                    ? "#fef3c7"
                    : rec.type === "info"
                    ? "#dbeafe"
                    : "#dcfce7",
                borderRadius: 4,
                border: `1px solid ${
                  rec.type === "warning"
                    ? "#f59e0b"
                    : rec.type === "info"
                    ? "#3b82f6"
                    : "#16a34a"
                }`,
              }}
            >
              <h4 style={{ margin: "0 0 8px 0" }}>{rec.title}</h4>
              <p style={{ margin: "0 0 8px 0" }}>{rec.description}</p>
              {rec.suggested_models && (
                <div>
                  <strong>Suggested Models:</strong>
                  <ul>
                    {rec.suggested_models.map((model, j) => (
                      <li key={j}>{model}</li>
                    ))}
                  </ul>
                </div>
              )}
              {rec.suggested_methods && (
                <div>
                  <strong>Suggested Methods:</strong>
                  <ul>
                    {rec.suggested_methods.map((method, j) => (
                      <li key={j}>{method}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
