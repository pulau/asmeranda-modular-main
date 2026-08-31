"use client";

/**
 * Halaman login - placeholder. Pada F7 auth flow akan diimplementasi
 * dengan JWT + httpOnly cookie. Untuk MVP tampilkan info saja.
 */
import { useT } from "@/lib/i18n";
import { useWorkflow } from "@/lib/workflow-store";

export default function LoginPage() {
  const lang = useWorkflow((s) => s.language) || "id";
  const tr = useT(lang);
  return (
    <div>
      <h1>Login</h1>
      <p style={{ color: "#64748b" }}>
        Auth flow (JWT + OTP) akan diimplementasi di F7. Untuk MVP,
        Asmeranda Backend saat ini berjalan tanpa autentikasi.
      </p>
    </div>
  );
}
