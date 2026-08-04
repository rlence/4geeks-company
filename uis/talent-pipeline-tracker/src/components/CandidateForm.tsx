"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createCandidate, replaceCandidate } from "@/lib/api";
import type { Candidate, CandidateInput } from "@/types/tracker";

interface Props {
  mode: "create" | "edit";
  candidate?: Candidate;
}

const emptyForm: CandidateInput = {
  full_name: "",
  email: "",
  phone: "",
  position: "",
  linkedin_url: "",
  cv_url: "",
  experience_years: 0,
};

export const CandidateForm = ({ mode, candidate }: Props) => {
  const router = useRouter();
  const [form, setForm] = useState<CandidateInput>(
    candidate
      ? {
          full_name: candidate.full_name,
          email: candidate.email,
          phone: candidate.phone,
          position: candidate.position,
          linkedin_url: candidate.linkedin_url ?? "",
          cv_url: candidate.cv_url ?? "",
          experience_years: candidate.experience_years,
        }
      : emptyForm
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const validate = (): boolean => {
    const nextErrors: Record<string, string> = {};
    if (!form.full_name.trim()) nextErrors.full_name = "El nombre completo es obligatorio";
    if (!/^\S+@\S+\.\S+$/.test(form.email)) nextErrors.email = "Ingresa un email válido";
    if (!form.phone.trim()) nextErrors.phone = "El teléfono es obligatorio";
    if (!form.position.trim()) nextErrors.position = "El puesto es obligatorio";
    if (form.experience_years < 0) nextErrors.experience_years = "Los años de experiencia no pueden ser negativos";
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    setSubmitError(null);

    const payload: CandidateInput = {
      ...form,
      linkedin_url: form.linkedin_url?.trim() || null,
      cv_url: form.cv_url?.trim() || null,
    };

    try {
      const result = mode === "create" ? await createCandidate(payload) : await replaceCandidate(candidate!.id, payload);
      router.push(`/candidates/${result.id}`);
    } catch {
      setSubmitError("No se pudo guardar la candidatura. Intenta de nuevo.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-lg space-y-4">
      <div>
        <label className="block text-sm font-medium">Nombre completo</label>
        <input
          value={form.full_name}
          onChange={(event) => setForm({ ...form, full_name: event.target.value })}
          className="w-full rounded border px-3 py-2"
        />
        {errors.full_name && <p className="text-sm text-red-600">{errors.full_name}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium">Email</label>
        <input
          value={form.email}
          onChange={(event) => setForm({ ...form, email: event.target.value })}
          className="w-full rounded border px-3 py-2"
        />
        {errors.email && <p className="text-sm text-red-600">{errors.email}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium">Teléfono</label>
        <input
          value={form.phone}
          onChange={(event) => setForm({ ...form, phone: event.target.value })}
          className="w-full rounded border px-3 py-2"
        />
        {errors.phone && <p className="text-sm text-red-600">{errors.phone}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium">Puesto</label>
        <input
          value={form.position}
          onChange={(event) => setForm({ ...form, position: event.target.value })}
          className="w-full rounded border px-3 py-2"
        />
        {errors.position && <p className="text-sm text-red-600">{errors.position}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium">LinkedIn (opcional)</label>
        <input
          value={form.linkedin_url ?? ""}
          onChange={(event) => setForm({ ...form, linkedin_url: event.target.value })}
          className="w-full rounded border px-3 py-2"
        />
      </div>

      <div>
        <label className="block text-sm font-medium">Enlace al CV (opcional)</label>
        <input
          value={form.cv_url ?? ""}
          onChange={(event) => setForm({ ...form, cv_url: event.target.value })}
          className="w-full rounded border px-3 py-2"
        />
      </div>

      <div>
        <label className="block text-sm font-medium">Años de experiencia</label>
        <input
          type="number"
          min={0}
          value={form.experience_years}
          onChange={(event) => setForm({ ...form, experience_years: Number(event.target.value) })}
          className="w-full rounded border px-3 py-2"
        />
        {errors.experience_years && <p className="text-sm text-red-600">{errors.experience_years}</p>}
      </div>

      {submitError && <p className="text-red-600">{submitError}</p>}

      <button type="submit" disabled={submitting} className="rounded bg-orange-700 px-4 py-2 text-white">
        {submitting ? "Guardando…" : mode === "create" ? "Registrar candidatura" : "Guardar cambios"}
      </button>
    </form>
  );
};
