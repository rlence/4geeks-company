"use client";

import { useState } from "react";
import { patchCandidate } from "@/lib/api";
import { STAGE_LABELS, STATUS_LABELS } from "@/lib/labels";
import type { Candidate, CandidateStage, CandidateStatus } from "@/types/tracker";

interface Props {
  candidate: Candidate;
  onUpdated: (candidate: Candidate) => void;
}

export const StatusStageControls = ({ candidate, onUpdated }: Props) => {
  const [saving, setSaving] = useState<"status" | "stage" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handlePatch = async (
    patch: { status?: CandidateStatus; stage?: CandidateStage },
    field: "status" | "stage"
  ) => {
    setSaving(field);
    setError(null);
    try {
      const updated = await patchCandidate(candidate.id, patch);
      onUpdated(updated);
    } catch {
      setError("No se pudo actualizar. Intenta de nuevo.");
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="flex flex-wrap items-end gap-4">
      <label className="flex flex-col text-sm">
        Estado
        <select
          value={candidate.status}
          disabled={saving === "status"}
          onChange={(event) => handlePatch({ status: event.target.value as CandidateStatus }, "status")}
          className="rounded border px-3 py-2"
        >
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col text-sm">
        Etapa
        <select
          value={candidate.stage}
          disabled={saving === "stage"}
          onChange={(event) => handlePatch({ stage: event.target.value as CandidateStage }, "stage")}
          className="rounded border px-3 py-2"
        >
          {Object.entries(STAGE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {saving && <span className="text-sm text-gray-500">Guardando…</span>}
      {error && <span className="text-sm text-red-600">{error}</span>}
    </div>
  );
};
