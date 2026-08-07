"use client";

import { useState } from "react";
import { CATEGORY_LABELS, CATEGORY_OPTIONS, COUNTRY_CURRENCY, COUNTRY_OPTIONS, COUNTRY_LABELS } from "@/lib/labels";
import { createSupplier, getApiErrorMessage } from "@/lib/suppliersApi";
import type { Category, Country, Supplier } from "@/types/supplier";

interface SupplierFormProps {
  onCreated: (created: Supplier) => void;
}

const emptyState = {
  name: "",
  country: "Colombia" as Country,
  categories: [] as Category[],
  rate_per_unit: "",
  contact_email: "",
  notes: "",
};

export const SupplierForm = ({ onCreated }: SupplierFormProps) => {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyState);
  const [clientError, setClientError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const toggleCategory = (category: Category) => {
    setForm((prev) => ({
      ...prev,
      categories: prev.categories.includes(category)
        ? prev.categories.filter((c) => c !== category)
        : [...prev.categories, category],
    }));
  };

  const resetAndClose = () => {
    setForm(emptyState);
    setClientError(null);
    setServerError(null);
    setOpen(false);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setClientError(null);
    setServerError(null);

    const rate = Number(form.rate_per_unit);
    if (!form.name.trim()) {
      setClientError("El nombre es requerido");
      return;
    }
    if (form.categories.length === 0) {
      setClientError("Selecciona al menos una categoría");
      return;
    }
    if (!Number.isFinite(rate) || rate <= 0) {
      setClientError("La tarifa debe ser un número mayor a 0");
      return;
    }

    setSubmitting(true);
    try {
      const created = await createSupplier({
        name: form.name.trim(),
        country: form.country,
        categories: form.categories,
        rate_per_unit: rate,
        currency: COUNTRY_CURRENCY[form.country],
        status: "active",
        contact_email: form.contact_email.trim() || undefined,
        notes: form.notes.trim() || undefined,
      });
      onCreated(created);
      resetAndClose();
    } catch (err) {
      setServerError(getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="whitespace-nowrap rounded bg-orange-700 px-4 py-2 text-sm text-white"
      >
        + Nuevo proveedor
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 space-y-4 rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Registrar proveedor</h2>
        <button type="button" onClick={resetAndClose} className="text-sm text-gray-500 hover:underline">
          Cancelar
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          Nombre
          <input
            type="text"
            value={form.name}
            onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
            className="rounded border px-3 py-2"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          País
          <select
            value={form.country}
            onChange={(event) => setForm((prev) => ({ ...prev, country: event.target.value as Country }))}
            className="rounded border px-3 py-2"
          >
            {COUNTRY_OPTIONS.map((country) => (
              <option key={country} value={country}>
                {COUNTRY_LABELS[country]}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          Tarifa por unidad ({COUNTRY_CURRENCY[form.country]})
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={form.rate_per_unit}
            onChange={(event) => setForm((prev) => ({ ...prev, rate_per_unit: event.target.value }))}
            className="rounded border px-3 py-2"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          Email de contacto (opcional)
          <input
            type="email"
            value={form.contact_email}
            onChange={(event) => setForm((prev) => ({ ...prev, contact_email: event.target.value }))}
            className="rounded border px-3 py-2"
          />
        </label>
      </div>

      <fieldset>
        <legend className="mb-1 text-sm">Categorías</legend>
        <div className="flex flex-wrap gap-3">
          {CATEGORY_OPTIONS.map((category) => (
            <label key={category} className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={form.categories.includes(category)}
                onChange={() => toggleCategory(category)}
              />
              {CATEGORY_LABELS[category]}
            </label>
          ))}
        </div>
      </fieldset>

      <label className="flex flex-col gap-1 text-sm">
        Notas internas (opcional)
        <textarea
          value={form.notes}
          onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
          className="rounded border px-3 py-2"
          rows={2}
        />
      </label>

      {clientError && <p className="text-sm text-red-600">{clientError}</p>}
      {serverError && <p className="text-sm text-red-600">{serverError}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="rounded bg-orange-700 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {submitting ? "Guardando…" : "Registrar proveedor"}
      </button>
    </form>
  );
};
