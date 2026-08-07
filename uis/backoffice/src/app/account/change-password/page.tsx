"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { changePassword, getApiErrorMessage } from "@/lib/authApi";
import { getToken } from "@/lib/session";

type Status = "idle" | "submitting" | "success" | "error";

export default function ChangePasswordPage() {
  const [hasSession, setHasSession] = useState<boolean | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage is only readable client-side, after mount
    setHasSession(Boolean(getToken()));
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("La nueva contraseña y la confirmación no coinciden");
      return;
    }

    setStatus("submitting");
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setStatus("success");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(getApiErrorMessage(err));
      setStatus("error");
    }
  };

  if (hasSession === null) return null;

  if (!hasSession) {
    return (
      <main className="mx-auto max-w-sm space-y-4 px-6 py-16">
        <h1 className="text-2xl font-bold">Cambiar contraseña</h1>
        <p className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-700">
          Necesitas iniciar sesión para cambiar tu contraseña.{" "}
          <Link href="/login" className="text-orange-700 hover:underline">
            Ir a iniciar sesión
          </Link>
          .
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-sm space-y-6 px-6 py-16">
      <h1 className="text-2xl font-bold">Cambiar contraseña</h1>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
        <label className="flex flex-col gap-1 text-sm">
          Contraseña actual
          <input
            type="password"
            required
            disabled={status === "submitting"}
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            className="rounded border px-3 py-2 disabled:opacity-50"
          />
        </label>

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
          Confirmar nueva contraseña
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

        {status === "success" && <p className="text-sm text-green-700">Contraseña actualizada correctamente.</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={status === "submitting"}
          className="w-full rounded bg-orange-700 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {status === "submitting" ? "Guardando…" : "Cambiar contraseña"}
        </button>
      </form>
    </main>
  );
}
