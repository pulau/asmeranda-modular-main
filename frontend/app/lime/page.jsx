"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

export default function LimePage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const modelId = useWorkflow((s) => s.modelId);
  const stateId = useWorkflow((s) => s.stateId);

  const [sampleIndex, setSampleIndex] = useState(0);
  const [numFeatures, setNumFeatures] = useState(10);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (!modelId) {
    return (
      <div>
        <h1>{tr("lime.title")}</h1>
        <p style={{ color: "#dc2626" }}>⚠ Latih model dulu.</p>
      </div>
    );
  }

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.runLime({
        model_id: modelId,
        state_id: stateId,
        sample_index: Number(sampleIndex),
        num_features: Number(numFeatures),
      });
      setResult(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>{tr("lime.title")}</h1>
      <p style={{ color: "#64748b" }}>
        Model: <code>{modelId}</code>
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          maxWidth: 480,
          marginTop: 12,
        }}
      >
        <label>
          Sample index
          <input
            type="number"
            min="0"
            value={sampleIndex}
            onChange={(e) => setSampleIndex(e.target.value)}
            style={{ width: "100%" }}
          />
        </label>
        <label>
          Num features
          <input
            type="number"
            min="1"
            max="50"
            value={numFeatures}
            onChange={(e) => setNumFeatures(e.target.value)}
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
        {busy ? tr("common.loading") : tr("lime.run")}
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
                alt="LIME plot"
                style={{ maxWidth: "100%", height: "auto" }}
              />
            </div>
          )}

          {result.explanation && result.explanation.length > 0 && (
            <div
              style={{
                marginTop: 16,
                background: "#fff",
                padding: 16,
                borderRadius: 8,
                border: "1px solid #e2e8f0",
              }}
            >
              <h3>{tr("lime.explanation")}</h3>
              <table>
                <thead>
                  <tr>
                    <th>Feature</th>
                    <th>Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {result.explanation.map((row, i) => (
                    <tr key={i}>
                      <td>{row.feature}</td>
                      <td
                        style={{
                          color: row.weight > 0 ? "#16a34a" : "#dc2626",
                        }}
                      >
                        {Number(row.weight).toFixed(4)}
                      </td>
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
