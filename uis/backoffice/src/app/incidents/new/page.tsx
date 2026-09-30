"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { createIncident } from "@/lib/incidentsApi";
import { categoryLabels, type IncidentCategory } from "@/types/incident";

export default function Page() {
  const ready = useRequireAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!ready) return <p className="p-6">Comprobando sesión…</p>;
  return <main className="mx-auto max-w-2xl space-y-6 p-6"><Link href="/incidents" className="text-orange-800 underline">← Mis incidencias</Link><h1 className="text-2xl font-bold">Nueva incidencia</h1><form className="space-y-5 rounded border bg-white p-6" onSubmit={async e => {
    e.preventDefault(); const data = new FormData(e.currentTarget); setBusy(true); setError("");
    try { const incident = await createIncident({ title: String(data.get("title")).trim(), description: String(data.get("description")).trim(), category: data.get("category") as IncidentCategory }); router.push(`/incidents/${incident.id}`); }
    catch (err) { setError(err instanceof Error ? err.message : "No se pudo guardar"); setBusy(false); }
  }}><label className="block">Título<input name="title" required minLength={5} maxLength={160} className="mt-2 block w-full rounded border p-2" /></label><label className="block">Descripción<textarea name="description" required minLength={10} maxLength={4000} rows={5} className="mt-2 block w-full rounded border p-2" /></label><label className="block">Categoría<select name="category" className="ml-3 rounded border p-2">{Object.entries(categoryLabels).map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>{error && <p role="alert" className="text-red-700">{error}</p>}<button disabled={busy} className="rounded bg-orange-700 px-4 py-2 text-white disabled:opacity-50">{busy ? "Guardando…" : "Crear incidencia"}</button></form></main>;
}
