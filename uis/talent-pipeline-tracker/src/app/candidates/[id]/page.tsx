"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { NotesPanel } from "@/components/NotesPanel";
import { StatusStageControls } from "@/components/StatusStageControls";
import { getCandidate } from "@/lib/api";
import type { Candidate } from "@/types/tracker";

type FetchStatus = "loading" | "success" | "error";

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset to loading when the route id changes
    setStatus("loading");
    getCandidate(id, controller.signal)
      .then((result) => {
        setCandidate(result);
        setStatus("success");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "No se pudo cargar la candidatura.");
        setStatus("error");
      });
    return () => controller.abort();
  }, [id]);

  if (status === "loading") return <main className="mx-auto max-w-3xl p-6">Cargando…</main>;
  if (status === "error" || !candidate) {
    return <main className="mx-auto max-w-3xl p-6 text-red-600">{error}</main>;
  }

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-6">
      <Link href="/" className="text-orange-700 hover:underline">
        ← Volver al listado
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{candidate.full_name}</h1>
          <p className="text-gray-600">{candidate.position}</p>
        </div>
        <Link href={`/candidates/${candidate.id}/edit`} className="rounded border px-4 py-2">
          Editar datos
        </Link>
      </div>

      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-gray-500">Email</dt>
          <dd>{candidate.email}</dd>
        </div>
        <div>
          <dt className="text-gray-500">Teléfono</dt>
          <dd>{candidate.phone}</dd>
        </div>
        <div>
          <dt className="text-gray-500">LinkedIn</dt>
          <dd>
            {candidate.linkedin_url ? (
              <a href={candidate.linkedin_url} target="_blank" rel="noreferrer" className="text-orange-700 hover:underline">
                Ver perfil
              </a>
            ) : (
              "No disponible"
            )}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">CV</dt>
          <dd>
            {candidate.cv_url ? (
              <a href={candidate.cv_url} target="_blank" rel="noreferrer" className="text-orange-700 hover:underline">
                Ver CV
              </a>
            ) : (
              "No disponible"
            )}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500">Años de experiencia</dt>
          <dd>{candidate.experience_years}</dd>
        </div>
        <div>
          <dt className="text-gray-500">Fecha de aplicación</dt>
          <dd>{new Date(candidate.applied_at).toLocaleDateString("es-CO")}</dd>
        </div>
      </dl>

      <StatusStageControls candidate={candidate} onUpdated={setCandidate} />

      <NotesPanel candidateId={candidate.id} />
    </main>
  );
}
