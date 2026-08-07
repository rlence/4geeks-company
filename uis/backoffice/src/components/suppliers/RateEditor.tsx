"use client";

import { useState } from "react";
import { getApiErrorMessage, updateSupplierRate } from "@/lib/suppliersApi";
import type { Supplier } from "@/types/supplier";

interface RateEditorProps {
  supplier: Supplier;
  onUpdated: (updated: Supplier) => void;
}

export const RateEditor = ({ supplier, onUpdated }: RateEditorProps) => {
  const [value, setValue] = useState(String(supplier.rate_per_unit));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isDirty = value !== String(supplier.rate_per_unit);

  const handleSave = async () => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("La tarifa debe ser un número mayor a 0");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await updateSupplierRate(supplier.id, parsed);
      onUpdated(updated);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <input
          type="number"
          step="0.01"
          min="0.01"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="w-24 rounded border px-2 py-1 text-sm"
        />
        <span className="text-xs text-gray-500">{supplier.currency}</span>
        {isDirty && (
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-orange-700 px-2 py-1 text-xs text-white disabled:opacity-50"
          >
            {saving ? "Guardando…" : "Guardar"}
          </button>
        )}
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
};
