'use client';

import { useState } from 'react';
import { useWorkflow } from '@/lib/workflow-store';
import { useT } from '@/lib/i18n';

export default function AdvancedMLPage() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [activeTab, setActiveTab] = useState('umap');
  const [targetColumn, setTargetColumn] = useState('value');
  
  const stateId = useWorkflow((s) => s.stateId);
  const numericalColumns = useWorkflow((s) => s.numericalColumns);
  const setAdvancedMLResults = useWorkflow((s) => s.set);
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);

  const tabs = [
    { id: 'umap', label: tr('advanced_ml.umap') },
    { id: 'hdbscan', label: tr('advanced_ml.hdbscan') },
    { id: 'anomaly', label: tr('advanced_ml.anomaly') },
    { id: 'forecast', label: tr('advanced_ml.forecast') },
    { id: 'utilities', label: tr('advanced_ml.utilities') },
  ];

  const handleUMAP = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/advanced-ml/umap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state_id: stateId,
          n_components: 2,
          n_neighbors: 15,
          min_dist: 0.1,
        }),
      });
      const data = await response.json();
      setResults(data);
      setAdvancedMLResults({ umap: data });
    } catch (error) {
      console.error('UMAP failed:', error);
      setResults({ success: false, error: 'UMAP failed' });
    } finally {
      setLoading(false);
    }
  };

  const handleHDBSCAN = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/advanced-ml/hdbscan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state_id: stateId,
          min_cluster_size: 5,
          min_samples: null,
          metric: 'euclidean',
        }),
      });
      const data = await response.json();
      setResults(data);
      setAdvancedMLResults({ hdbscan: data });
    } catch (error) {
      console.error('HDBSCAN failed:', error);
      setResults({ success: false, error: 'HDBSCAN failed' });
    } finally {
      setLoading(false);
    }
  };

  const handleAnomalyDetection = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/advanced-ml/anomaly-detection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state_id: stateId,
          method: 'isolation_forest',
          contamination: 0.1,
          n_estimators: 100,
        }),
      });
      const data = await response.json();
      setResults(data);
      setAdvancedMLResults({ anomaly: data });
    } catch (error) {
      console.error('Anomaly detection failed:', error);
      setResults({ success: false, error: 'Anomaly detection failed' });
    } finally {
      setLoading(false);
    }
  };

  const handleForecast = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/advanced-ml/forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state_id: stateId,
          target_column: targetColumn,
          periods: 10,
          method: 'arima',
        }),
      });
      const data = await response.json();
      setResults(data);
      setAdvancedMLResults({ forecast: data });
    } catch (error) {
      console.error('Forecasting failed:', error);
      setResults({ success: false, error: 'Forecasting failed' });
    } finally {
      setLoading(false);
    }
  };

  const handleMissingValues = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/advanced-ml/handle-missing-values', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state_id: stateId,
          strategy: 'auto',
          numeric_strategy: 'mean',
          categorical_strategy: 'mode',
          threshold: 0.5,
        }),
      });
      const data = await response.json();
      setResults(data);
      setAdvancedMLResults({ missing_values: data });
    } catch (error) {
      console.error('Missing value handling failed:', error);
      setResults({ success: false, error: 'Missing value handling failed' });
    } finally {
      setLoading(false);
    }
  };

  const handleDetectOutliers = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/advanced-ml/detect-outliers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state_id: stateId,
          method: 'iqr',
          threshold: 1.5,
          columns: null,
        }),
      });
      const data = await response.json();
      setResults(data);
      setAdvancedMLResults({ outliers: data });
    } catch (error) {
      console.error('Outlier detection failed:', error);
      setResults({ success: false, error: 'Outlier detection failed' });
    } finally {
      setLoading(false);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'umap':
        return (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold">{tr('advanced_ml.umap')}</h2>
            <p className="text-gray-600">
              Uniform Manifold Approximation and Projection for dimensionality reduction
            </p>
            <button
              onClick={handleUMAP}
              disabled={loading || !stateId}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
            >
              {loading ? 'Processing...' : 'Run UMAP'}
            </button>
          </div>
        );
      case 'hdbscan':
        return (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold">{tr('advanced_ml.hdbscan')}</h2>
            <p className="text-gray-600">
              Hierarchical Density-Based Spatial Clustering of Applications with Noise
            </p>
            <button
              onClick={handleHDBSCAN}
              disabled={loading || !stateId}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-300"
            >
              {loading ? 'Processing...' : 'Run HDBSCAN'}
            </button>
          </div>
        );
      case 'anomaly':
        return (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold">{tr('advanced_ml.anomaly')}</h2>
            <p className="text-gray-600">
              Detect anomalies using Isolation Forest or One-Class SVM
            </p>
            <button
              onClick={handleAnomalyDetection}
              disabled={loading || !stateId}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-300"
            >
              {loading ? 'Processing...' : 'Detect Anomalies'}
            </button>
          </div>
        );
      case 'forecast':
        return (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold">{tr('advanced_ml.forecast')}</h2>
            <p className="text-gray-600">
              Forecast time series data using ARIMA, SARIMA, Prophet, or LSTM
            </p>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Target Column</label>
              <select
                value={targetColumn}
                onChange={(e) => setTargetColumn(e.target.value)}
                className="w-full p-2 border rounded"
              >
                {numericalColumns.map((col) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleForecast}
              disabled={loading || !stateId}
              className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:bg-gray-300"
            >
              {loading ? 'Processing...' : 'Run Forecast'}
            </button>
          </div>
        );
      case 'utilities':
        return (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold">{tr('advanced_ml.utilities')}</h2>
            <p className="text-gray-600">
              Handle missing values, detect outliers, and validate data
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleMissingValues}
                disabled={loading || !stateId}
                className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600 disabled:bg-gray-300"
              >
                {loading ? 'Processing...' : 'Handle Missing Values'}
              </button>
              <button
                onClick={handleDetectOutliers}
                disabled={loading || !stateId}
                className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:bg-gray-300"
              >
                {loading ? 'Processing...' : 'Detect Outliers'}
              </button>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">{tr('advanced_ml.title')}</h1>
      
      {!stateId && (
        <div className="mb-6 p-4 bg-yellow-100 border border-yellow-400 rounded">
          <p className="text-yellow-800">
            Please complete preprocessing first to access advanced ML features.
          </p>
        </div>
      )}

      <div className="mb-6 border-b">
        <div className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 border-b-2 ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-500'
                  : 'border-transparent text-gray-500'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-6">{renderContent()}</div>

      {results && (
        <div className="mt-6 p-4 bg-gray-100 rounded">
          <h3 className="font-bold mb-2">Results:</h3>
          <pre className="text-sm overflow-auto">
            {JSON.stringify(results, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}