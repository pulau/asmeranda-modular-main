"use client";

/**
 * Layout utama — sidebar di kiri (desktop) atau bawah (mobile).
 */
import { useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import { rehydrateWorkflow } from "@/lib/workflow-store";

export default function MainLayout({ children }) {
  useEffect(() => {
    rehydrateWorkflow();
  }, []);

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">{children}</main>
    </div>
  );
}
