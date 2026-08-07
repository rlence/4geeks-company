"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { getApiErrorMessage, resetPassword } from "@/lib/authApi";

type Status = "idle" | "submitting" | "error";

const ResetPasswordForm = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }

    setStatus("submitting");
    try {
      await resetPassword({ token, new_password: newPassword });
      router.push("/login?reset=success");
    } catch (err) {
      setError(getApiErrorMessage(err));
      setStatus("error");
    }
  };

  return (
    <main className="mx-auto max-w-sm space-y-6 px-6 py-16">
      <h1 className="text-2xl font-bold">Restablecer contraseña</h1>

      {!token ? (
        <p className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-red-600">
          Este enlace no incluye un token válido.{" "}
          <Link href="/forgot-password" className="text-orange-700 hover:underline">
            Solicita uno nuevo
          </Link>
          .
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
          <label className="flex flex-col gap-1 text-sm">
            Nueva contraseña
            <input
              type="password"
              required
              minLength={8}
              disabled={status === "submitting"}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              className="rounded border px-3 py-2 disabled:opacity-50"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            Confirmar contraseña
            <input
              type="password"
              required
              minLength={8}
              disabled={status === "submitting"}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              className="rounded border px-3 py-2 disabled:opacity-50"
            />
          </label>

          {error && (
            <div className="space-y-1">
              <p className="text-sm text-red-600">{error}</p>
              {status === "error" && (
                <p className="text-sm">
                  <Link href="/forgot-password" className="text-orange-700 hover:underline">
                    Volver a solicitar el enlace
                  </Link>
                </p>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={status === "submitting"}
            className="w-full rounded bg-orange-700 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {status === "submitting" ? "Guardando…" : "Restablecer contraseña"}
          </button>
        </form>
      )}
    </main>
  );
};

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-sm px-6 py-16">Cargando…</main>}>
      <ResetPasswordForm />
    </Suspense>
  );
}
