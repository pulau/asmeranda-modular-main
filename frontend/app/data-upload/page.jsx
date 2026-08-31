"use client";

import { useRef, useState, useEffect } from "react";
import { api, ApiError } from "@/lib/api";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

export default function DataUploadPage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const set = useWorkflow((s) => s.set);
  const reset = useWorkflow((s) => s.reset);
  const datasetId = useWorkflow((s) => s.datasetId);
  const datasetName = useWorkflow((s) => s.datasetName);

  const fileInput = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [list, setList] = useState([]);
  const [listLoading, setListLoading] = useState(false);

  // Load dataset list on mount
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refresh() {
    setListLoading(true);
    try {
      const r = await api.listDatasets();
      setList(r.datasets || []);
    } catch {
      // silent
    } finally {
      setListLoading(false);
    }
  }

  async function doUpload(file) {
    if (!file) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    setProgress(0);
    try {
      const r = await api.uploadDataset(file, setProgress);
      if (!r.success) throw new ApiError(r.error || "Upload gagal", 400);
      set({
        datasetId: r.metadata.dataset_id,
        datasetName: r.metadata.filename,
        numericalColumns: r.metadata.numerical_columns,
        categoricalColumns: r.metadata.categorical_columns,
      });
      setSuccess(tr("upload.success"));
      await refresh();
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
      setProgress(0);
    }
  }

  async function doDelete(id, name) {
    if (!confirm(`Hapus dataset "${name}"?`)) return;
    try {
      await api.deleteDataset(id);
      await refresh();
      if (useWorkflow.getState().datasetId === id) {
        reset();
      }
    } catch (e) {
      alert("Gagal menghapus: " + e.message);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) doUpload(file);
  }

  return (
    <div>
      {/* ── Page Header ── */}
      <div className="page-header">
        <h1 className="page-title">📂 {tr("upload.title")}</h1>
        <p className="page-subtitle">{tr("upload.subtitle")}</p>
      </div>

      {/* ── Current Dataset Info ── */}
      {datasetId && (
        <div className="alert alert-info mb-6">
          <span>💾</span>
          <div>
            <strong>Dataset aktif:</strong> {datasetName}{" "}
            <code>{datasetId.slice(0, 8)}…</code>
            <br />
            <span style={{ fontSize: "var(--text-xs)", opacity: 0.8 }}>
              Upload file baru untuk mengganti dataset aktif
            </span>
          </div>
        </div>
      )}

      {/* ── Drop Zone ── */}
      <div
        className={`drop-zone${dragActive ? " drop-zone--active" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        onClick={() => !busy && fileInput.current?.click()}
        style={{ cursor: busy ? "not-allowed" : "pointer" }}
      >
        <div className="drop-zone-icon">
          {busy ? "⏳" : dragActive ? "📥" : "📂"}
        </div>
        <p
          style={{
            fontWeight: 600,
            fontSize: "var(--text-lg)",
            color: "var(--color-slate-700)",
            marginBottom: "var(--space-2)",
          }}
        >
          {busy
            ? `Mengupload... ${progress}%`
            : dragActive
            ? "Lepaskan file di sini"
            : tr("upload.drag")}
        </p>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-slate-400)" }}>
          Format: <code>CSV</code> <code>XLSX</code> <code>XLS</code>{" "}
          <code>Parquet</code> <code>JSON</code> <code>TSV</code>
        </p>

        <input
          ref={fileInput}
          type="file"
          style={{ display: "none" }}
          accept=".csv,.xlsx,.xls,.parquet,.json,.tsv"
          onChange={(e) => doUpload(e.target.files?.[0])}
          disabled={busy}
        />
      </div>

      {/* ── Progress Bar ── */}
      {busy && (
        <div className="mt-4">
          <div className="flex-between" style={{ marginBottom: "var(--space-2)", fontSize: "var(--text-sm)", color: "var(--color-slate-500)" }}>
            <span>Mengupload file...</span>
            <strong>{progress}%</strong>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* ── Feedback Messages ── */}
      {error && (
        <div className="alert alert-error mt-4">
          <span>✗</span>
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="alert alert-success mt-4">
          <span>✓</span>
          <div>
            {success}{" "}
            {datasetName && (
              <>
                — <code>{datasetName}</code>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Dataset List ── */}
      <div className="mt-8">
        <div className="flex-between mb-4">
          <h2 style={{ fontSize: "var(--text-xl)", fontWeight: 700, color: "var(--color-slate-800)" }}>
            Daftar Dataset
          </h2>
          <button
            className="btn btn-secondary btn-sm"
            onClick={refresh}
            disabled={listLoading}
          >
            {listLoading ? "⏳ Memuat..." : "🔄 Refresh"}
          </button>
        </div>

        {listLoading && list.length === 0 && (
          <div>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="skeleton"
                style={{ height: "52px", marginBottom: "var(--space-2)" }}
              />
            ))}
          </div>
        )}

        {!listLoading && list.length === 0 && (
          <div
            className="card"
            style={{ textAlign: "center", padding: "var(--space-12)", color: "var(--color-slate-400)" }}
          >
            <div style={{ fontSize: "40px", marginBottom: "var(--space-3)" }}>📭</div>
            <p style={{ fontWeight: 500 }}>Belum ada dataset yang diupload</p>
          </div>
        )}

        {list.length > 0 && (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nama File</th>
                  <th>Baris</th>
                  <th>Kolom</th>
                  <th>Aksi</th>
                </tr>
              </thead>
              <tbody>
                {list.map((d) => (
                  <tr key={d.dataset_id}>
                    <td>
                      <code>{d.dataset_id.slice(0, 8)}…</code>
                      {d.dataset_id === datasetId && (
                        <span
                          style={{
                            marginLeft: "6px",
                            fontSize: "10px",
                            background: "var(--color-primary-100)",
                            color: "var(--color-primary-700)",
                            padding: "1px 6px",
                            borderRadius: "999px",
                            fontWeight: 600,
                          }}
                        >
                          aktif
                        </span>
                      )}
                    </td>
                    <td style={{ fontWeight: 500 }}>{d.filename}</td>
                    <td>{d.rows?.toLocaleString()}</td>
                    <td>{d.columns}</td>
                    <td>
                      <div className="flex-gap-2">
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => {
                            set({
                              datasetId: d.dataset_id,
                              datasetName: d.filename,
                              numericalColumns: d.numerical_columns || [],
                              categoricalColumns: d.categorical_columns || [],
                            });
                          }}
                          disabled={d.dataset_id === datasetId}
                        >
                          {d.dataset_id === datasetId ? "✓ Aktif" : "Pilih"}
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => doDelete(d.dataset_id, d.filename)}
                        >
                          Hapus
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
