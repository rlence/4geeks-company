"use client";
import Link from "next/link";
import { useState } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useIncidents } from "@/hooks/useIncidents";
import { categoryLabels, statusLabels } from "@/types/incident";

function List() {
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [offset, setOffset] = useState(0);
  const state = useIncidents(status, category, offset);
  return <main className="mx-auto max-w-5xl space-y-6 p-6">
    <div className="flex flex-wrap items-center justify-between gap-4"><div><h1 className="text-2xl font-bold">Mis incidencias</h1><p className="text-gray-600">Consulta tus tickets y sigue su estado.</p></div><Link className="rounded bg-orange-700 px-4 py-2 text-white" href="/incidents/new">Nueva incidencia</Link></div>
    <div className="flex flex-wrap gap-4"><label>Estado<select className="ml-2 rounded border p-2" value={status} onChange={e => { setStatus(e.target.value); setOffset(0); }}><option value="">Todos</option>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Categoría<select className="ml-2 rounded border p-2" value={category} onChange={e => { setCategory(e.target.value); setOffset(0); }}><option value="">Todas</option>{Object.entries(categoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div>
    {state.status === "loading" && <p role="status">Cargando incidencias…</p>}
    {state.status === "error" && <p role="alert" className="text-red-700">{state.error} <Link href="/login" className="underline">Iniciar sesión</Link></p>}
    {state.status === "success" && state.data && <><p>{state.data.total} incidencias</p>{!state.data.items.length && <p>No hay incidencias con estos filtros.</p>}<ul className="divide-y rounded border bg-white">{state.data.items.map(i => <li key={i.id} className="p-4"><Link className="font-semibold text-orange-800 underline" href={`/incidents/${i.id}`}>#{i.id} · {i.title}</Link><p className="mt-1 text-sm text-gray-600">{statusLabels[i.status]} · {categoryLabels[i.category]} · {new Date(i.updated_at).toLocaleString("es")}</p></li>)}</ul><div className="flex gap-4"><button className="rounded border p-2 disabled:opacity-40" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 20))}>Anterior</button><button className="rounded border p-2 disabled:opacity-40" disabled={offset + 20 >= state.data.total} onClick={() => setOffset(offset + 20)}>Siguiente</button></div></>}
  </main>;
}
export default function Page() { return useRequireAuth() ? <List /> : <p className="p-6">Comprobando sesión…</p>; }
