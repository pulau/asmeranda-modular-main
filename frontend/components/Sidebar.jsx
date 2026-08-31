"use client";

/**
 * Sidebar navigasi — tetap di setiap halaman.
 * Item disable jika workflow step belum siap.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useWorkflow } from "@/lib/workflow-store";
import { useT } from "@/lib/i18n";

const STEPS = [
  {
    href: "/data-upload",
    key: "nav.upload",
    can: "eda",
    icon: "📂",
    alwaysEnabled: true,
  },
  { href: "/eda", key: "nav.eda", can: "eda", icon: "🔍" },
  {
    href: "/preprocessing",
    key: "nav.preprocessing",
    can: "preprocessing",
    icon: "⚙️",
  },
  { href: "/clustering", key: "nav.clustering", can: "preprocessing", icon: "🎯" },
  { href: "/training", key: "nav.training", can: "training", icon: "🧠" },
  { href: "/optimization", key: "nav.optimization", can: "training", icon: "🔧" },
  { href: "/shap", key: "nav.shap", can: "shap", icon: "📊" },
  { href: "/lime", key: "nav.lime", can: "shap", icon: "🔬" },
  {
    href: "/timeseries",
    key: "nav.timeseries",
    can: "timeseries",
    icon: "📈",
  },
  {
    href: "/advanced-ml",
    key: "nav.advanced_ml",
    can: "preprocessing",
    icon: "🚀",
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const lang = useWorkflow((s) => s.language) || "id";
  const canProceedTo = useWorkflow((s) => s.canProceedTo);
  const setLang = useWorkflow((s) => s.set);
  const datasetId = useWorkflow((s) => s.datasetId);
  const tr = useT(lang);

  // Hitung progress berapa langkah sudah selesai
  const completedSteps = STEPS.filter((s) => !s.alwaysEnabled && canProceedTo(s.can)).length;
  const progressPct = Math.round((completedSteps / (STEPS.length - 1)) * 100);

  return (
    <aside className="app-sidebar">
      {/* ── Header / Brand ── */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">🤖</div>
          <div>
            <div className="sidebar-title">{tr("app.title")}</div>
          </div>
        </div>
        <div className="sidebar-subtitle">{tr("app.subtitle")}</div>

        {/* Progress bar workflow */}
        {datasetId && (
          <div style={{ marginTop: "12px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "10px",
                color: "var(--sidebar-muted)",
                marginBottom: "4px",
              }}
            >
              <span>Progres Workflow</span>
              <span>{progressPct}%</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Navigation ── */}
      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Workflow</div>
        {STEPS.map((step, idx) => {
          const enabled = step.alwaysEnabled || canProceedTo(step.can);
          const active = pathname === step.href;
          const done = !step.alwaysEnabled && canProceedTo(step.can);

          return (
            <Link
              key={step.href}
              href={enabled ? step.href : "#"}
              className={[
                "sidebar-link",
                active ? "sidebar-link--active" : "",
                !enabled ? "sidebar-link--disabled" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={(e) => !enabled && e.preventDefault()}
              title={
                !enabled ? "Selesaikan langkah sebelumnya terlebih dahulu" : ""
              }
            >
              <span className="sidebar-link-icon">{step.icon}</span>
              <span>
                {idx + 1}. {tr(step.key)}
              </span>
              {done && !active && (
                <span className="sidebar-link-badge">✓</span>
              )}
              {!enabled && (
                <span
                  className="sidebar-link-badge"
                  style={{ background: "var(--sidebar-muted)" }}
                >
                  🔒
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* ── Footer — Language ── */}
      <div className="sidebar-footer">
        <label className="sidebar-lang-label">🌐 Bahasa / Language</label>
        <select
          className="sidebar-lang-select"
          value={lang}
          onChange={(e) => setLang({ language: e.target.value })}
        >
          <option value="id">🇮🇩 Bahasa Indonesia</option>
          <option value="en">🇺🇸 English</option>
        </select>

        <div
          style={{
            marginTop: "12px",
            fontSize: "10px",
            color: "var(--sidebar-muted)",
            textAlign: "center",
            lineHeight: 1.5,
          }}
        >
          © PT. Asmer Sahabat Sukses
        </div>
      </div>
    </aside>
  );
}
