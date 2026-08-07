"use client";

import { useState } from "react";
import { getApiErrorMessage, updateSupplierStatus } from "@/lib/suppliersApi";
import type { Supplier } from "@/types/supplier";

interface StatusToggleProps {
  supplier: Supplier;
  onUpdated: (updated: Supplier) => void;
}

export const StatusToggle = ({ supplier, onUpdated }: StatusToggleProps) => {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isActive = supplier.status === "active";

  const handleToggle = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateSupplierStatus(supplier.id, isActive ? "suspended" : "active");
      onUpdated(updated);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <button
        onClick={handleToggle}
        disabled={saving}
        className={`rounded px-2 py-1 text-xs font-medium disabled:opacity-50 ${
          isActive
            ? "border border-red-300 text-red-700 hover:bg-red-50"
            : "border border-green-300 text-green-700 hover:bg-green-50"
        }`}
      >
        {saving ? "Actualizando…" : isActive ? "Suspender" : "Activar"}
      </button>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
};
