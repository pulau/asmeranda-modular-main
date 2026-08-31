"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

export default function TimeseriesPage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const datasetId = useWorkflow((s) => s.datasetId);
  const datasetName = useWorkflow((s) => s.datasetName);

  const [targetColumn, setTargetColumn] = useState("");
  const [horizon, setHorizon] = useState(10);
  const [method, setMethod] = useState("naive");
  const [contamination, setContamination] = useState(0.05);

  const [columns, setColumns] = useState([]);
  const [detect, setDetect] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [anomalies, setAnomalies] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!datasetId) return;
    (async () => {
      try {
        const s = await api.edaSummary(datasetId);
        if (s.success) {
          setColumns([
            ...(s.metadata.numerical_columns || []),
            ...(s.metadata.categorical_columns || []),
          ]);
          if (!targetColumn && s.metadata.numerical_columns?.length > 0) {
            setTargetColumn(s.metadata.numerical_columns[0]);
          }
        }
      } catch (e) {
        setError(e.message);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  if (!datasetId) {
    return (
      <div>
        <h1>{tr("timeseries.title")}</h1>
        <p style={{ color: "#dc2626" }}>⚠ Unggah dataset dulu.</p>
      </div>
    );
  }

  async function doDetect() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.tsDetect(datasetId, targetColumn);
      setDetect(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function doForecast() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.tsForecast(datasetId, targetColumn, horizon, method);
      setForecast(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function doAnomalies() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.tsAnomalies(datasetId, targetColumn, contamination);
      setAnomalies(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>{tr("timeseries.title")}</h1>
      <p style={{ color: "#64748b" }}>
        Dataset: <code>{datasetName}</code>
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr",
          gap: 12,
          marginTop: 12,
          maxWidth: 960,
        }}
      >
        <label>
          {tr("timeseries.target")}
          <select
            value={targetColumn}
            onChange={(e) => setTargetColumn(e.target.value)}
            style={{ width: "100%" }}
          >
            <option value="">--</option>
            {columns.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label>
          {tr("timeseries.horizon")}
          <input
            type="number"
            min="1"
            max="500"
            value={horizon}
            onChange={(e) => setHorizon(e.target.value)}
            style={{ width: "100%" }}
          />
        </label>
        <label>
          {tr("timeseries.method")}
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            style={{ width: "100%" }}
          >
            <option value="naive">naive</option>
            <option value="drift">drift</option>
            <option value="mean">mean</option>
          </select>
        </label>
        <label>
          {tr("timeseries.contamination")}
          <input
            type="number"
            min="0.001"
            max="0.5"
            step="0.01"
            value={contamination}
            onChange={(e) => setContamination(e.target.value)}
            style={{ width: "100%" }}
          />
        </label>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
        <button
          onClick={doDetect}
          disabled={busy || !targetColumn}
          style={btnPrimary}
        >
          {tr("timeseries.detect")}
        </button>
        <button
          onClick={doForecast}
          disabled={busy || !targetColumn}
          style={btnPrimary}
        >
          {tr("timeseries.forecast")}
        </button>
        <button
          onClick={doAnomalies}
          disabled={busy || !targetColumn}
          style={btnPrimary}
        >
          {tr("timeseries.anomalies")}
        </button>
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

      {detect && detect.success && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 6,
          }}
        >
          <h3>Detect</h3>
          <p>N: {detect.n_observations}</p>
          <p>Mean: {Number(detect.mean).toFixed(3)} | Std: {Number(detect.std).toFixed(3)}</p>
          <p>
            Min: {Number(detect.min).toFixed(3)} | Max: {Number(detect.max).toFixed(3)}
          </p>
          <p>
            Stationary (ADF p&lt;0.05):{" "}
            {detect.is_stationary === null
              ? "n/a"
              : detect.is_stationary
              ? "✓ yes"
              : "✗ no"}
          </p>
          <p>Anomalies detected: {detect.n_anomalies}</p>
        </div>
      )}

      {forecast && forecast.success && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 6,
          }}
        >
          <h3>Forecast ({forecast.method})</h3>
          <p>Last observed: {Number(forecast.last_observed).toFixed(3)}</p>
          <table>
            <thead>
              <tr>
                <th>Step</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {forecast.forecast.map((v, i) => (
                <tr key={i}>
                  <td>{i + 1}</td>
                  <td>{Number(v).toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {anomalies && anomalies.success && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 6,
          }}
        >
          <h3>Anomalies</h3>
          <p>Found: {anomalies.n_anomalies} of {anomalies.n_observations}</p>
          <table>
            <thead>
              <tr>
                <th>Index</th>
                <th>Value</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {(anomalies.anomalies || []).slice(0, 50).map((a) => (
                <tr key={a.index}>
                  <td>{a.index}</td>
                  <td>{Number(a.value).toFixed(3)}</td>
                  <td>{Number(a.score).toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const btnPrimary = {
  padding: "8px 14px",
  background: "#1e40af",
  color: "#fff",
  border: "none",
  borderRadius: 4,
  cursor: "pointer",
};
