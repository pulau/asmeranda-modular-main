"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

const MODELS = [
  "RandomForest",
  "GradientBoosting",
  "LogisticRegression",
  "LinearRegression",
  "DecisionTree",
  "KNeighbors",
  "SVM",
  "XGBoost",
  "LightGBM",
  "CatBoost",
  "Voting",
  "Stacking",
];

const CV_METHODS = ["kfold", "stratified", "loo", "timeseries", "none"];

const HYPERPARAM_TEMPLATES = {
  RandomForest: {
    n_estimators: { min: 50, max: 300, default: 100, type: "int" },
    max_depth: { min: 3, max: 20, default: 10, type: "int" },
    min_samples_split: { min: 2, max: 10, default: 2, type: "int" },
    min_samples_leaf: { min: 1, max: 5, default: 1, type: "int" },
  },
  GradientBoosting: {
    n_estimators: { min: 50, max: 300, default: 100, type: "int" },
    learning_rate: { min: 0.01, max: 0.3, default: 0.1, type: "float" },
    max_depth: { min: 3, max: 10, default: 3, type: "int" },
    subsample: { min: 0.5, max: 1.0, default: 0.8, type: "float" },
  },
  LogisticRegression: {
    C: { min: 0.01, max: 10.0, default: 1.0, type: "float" },
    max_iter: { min: 100, max: 1000, default: 1000, type: "int" },
    solver: { options: ["lbfgs", "liblinear", "saga"], default: "lbfgs", type: "select" },
  },
  LinearRegression: {
    fit_intercept: { default: true, type: "boolean" },
  },
  DecisionTree: {
    max_depth: { min: 3, max: 20, default: 10, type: "int" },
    min_samples_split: { min: 2, max: 10, default: 2, type: "int" },
    min_samples_leaf: { min: 1, max: 5, default: 1, type: "int" },
  },
  KNeighbors: {
    n_neighbors: { min: 1, max: 20, default: 5, type: "int" },
    weights: { options: ["uniform", "distance"], default: "uniform", type: "select" },
  },
  SVM: {
    C: { min: 0.1, max: 10.0, default: 1.0, type: "float" },
    kernel: { options: ["linear", "rbf", "poly"], default: "rbf", type: "select" },
  },
  XGBoost: {
    n_estimators: { min: 50, max: 300, default: 100, type: "int" },
    learning_rate: { min: 0.01, max: 0.3, default: 0.1, type: "float" },
    max_depth: { min: 3, max: 10, default: 3, type: "int" },
  },
  LightGBM: {
    n_estimators: { min: 50, max: 300, default: 100, type: "int" },
    learning_rate: { min: 0.01, max: 0.3, default: 0.1, type: "float" },
    max_depth: { min: 3, max: 10, default: 3, type: "int" },
  },
  CatBoost: {
    iterations: { min: 50, max: 300, default: 100, type: "int" },
    learning_rate: { min: 0.01, max: 0.3, default: 0.1, type: "float" },
    depth: { min: 3, max: 10, default: 3, type: "int" },
  },
  Voting: {
    voting: { options: ["hard", "soft"], default: "soft", type: "select" },
  },
  Stacking: {
    final_estimator: { options: ["LogisticRegression", "LinearRegression"], default: "LogisticRegression", type: "select" },
  },
};

export default function TrainingPage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const set = useWorkflow((s) => s.set);
  const stateId = useWorkflow((s) => s.stateId);
  const problemType = useWorkflow((s) => s.problemType);

  const [modelType, setModelType] = useState("RandomForest");
  const [cvMethod, setCvMethod] = useState("kfold");
  const [cvFolds, setCvFolds] = useState(5);
  const [hyperparams, setHyperparams] = useState({});
  const [showHyperparams, setShowHyperparams] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [evaluating, setEvaluating] = useState(false);
  const [learningCurveResult, setLearningCurveResult] = useState(null);
  const [generatingLearningCurve, setGeneratingLearningCurve] = useState(false);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [comparingModels, setComparingModels] = useState(false);

  // Reset hyperparameters when model type changes
  useEffect(() => {
    const template = HYPERPARAM_TEMPLATES[modelType] || {};
    const defaults = {};
    Object.keys(template).forEach(key => {
      defaults[key] = template[key].default;
    });
    setHyperparams(defaults);
  }, [modelType]);

  if (!stateId || !problemType) {
    return (
      <div>
        <h1>{tr("training.title")}</h1>
        <p style={{ color: "#dc2626" }}>⚠ Jalankan preprocessing dulu.</p>
      </div>
    );
  }

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    setEvaluationResult(null);
    try {
      const r = await api.startTraining({
        state_id: stateId,
        model_type: modelType,
        problem_type: problemType,
        cv_method: cvMethod,
        cv_folds: Number(cvFolds),
        hyperparams: hyperparams,
      });
      if (!r.success) throw new Error(r.error);
      setResult(r);
      set({
        modelId: r.model_id,
        modelType: modelType,
        metrics: r.metrics,
        cvScores: r.cv_scores,
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runEvaluation() {
    if (!result || !result.model_id) {
      setError("Train a model first before evaluation");
      return;
    }
    
    setEvaluating(true);
    setError(null);
    setEvaluationResult(null);
    try {
      const r = await api.evaluateModel({
        state_id: stateId,
        model_id: result.model_id,
        generate_plots: true,
        plot_types: ["confusion_matrix", "roc_curve", "feature_importance", "precision_recall_curve"],
      });
      if (!r.success) throw new Error(r.error);
      setEvaluationResult(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setEvaluating(false);
    }
  }

  async function runLearningCurve() {
    if (!result || !result.model_id) {
      setError("Train a model first before generating learning curve");
      return;
    }
    
    setGeneratingLearningCurve(true);
    setError(null);
    setLearningCurveResult(null);
    try {
      const r = await fetch('/api/v1/training/learning-curve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state_id: stateId,
          model_id: result.model_id,
          cv: 5,
          train_sizes: null
        })
      });
      const data = await r.json();
      if (!data.success) throw new Error(data.error || "Learning curve generation failed");
      setLearningCurveResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setGeneratingLearningCurve(false);
    }
  }

  async function runModelComparison() {
    setComparingModels(true);
    setError(null);
    setComparisonResult(null);
    try {
      const r = await fetch('/api/v1/training/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state_id: stateId,
          model_types: null,
          cv_method: cvMethod,
          cv_folds: Number(cvFolds)
        })
      });
      const data = await r.json();
      if (!data.success) throw new Error(data.error || "Model comparison failed");
      setComparisonResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setComparingModels(false);
    }
  }

  return (
    <div>
      <h1>{tr("training.title")}</h1>
      <p style={{ color: "#64748b" }}>
        Problem type: <strong>{problemType}</strong>
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
          {tr("training.model_type")}
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
          {tr("training.cv_method")}
          <select
            value={cvMethod}
            onChange={(e) => setCvMethod(e.target.value)}
            style={{ width: "100%" }}
          >
            {CV_METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>

        <label>
          {tr("training.cv_folds")}
          <input
            type="number"
            min="2"
            max="20"
            value={cvFolds}
            onChange={(e) => setCvFolds(e.target.value)}
            style={{ width: "100%" }}
          />
        </label>
      </div>

      <div style={{ marginTop: 16 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={showHyperparams}
            onChange={(e) => setShowHyperparams(e.target.checked)}
          />
          <strong>Advanced: Configure Hyperparameters</strong>
        </label>
      </div>

      {showHyperparams && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#f8fafc",
            borderRadius: 8,
            border: "1px solid #e2e8f0",
          }}
        >
          <h4 style={{ marginTop: 0, marginBottom: 12 }}>
            Hyperparameters for {modelType}
          </h4>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
            }}
          >
            {Object.entries(HYPERPARAM_TEMPLATES[modelType] || {}).map(
              ([paramName, config]) => (
                <label key={paramName}>
                  {paramName}
                  {config.type === "select" ? (
                    <select
                      value={hyperparams[paramName] || config.default}
                      onChange={(e) =>
                        setHyperparams({
                          ...hyperparams,
                          [paramName]: e.target.value,
                        })
                      }
                      style={{ width: "100%" }}
                    >
                      {config.options.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  ) : config.type === "boolean" ? (
                    <select
                      value={hyperparams[paramName] ?? config.default}
                      onChange={(e) =>
                        setHyperparams({
                          ...hyperparams,
                          [paramName]: e.target.value === "true",
                        })
                      }
                      style={{ width: "100%" }}
                    >
                      <option value="true">True</option>
                      <option value="false">False</option>
                    </select>
                  ) : (
                    <input
                      type={config.type === "float" ? "number" : "number"}
                      step={config.type === "float" ? "0.01" : "1"}
                      min={config.min}
                      max={config.max}
                      value={hyperparams[paramName] ?? config.default}
                      onChange={(e) =>
                        setHyperparams({
                          ...hyperparams,
                          [paramName]:
                            config.type === "float"
                              ? parseFloat(e.target.value)
                              : parseInt(e.target.value),
                        })
                      }
                      style={{ width: "100%" }}
                    />
                  )}
                </label>
              )
            )}
          </div>
        </div>
      )}

      <button
        onClick={run}
        disabled={busy}
        style={{
          marginTop: 20,
          padding: "10px 20px",
          background: "#1e40af",
          color: "#fff",
          border: "none",
          borderRadius: 6,
        }}
      >
        {busy ? tr("common.loading") : tr("training.start")}
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
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#dcfce7",
            borderRadius: 6,
            color: "#166534",
          }}
        >
          <h3>✓ {tr("common.success")}</h3>
          <p>
            Model ID: <code>{result.model_id}</code>
          </p>
          <h4>{tr("training.metrics")}</h4>
          <pre
            style={{
              background: "#0f172a",
              color: "#e2e8f0",
              padding: 12,
              borderRadius: 4,
              overflow: "auto",
            }}
          >
            {JSON.stringify(result.metrics, null, 2)}
          </pre>
          {result.cv_scores && (
            <>
              <h4>{tr("training.cv_scores")}</h4>
              <p>
                Method: {result.cv_scores.method} | Folds: {result.cv_scores.folds} |{" "}
                Scoring: {result.cv_scores.scoring}
              </p>
              <p>
                Mean: {Number(result.cv_scores.mean).toFixed(4)} | Std:{" "}
                {Number(result.cv_scores.std).toFixed(4)}
              </p>
            </>
          )}
          
          <button
            onClick={runEvaluation}
            disabled={evaluating}
            style={{
              marginTop: 16,
              padding: "8px 16px",
              background: "#059669",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              fontSize: 14,
            }}
          >
            {evaluating ? "Running Evaluation..." : "Run Comprehensive Evaluation"}
          </button>
          
          <button
            onClick={runLearningCurve}
            disabled={generatingLearningCurve}
            style={{
              marginTop: 16,
              marginLeft: 8,
              padding: "8px 16px",
              background: "#0891b2",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              fontSize: 14,
            }}
          >
            {generatingLearningCurve ? "Generating Learning Curve..." : "Generate Learning Curve"}
          </button>
          
          <button
            onClick={runModelComparison}
            disabled={comparingModels}
            style={{
              marginTop: 16,
              marginLeft: 8,
              padding: "8px 16px",
              background: "#7c3aed",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              fontSize: 14,
            }}
          >
            {comparingModels ? "Comparing Models..." : "Compare All Models"}
          </button>
          
          <button
            onClick={() => {
              const API_BASE = process.env.NEXT_PUBLIC_API_BASE_PATH || "/api/v1";
              window.open(`${API_BASE}/training/models/${result.model_id}/download`, '_blank');
            }}
            style={{
              marginTop: 16,
              marginLeft: 8,
              padding: "8px 16px",
              background: "#7c3aed",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              fontSize: 14,
            }}
          >
            Download Model
          </button>
          
          <p>
            Lanjut ke <strong>SHAP</strong> atau <strong>LIME</strong> untuk interpretasi.
          </p>
        </div>
      )}

      {evaluationResult && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#f0fdf4",
            borderRadius: 6,
            border: "1px solid #16a34a",
          }}
        >
          <h3>📊 Evaluation Results</h3>
          
          {evaluationResult.metrics && (
            <div style={{ marginBottom: 16 }}>
              <h4>Detailed Metrics</h4>
              <pre
                style={{
                  background: "#0f172a",
                  color: "#e2e8f0",
                  padding: 12,
                  borderRadius: 4,
                  overflow: "auto",
                }}
              >
                {JSON.stringify(evaluationResult.metrics, null, 2)}
              </pre>
            </div>
          )}
          
          {evaluationResult.plots && (
            <div>
              <h4>Visualization Plots</h4>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                  gap: 16,
                  marginTop: 12,
                }}
              >
                {Object.entries(evaluationResult.plots).map(([plotName, plotBase64]) => (
                  plotBase64 && (
                    <div
                      key={plotName}
                      style={{
                        background: "#fff",
                        padding: 12,
                        borderRadius: 8,
                        border: "1px solid #e2e8f0",
                      }}
                    >
                      <h5 style={{ marginTop: 0, marginBottom: 8, textTransform: "capitalize" }}>
                        {plotName.replace(/_/g, " ")}
                      </h5>
                      <img
                        src={`data:image/png;base64,${plotBase64}`}
                        alt={plotName}
                        style={{ maxWidth: "100%", height: "auto" }}
                      />
                    </div>
                  )
                ))}
              </div>
            </div>
          )}
          
          {learningCurveResult && (
            <div style={{ marginTop: 16, padding: 16, background: "#f0fdf4", borderRadius: 6, border: "1px solid #16a34a" }}>
              <h3>📈 Learning Curve Analysis</h3>
              <div style={{ marginBottom: 16 }}>
                <h4>Diagnosis: <strong>{learningCurveResult.diagnosis}</strong></h4>
                <p>Final Training Score: {learningCurveResult.final_train_score?.toFixed(4)}</p>
                <p>Final Test Score: {learningCurveResult.final_test_score?.toFixed(4)}</p>
                <p>Score Gap: {learningCurveResult.score_gap?.toFixed(4)}</p>
                <p>Scoring Metric: {learningCurveResult.scoring}</p>
              </div>
              {learningCurveResult.plot_base64 && (
                <div style={{ background: "#fff", padding: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}>
                  <h5 style={{ marginTop: 0, marginBottom: 8 }}>Learning Curve Plot</h5>
                  <img
                    src={`data:image/png;base64,${learningCurveResult.plot_base64}`}
                    alt="Learning Curve"
                    style={{ maxWidth: "100%", height: "auto" }}
                  />
                </div>
              )}
            </div>
          )}
          
          {comparisonResult && (
            <div style={{ marginTop: 16, padding: 16, background: "#f0fdf4", borderRadius: 6, border: "1px solid #16a34a" }}>
              <h3>🏆 Model Comparison Results</h3>
              <div style={{ marginBottom: 16 }}>
                <h4>Best Model: <strong>{comparisonResult.best_model?.model_type}</strong></h4>
                <p>Ranking Metric: {comparisonResult.ranking_metric}</p>
              </div>
              <div style={{ marginBottom: 16 }}>
                <h4>Performance Ranking:</h4>
                <div style={{ maxHeight: "300px", overflowY: "auto" }}>
                  {comparisonResult.ranking?.map((model, index) => (
                    <div key={index} style={{ padding: 8, borderBottom: "1px solid #e2e8f0" }}>
                      <strong>{index + 1}. {model.model_type}</strong>
                      <br />
                      {comparisonResult.ranking_metric}: {model.metrics?.[comparisonResult.ranking_metric]?.toFixed(4)}
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4>All Results:</h4>
                <pre
                  style={{
                    background: "#0f172a",
                    color: "#e2e8f0",
                    padding: 12,
                    borderRadius: 4,
                    overflow: "auto",
                    maxHeight: "300px",
                  }}
                >
                  {JSON.stringify(comparisonResult.results, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
