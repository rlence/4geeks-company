"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { getIncident, changeIncidentStatus } from "@/lib/incidentsApi";
import { categoryLabels, statusLabels, type Incident, type IncidentStatus } from "@/types/incident";

function Detail({ id }: { id: string }) {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- estado de consulta al cambiar id o recargar
    setStatus("loading");
    getIncident(id, controller.signal).then(data => { setIncident(data); setStatus("success"); setError(""); }).catch(err => { if (!controller.signal.aborted) { setError(err.message); setStatus("error"); } });
    return () => controller.abort();
  }, [id, reload]);
  async function change(next: IncidentStatus) {
    if (!incident) return;
    setBusy(true); setError("");
    try { setIncident(await changeIncidentStatus(incident.id, next, incident.version)); }
    catch (err) { setError(err instanceof Error ? err.message : "No se pudo cambiar el estado"); }
    finally { setBusy(false); }
  }
  const next: IncidentStatus[] = incident?.status === "open" ? ["in_progress", "resolved"] : incident?.status === "in_progress" ? ["resolved"] : ["in_progress"];
  return <main className="mx-auto max-w-3xl space-y-5 p-6"><Link href="/incidents" className="text-orange-800 underline">← Mis incidencias</Link>
    {status === "loading" && <p role="status">Cargando incidencia…</p>}{error && <p role="alert" className="text-red-700">{error}</p>}
    {status === "success" && incident && <article className="space-y-5 rounded border bg-white p-6"><h1 className="text-2xl font-bold">#{incident.id} · {incident.title}</h1><p>{statusLabels[incident.status]} · {categoryLabels[incident.category]}</p><p className="whitespace-pre-wrap">{incident.description}</p><p className="text-sm text-gray-600">Actualizada: {new Date(incident.updated_at).toLocaleString("es")}</p>{incident.resolved_at && <p>Resuelta: {new Date(incident.resolved_at).toLocaleString("es")}</p>}<div className="flex flex-wrap gap-3">{next.map(s => <button key={s} disabled={busy} onClick={() => change(s)} className="rounded bg-orange-700 px-4 py-2 text-white disabled:opacity-50">{s === "in_progress" && incident.status === "resolved" ? "Reabrir" : `Marcar: ${statusLabels[s]}`}</button>)}</div></article>}
    <button disabled={busy} onClick={() => setReload(n => n + 1)} className="rounded border p-2">Recargar detalle</button></main>;
}
export default function Page() { const ready = useRequireAuth(); const { id } = useParams<{ id: string }>(); return ready ? <Detail id={id} /> : <p className="p-6">Comprobando sesión…</p>; }
