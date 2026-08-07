"use client";

import { useState } from "react";
import { forgotPassword, getApiErrorMessage } from "@/lib/authApi";

type Status = "idle" | "submitting" | "success" | "error";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setStatus("submitting");
    setError(null);

    try {
      await forgotPassword({ email });
      setStatus("success");
    } catch (err) {
      setError(getApiErrorMessage(err));
      setStatus("error");
    }
  };

  return (
    <main className="mx-auto max-w-sm space-y-6 px-6 py-16">
      <h1 className="text-2xl font-bold">¿Olvidaste tu contraseña?</h1>

      {status === "success" ? (
        <p className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-700">
          Si esa dirección está registrada, recibirás un enlace en breve.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
          <label className="flex flex-col gap-1 text-sm">
            Email
            <input
              type="email"
              required
              disabled={status === "submitting"}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="rounded border px-3 py-2 disabled:opacity-50"
            />
          </label>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={status === "submitting"}
            className="w-full rounded bg-orange-700 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {status === "submitting" ? "Enviando…" : "Enviar enlace de restablecimiento"}
          </button>
        </form>
      )}
    </main>
  );
}
