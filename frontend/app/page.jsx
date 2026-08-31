"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

const WORKFLOW_STEPS = [
  {
    step: 1,
    icon: "📂",
    key: "nav.upload",
    href: "/data-upload",
    desc: "upload.subtitle",
    can: "eda",
    always: true,
  },
  {
    step: 2,
    icon: "🔍",
    key: "nav.eda",
    href: "/eda",
    desc: "eda.subtitle",
    can: "eda",
  },
  {
    step: 3,
    icon: "⚙️",
    key: "nav.preprocessing",
    href: "/preprocessing",
    desc: "preprocessing.subtitle",
    can: "preprocessing",
  },
  {
    step: 4,
    icon: "🧠",
    key: "nav.training",
    href: "/training",
    desc: "training.subtitle",
    can: "training",
  },
  {
    step: 5,
    icon: "📊",
    key: "nav.shap",
    href: "/shap",
    desc: "shap.subtitle",
    can: "shap",
  },
  {
    step: 6,
    icon: "🔬",
    key: "nav.lime",
    href: "/lime",
    desc: "lime.subtitle",
    can: "shap",
  },
  {
    step: 7,
    icon: "📈",
    key: "nav.timeseries",
    href: "/timeseries",
    desc: "timeseries.subtitle",
    can: "timeseries",
  },
];

function StatusBadge({ status }) {
  if (status === "loading") {
    return (
      <span className="flex-gap-2" style={{ fontSize: "var(--text-sm)", color: "var(--color-slate-400)" }}>
        <span className="status-dot status-dot--loading" />
        Memeriksa koneksi...
      </span>
    );
  }
  if (status === "ok") {
    return (
      <span className="flex-gap-2" style={{ fontSize: "var(--text-sm)", color: "var(--color-success-600)", fontWeight: 600 }}>
        <span className="status-dot status-dot--ok" />
        Backend terhubung
      </span>
    );
  }
  return (
    <span className="flex-gap-2" style={{ fontSize: "var(--text-sm)", color: "var(--color-error-600)", fontWeight: 600 }}>
      <span className="status-dot status-dot--error" />
      Backend tidak tersedia
    </span>
  );
}

export default function HomePage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  const canProceedTo = useWorkflow((s) => s.canProceedTo);
  const datasetId = useWorkflow((s) => s.datasetId);

  const [status, setStatus] = useState("loading");
  const [info, setInfo] = useState(null);

  useEffect(() => {
    let cancelled = false;
    let timer = null;

    const checkHealth = async () => {
      try {
        const r = await fetch("/health");
        if (cancelled) return;
        if (r.ok) {
          const data = await r.json();
          setInfo(data);
          if (data.status === "ok") {
            setStatus("ok");
            return;
          }
        }
        setStatus("error");
        timer = setTimeout(checkHealth, 3000);
      } catch {
        if (cancelled) return;
        setStatus("error");
        timer = setTimeout(checkHealth, 3000);
      }
    };

    checkHealth();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  return (
    <div>
      {/* ── Page Header ── */}
      <div className="page-header">
        <h1 className="page-title">
          🤖 {tr("app.title")}
        </h1>
        <p className="page-subtitle">{tr("app.subtitle")}</p>
      </div>

      {/* ── Status Grid ── */}
      <div className="grid-2 mb-6">
        {/* Backend Status Card */}
        <div className="card">
          <div className="flex-between mb-4">
            <h2 className="card-title" style={{ margin: 0 }}>Backend API</h2>
            <span style={{ fontSize: "24px" }}>⚡</span>
          </div>
          <StatusBadge status={status} />
          {status === "ok" && info && (
            <div
              style={{
                marginTop: "12px",
                padding: "10px 12px",
                background: "var(--color-slate-50)",
                borderRadius: "var(--radius-md)",
                fontSize: "var(--text-xs)",
                color: "var(--color-slate-500)",
                fontFamily: "var(--font-mono)",
              }}
            >
              Python {info.python_version} • {info.platform?.split("-")[0]}
            </div>
          )}
          {status === "error" && (
            <p
              style={{
                marginTop: "8px",
                fontSize: "var(--text-xs)",
                color: "var(--color-slate-500)",
              }}
            >
              Pastikan backend FastAPI berjalan di{" "}
              <code>http://localhost:8000</code>
            </p>
          )}
        </div>

        {/* Dataset Status Card */}
        <div className="card">
          <div className="flex-between mb-4">
            <h2 className="card-title" style={{ margin: 0 }}>Dataset Aktif</h2>
            <span style={{ fontSize: "24px" }}>🗂️</span>
          </div>
          {datasetId ? (
            <>
              <span
                className="flex-gap-2"
                style={{ fontSize: "var(--text-sm)", color: "var(--color-success-600)", fontWeight: 600 }}
              >
                <span className="status-dot status-dot--ok" />
                Dataset tersedia
              </span>
              <div
                style={{
                  marginTop: "12px",
                  padding: "10px 12px",
                  background: "var(--color-slate-50)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "var(--text-xs)",
                  color: "var(--color-slate-500)",
                }}
              >
                <code>{datasetId.slice(0, 16)}...</code>
              </div>
            </>
          ) : (
            <>
              <span
                className="flex-gap-2"
                style={{ fontSize: "var(--text-sm)", color: "var(--color-slate-400)" }}
              >
                <span className="status-dot status-dot--loading" />
                Belum ada dataset
              </span>
              <div style={{ marginTop: "12px" }}>
                <Link href="/data-upload" className="btn btn-primary btn-sm">
                  📂 Upload Dataset
                </Link>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Workflow Steps ── */}
      <div className="card">
        <div className="flex-between" style={{ marginBottom: "var(--space-6)" }}>
          <div>
            <h2 className="card-title" style={{ margin: 0 }}>Alur Kerja ML</h2>
            <p className="card-subtitle" style={{ margin: 0, marginTop: "4px" }}>
              Ikuti langkah-langkah berikut secara berurutan
            </p>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {WORKFLOW_STEPS.map((s, idx) => {
            const enabled = s.always || canProceedTo(s.can);
            const done = !s.always && canProceedTo(s.can);

            return (
              <div
                key={s.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-4)",
                  padding: "var(--space-4)",
                  borderRadius: "var(--radius-lg)",
                  background: done
                    ? "var(--color-success-50)"
                    : enabled
                    ? "var(--color-slate-50)"
                    : "transparent",
                  border: `1px solid ${
                    done
                      ? "var(--color-success-100)"
                      : enabled
                      ? "var(--color-slate-200)"
                      : "var(--color-slate-100)"
                  }`,
                  opacity: !enabled && !s.always ? 0.55 : 1,
                  transition: "all var(--transition-normal)",
                }}
              >
                {/* Step number */}
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "50%",
                    background: done
                      ? "var(--color-success-500)"
                      : enabled
                      ? "var(--color-primary-100)"
                      : "var(--color-slate-200)",
                    color: done
                      ? "#fff"
                      : enabled
                      ? "var(--color-primary-700)"
                      : "var(--color-slate-400)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: "700",
                    fontSize: "var(--text-sm)",
                    flexShrink: 0,
                  }}
                >
                  {done ? "✓" : s.step}
                </div>

                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontWeight: 600,
                      fontSize: "var(--text-sm)",
                      color: enabled
                        ? "var(--color-slate-800)"
                        : "var(--color-slate-400)",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <span>{s.icon}</span>
                    {tr(s.key)}
                  </div>
                </div>

                {enabled && (
                  <Link
                    href={s.href}
                    className="btn btn-secondary btn-sm"
                    style={{ flexShrink: 0 }}
                  >
                    {done ? "Lihat →" : "Mulai →"}
                  </Link>
                )}
                {!enabled && (
                  <span
                    style={{
                      fontSize: "var(--text-xs)",
                      color: "var(--color-slate-400)",
                      flexShrink: 0,
                    }}
                  >
                    🔒 Terkunci
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
