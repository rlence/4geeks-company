"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CandidateForm } from "@/components/CandidateForm";
import { getCandidate } from "@/lib/api";
import type { Candidate } from "@/types/tracker";

type FetchStatus = "loading" | "success" | "error";

export default function EditCandidatePage() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [candidate, setCandidate] = useState<Candidate | null>(null);

  useEffect(() => {
    getCandidate(id)
      .then((result) => {
        setCandidate(result);
        setStatus("success");
      })
      .catch(() => setStatus("error"));
  }, [id]);

  if (status === "loading") return <main className="mx-auto max-w-3xl p-6">Cargando…</main>;
  if (status === "error" || !candidate) {
    return <main className="mx-auto max-w-3xl p-6 text-red-600">No se pudo cargar la candidatura.</main>;
  }

  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="mb-4 text-2xl font-bold">Editar candidatura</h1>
      <CandidateForm mode="edit" candidate={candidate} />
    </main>
  );
}
