"use client";

import { Suspense } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CandidateFilters } from "@/components/CandidateFilters";
import { useCandidates } from "@/hooks/useCandidates";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/labels";

const CandidatesPageContent = () => {
  const { status, candidates, total, error, page } = useCandidates();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const totalPages = Math.max(1, Math.ceil(total / 20));

  const goToPage = (nextPage: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(nextPage));
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="mb-1 text-2xl font-bold">Brasaland — Pipeline de Candidaturas</h1>
      <p className="mb-4 text-gray-600">Asistente de Dirección · People &amp; Talent</p>

      <div className="mb-4 flex items-center justify-between gap-4">
        <CandidateFilters />
        <Link href="/candidates/new" className="whitespace-nowrap rounded bg-orange-700 px-4 py-2 text-white">
          + Nueva candidatura
        </Link>
      </div>

      {status === "loading" && <p>Cargando candidaturas…</p>}
      {status === "error" && <p className="text-red-600">{error}</p>}

      {status === "success" && (
        <>
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2">Nombre</th>
                <th className="py-2">Puesto</th>
                <th className="py-2">Estado</th>
                <th className="py-2">Etapa</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr key={candidate.id} className="border-b hover:bg-gray-50">
                  <td className="py-2">
                    <Link href={`/candidates/${candidate.id}`} className="text-orange-700 hover:underline">
                      {candidate.full_name}
                    </Link>
                  </td>
                  <td className="py-2">{candidate.position}</td>
                  <td className="py-2">{STATUS_LABELS[candidate.status]}</td>
                  <td className="py-2">{STAGE_LABELS[candidate.stage]}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {candidates.length === 0 && <p className="mt-4 text-gray-500">No hay candidaturas con estos filtros.</p>}

          <div className="mt-4 flex items-center justify-between">
            <span className="text-sm text-gray-500">
              Página {page} de {totalPages} · {total} candidaturas
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1}
                className="rounded border px-3 py-1 disabled:opacity-50"
              >
                Anterior
              </button>
              <button
                onClick={() => goToPage(page + 1)}
                disabled={page >= totalPages}
                className="rounded border px-3 py-1 disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
          </div>
        </>
      )}
    </main>
  );
};

export default function CandidatesPage() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-5xl p-6">Cargando…</main>}>
      <CandidatesPageContent />
    </Suspense>
  );
}
