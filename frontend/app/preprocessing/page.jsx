"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

export default function PreprocessingPage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const set = useWorkflow((s) => s.set);
  const datasetId = useWorkflow((s) => s.datasetId);
  const numericalColumns = useWorkflow((s) => s.numericalColumns) || [];
  const categoricalColumns = useWorkflow((s) => s.categoricalColumns) || [];
  const allColumns = [...numericalColumns, ...categoricalColumns];

  const [targetColumn, setTargetColumn] = useState("");
  const [problemType, setProblemType] = useState("Classification");
  const [scalingMethod, setScalingMethod] = useState("auto");
  const [imputationStrategy, setImputationStrategy] = useState("mean");
  const [applyEncoding, setApplyEncoding] = useState(true);
  const [testSize, setTestSize] = useState(0.2);
  
  // Feature selection states
  const [featureSelectionMethod, setFeatureSelectionMethod] = useState("none");
  const [maxFeatures, setMaxFeatures] = useState(10);
  const [selectionThreshold, setSelectionThreshold] = useState(0.05);
  const [showFeatureSelection, setShowFeatureSelection] = useState(false);
  
  // Imbalance handling states
  const [imbalanceMethod, setImbalanceMethod] = useState("none");
  const [samplingStrategy, setSamplingStrategy] = useState("auto");
  const [showImbalanceHandling, setShowImbalanceHandling] = useState(false);
  
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!targetColumn && allColumns.length > 0) {
      setTargetColumn(allColumns[allColumns.length - 1]);
    }
  }, [allColumns, targetColumn]);

  if (!datasetId) {
    return (
      <div>
        <h1>{tr("preprocessing.title")}</h1>
        <p style={{ color: "#dc2626" }}>⚠ Unggah dataset dulu.</p>
      </div>
    );
  }

  async function run() {
    if (!targetColumn) {
      setError("Pilih kolom target dulu");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.runPreprocessing({
        dataset_id: datasetId,
        target_column: targetColumn,
        problem_type: problemType,
        scaling_method: scalingMethod,
        imputation_strategy: imputationStrategy,
        apply_encoding: applyEncoding,
        test_size: Number(testSize),
        random_state: 42,
        feature_selection: showFeatureSelection ? {
          method: featureSelectionMethod,
          max_features: Number(maxFeatures),
          threshold: Number(selectionThreshold),
        } : null,
        imbalance_handling: showImbalanceHandling ? {
          method: imbalanceMethod,
          sampling_strategy: samplingStrategy,
        } : null,
      });
      if (!r.success) throw new Error(r.error);
      setResult(r);
      set({
        stateId: r.state_id,
        targetColumn: r.target_column,
        problemType: r.problem_type,
        featureNames: r.feature_names,
        nSamplesTrain: r.n_samples_train,
        nSamplesTest: r.n_samples_test,
        nFeatures: r.n_features,
        numericalColumns: numericalColumns.filter((c) => c !== targetColumn),
        categoricalColumns: categoricalColumns.filter((c) => c !== targetColumn),
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>{tr("preprocessing.title")}</h1>

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
          {tr("preprocessing.target")}
          <select
            value={targetColumn}
            onChange={(e) => setTargetColumn(e.target.value)}
            style={{ width: "100%" }}
          >
            <option value="">-- pilih --</option>
            {allColumns.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <label>
          {tr("preprocessing.problem")}
          <select
            value={problemType}
            onChange={(e) => setProblemType(e.target.value)}
            style={{ width: "100%" }}
          >
            <option value="Classification">
              {tr("preprocessing.problem.classification")}
            </option>
            <option value="Regression">
              {tr("preprocessing.problem.regression")}
            </option>
            <option value="Forecasting">
              {tr("preprocessing.problem.forecasting")}
            </option>
          </select>
        </label>

        <label>
          {tr("preprocessing.scaling")}
          <select
            value={scalingMethod}
            onChange={(e) => setScalingMethod(e.target.value)}
            style={{ width: "100%" }}
          >
            <option value="auto">auto</option>
            <option value="standard">standard</option>
            <option value="minmax">minmax</option>
            <option value="robust">robust</option>
            <option value="power">power</option>
            <option value="quantile">quantile</option>
            <option value="none">none</option>
          </select>
        </label>

        <label>
          {tr("preprocessing.imputation")}
          <select
            value={imputationStrategy}
            onChange={(e) => setImputationStrategy(e.target.value)}
            style={{ width: "100%" }}
          >
            <option value="mean">mean</option>
            <option value="median">median</option>
            <option value="most_frequent">most_frequent</option>
            <option value="drop">drop</option>
          </select>
        </label>

        <label>
          {tr("preprocessing.test_size")} ({(Number(testSize) * 100).toFixed(0)}%)
          <input
            type="number"
            min="0.05"
            max="0.5"
            step="0.05"
            value={testSize}
            onChange={(e) => setTestSize(e.target.value)}
            style={{ width: "100%" }}
          />
        </label>

        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            alignSelf: "end",
          }}
        >
          <input
            type="checkbox"
            checked={applyEncoding}
            onChange={(e) => setApplyEncoding(e.target.checked)}
          />
          Apply one-hot encoding
        </label>
      </div>

      <div style={{ marginTop: 16 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={showFeatureSelection}
            onChange={(e) => setShowFeatureSelection(e.target.checked)}
          />
          <strong>Advanced: Feature Selection</strong>
        </label>
      </div>

      {showFeatureSelection && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#f8fafc",
            borderRadius: 8,
            border: "1px solid #e2e8f0",
          }}
        >
          <h4 style={{ marginTop: 0, marginBottom: 12 }}>Feature Selection</h4>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: 12,
            }}
          >
            <label>
              Method
              <select
                value={featureSelectionMethod}
                onChange={(e) => setFeatureSelectionMethod(e.target.value)}
                style={{ width: "100%" }}
              >
                <option value="none">None</option>
                <option value="variance">Variance Threshold</option>
                <option value="correlation">Correlation Filter</option>
                <option value="kbest">SelectKBest</option>
                <option value="rfe">RFE (Recursive Elimination)</option>
              </select>
            </label>

            <label>
              Max Features
              <input
                type="number"
                min="1"
                max="100"
                value={maxFeatures}
                onChange={(e) => setMaxFeatures(e.target.value)}
                style={{ width: "100%" }}
              />
            </label>

            <label>
              Threshold
              <input
                type="number"
                min="0.01"
                max="1.0"
                step="0.01"
                value={selectionThreshold}
                onChange={(e) => setSelectionThreshold(e.target.value)}
                style={{ width: "100%" }}
              />
            </label>
          </div>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={showImbalanceHandling}
            onChange={(e) => setShowImbalanceHandling(e.target.checked)}
          />
          <strong>Advanced: Handle Imbalance Dataset</strong>
        </label>
      </div>

      {showImbalanceHandling && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: "#f8fafc",
            borderRadius: 8,
            border: "1px solid #e2e8f0",
          }}
        >
          <h4 style={{ marginTop: 0, marginBottom: 12 }}>Imbalance Handling</h4>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
            }}
          >
            <label>
              Method
              <select
                value={imbalanceMethod}
                onChange={(e) => setImbalanceMethod(e.target.value)}
                style={{ width: "100%" }}
              >
                <option value="none">None</option>
                <option value="oversample">Random Oversampling</option>
                <option value="undersample">Random Undersampling</option>
                <option value="smote">SMOTE</option>
                <option value="adasyn">ADASYN</option>
              </select>
            </label>

            <label>
              Sampling Strategy
              <select
                value={samplingStrategy}
                onChange={(e) => setSamplingStrategy(e.target.value)}
                style={{ width: "100%" }}
              >
                <option value="auto">Auto</option>
                <option value="minority">Minority</option>
                <option value="not_minority">Not Minority</option>
                <option value="all">All</option>
              </select>
            </label>
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
          fontSize: 14,
        }}
      >
        {busy ? tr("common.loading") : tr("preprocessing.run")}
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
          <p>Train: {result.n_samples_train} | Test: {result.n_samples_test} | Features: {result.n_features}</p>
          <p>Steps: {result.preprocessing_steps.join(" → ")}</p>
          
          {result.feature_selection_info && result.feature_selection_info.method !== "none" && (
            <div style={{ marginTop: 8, padding: 8, background: "#f0fdf4", borderRadius: 4 }}>
              <strong>Feature Selection:</strong> {result.feature_selection_info.method}
              {result.feature_selection_info.selected_features && (
                <span> ({result.feature_selection_info.selected_features.length} features selected)</span>
              )}
            </div>
          )}
          
          {result.imbalance_handling_info && result.imbalance_handling_info.method !== "none" && (
            <div style={{ marginTop: 8, padding: 8, background: "#f0fdf4", borderRadius: 4 }}>
              <strong>Imbalance Handling:</strong> {result.imbalance_handling_info.method}
              {result.imbalance_handling_info.original_shape && (
                <span> (Samples: {result.imbalance_handling_info.original_shape[0]} → {result.imbalance_handling_info.resampled_shape[0]})</span>
              )}
            </div>
          )}
          
          <p>
            Lanjut ke <strong>{tr("nav.training")}</strong>.
          </p>
        </div>
      )}
    </div>
  );
}
