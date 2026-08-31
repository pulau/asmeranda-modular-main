"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

const OPTIMIZATION_METHODS = ["grid_search", "random_search", "bayesian"];

const MODELS = [
  "RandomForest",
  "GradientBoosting",
  "LogisticRegression",
  "LinearRegression",
  "DecisionTree",
  "KNeighbors",
  "SVM",
];

export default function OptimizationPage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const stateId = useWorkflow((s) => s.stateId);
  const problemType = useWorkflow((s) => s.problemType);

  const [modelType, setModelType] = useState("RandomForest");
  const [method, setMethod] = useState("grid_search");
  const [cvFolds, setCvFolds] = useState(5);
  const [nIter, setNIter] = useState(50);
  const [useAsync, setUseAsync] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (!stateId || !problemType) {
    return (
      <div>
        <h1>{tr("optimization.title") || "Hyperparameter Optimization"}</h1>
        <p style={{ color: "#dc2626" }}>
          ⚠ Run preprocessing first.
        </p>
      </div>
    );
  }

  async function runOptimization() {
    setBusy(true);
    setError(null);
    setResult(null);

    try {
      const r = useAsync
        ? await api.optimizeHyperparameters({
            state_id: stateId,
            model_type: modelType,
            problem_type: problemType,
            method: method,
            cv_folds: Number(cvFolds),
            n_iter: Number(nIter),
          })
        : await api.optimizeHyperparametersSync({
            state_id: stateId,
            model_type: modelType,
            problem_type: problemType,
            method: method,
            cv_folds: Number(cvFolds),
            n_iter: Number(nIter),
          });

      if (!r.success) throw new Error(r.error);
      setResult(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>{tr("optimization.title") || "Hyperparameter Optimization"}</h1>
      <p style={{ color: "#64748b" }}>
        Automated hyperparameter tuning for better model performance
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 12,
          marginTop: 16,
          maxWidth: 720,
        }}
      >
        <label>
          Model Type
          <select
            value={modelType}
            onChange={(e) => setModelType(e.target.value)}
            style={{ width: "100%" }}
          >
            {MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>

        <label>
          Optimization Method
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            style={{ width: "100%" }}
          >
            {OPTIMIZATION_METHODS.map((m) => (
              <option key={m} value={m}>
                {m.replace("_", " ").toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <label>
          CV Folds
          <input
            type="number"
            min="2"
            max="10"
            value={cvFolds}
            onChange={(e) => setCvFolds(e.target.value)}
            style={{ width: "100%" }}
          />
        </label>
      </div>

      {(method === "random_search" || method === "bayesian") && (
        <div style={{ marginTop: 12 }}>
          <label>
            Iterations
            <input
              type="number"
              min="10"
              max="200"
              value={nIter}
              onChange={(e) => setNIter(e.target.value)}
              style={{ width: "100%" }}
            />
          </label>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={useAsync}
            onChange={(e) => setUseAsync(e.target.checked)}
          />
          Use Async (background processing)
        </label>
      </div>

      <button
        onClick={runOptimization}
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
        {busy ? "Optimizing..." : "Run Optimization"}
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
          <h3>Optimization Results</h3>
          <p>Method: {result.method?.replace("_", " ").toUpperCase()}</p>
          <p>
            Best Score:{" "}
            <strong>{result.best_score?.toFixed(4)}</strong>
          </p>
          
          {result.best_params && (
            <div style={{ marginTop: 12 }}>
              <h4>Best Parameters:</h4>
              <pre
                style={{
                  background: "#0f172a",
                  color: "#e2e8f0",
                  padding: 12,
                  borderRadius: 4,
                  overflow: "auto",
                }}
              >
                {JSON.stringify(result.best_params, null, 2)}
              </pre>
            </div>
          )}

          {useAsync && (
            <p style={{ marginTop: 12, fontStyle: "italic" }}>
              Results will be saved to state for later use.
            </p>
          )}
        </div>
      )}
    </div>
  );
}