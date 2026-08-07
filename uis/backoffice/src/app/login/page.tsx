"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getApiErrorMessage, login } from "@/lib/authApi";
import { setToken } from "@/lib/session";

type Status = "idle" | "submitting" | "error";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setStatus("submitting");
    setError(null);

    try {
      const { access_token } = await login({ email, password });
      setToken(access_token);
      router.push("/");
    } catch (err) {
      setError(getApiErrorMessage(err));
      setStatus("error");
    }
  };

  return (
    <main className="mx-auto max-w-sm space-y-6 px-6 py-16">
      <h1 className="text-2xl font-bold">Iniciar sesión</h1>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="rounded border px-3 py-2"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          Contraseña
          <input
            type="password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded border px-3 py-2"
          />
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={status === "submitting"}
          className="w-full rounded bg-orange-700 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {status === "submitting" ? "Entrando…" : "Entrar"}
        </button>

        <p className="text-center text-sm">
          <Link href="/forgot-password" className="text-orange-700 hover:underline">
            ¿Olvidaste tu contraseña?
          </Link>
        </p>
      </form>
    </main>
  );
}
