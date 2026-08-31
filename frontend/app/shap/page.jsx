"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

export default function ShapPage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const modelId = useWorkflow((s) => s.modelId);
  const stateId = useWorkflow((s) => s.stateId);

  const [maxSamples, setMaxSamples] = useState(200);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (!modelId) {
    return (
      <div>
        <h1>{tr("shap.title")}</h1>
        <p style={{ color: "#dc2626" }}>⚠ Latih model dulu.</p>
      </div>
    );
  }

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.runShap({
        model_id: modelId,
        state_id: stateId,
        max_samples: Number(maxSamples),
      });
      if (!r.success && r.error) {
        // Tetap tampilkan result partial (feature importance mungkin ada)
      }
      setResult(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>{tr("shap.title")}</h1>
      <p style={{ color: "#64748b" }}>
        Model: <code>{modelId}</code>
      </p>

      <div style={{ marginTop: 12, maxWidth: 360 }}>
        <label>
          Max samples
          <input
            type="number"
            min="10"
            max="5000"
            value={maxSamples}
            onChange={(e) => setMaxSamples(e.target.value)}
            style={{ width: "100%" }}
          />
        </label>
      </div>

      <button
        onClick={run}
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
        {busy ? tr("common.loading") : tr("shap.run")}
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

      {result && (
        <div style={{ marginTop: 16 }}>
          {result.error && (
            <p style={{ color: "#b45309", marginBottom: 12 }}>⚠ {result.error}</p>
          )}
          {result.plot_base64 && (
            <div
              style={{
                background: "#fff",
                padding: 16,
                borderRadius: 8,
                border: "1px solid #e2e8f0",
              }}
            >
              <img
                src={`data:image/png;base64,${result.plot_base64}`}
                alt="SHAP plot"
                style={{ maxWidth: "100%", height: "auto" }}
              />
            </div>
          )}

          {result.shap_values_summary && result.shap_values_summary.length > 0 && (
            <div
              style={{
                marginTop: 16,
                background: "#fff",
                padding: 16,
                borderRadius: 8,
                border: "1px solid #e2e8f0",
              }}
            >
              <h3>{tr("shap.top_features")}</h3>
              <table>
                <thead>
                  <tr>
                    <th>Feature</th>
                    <th>mean |SHAP|</th>
                  </tr>
                </thead>
                <tbody>
                  {result.shap_values_summary.slice(0, 20).map((row) => (
                    <tr key={row.feature}>
                      <td>{row.feature}</td>
                      <td>{Number(row.mean_abs_shap).toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
