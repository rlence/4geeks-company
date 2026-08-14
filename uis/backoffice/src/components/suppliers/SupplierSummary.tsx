"use client";

import { useMemo } from "react";
import type { Supplier } from "@/types/supplier";

interface SupplierSummaryProps {
  suppliers: Supplier[];
}

export const SupplierSummary = ({ suppliers }: SupplierSummaryProps) => {
  // Depende solo de `suppliers`, no del texto de búsqueda del padre —
  // así, escribir en el buscador re-renderiza este componente pero NO
  // vuelve a recorrer todas las filas para recalcular el resumen.
  const stats = useMemo(() => {
    const byCountry: Record<string, number> = {};
    const rateTotals: Record<string, { total: number; count: number }> = {};

    for (const supplier of suppliers) {
      byCountry[supplier.country] = (byCountry[supplier.country] ?? 0) + 1;
      const bucket = rateTotals[supplier.currency] ?? { total: 0, count: 0 };
      bucket.total += supplier.rate_per_unit;
      bucket.count += 1;
      rateTotals[supplier.currency] = bucket;
    }

    const avgRate = Object.fromEntries(
      Object.entries(rateTotals).map(([currency, { total, count }]) => [currency, total / count]),
    );

    return { total: suppliers.length, byCountry, avgRate };
  }, [suppliers]);

  return (
    <div className="mb-4 flex flex-wrap gap-4 rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-600">
      <span>
        <strong className="text-gray-900">{stats.total}</strong> proveedores
      </span>
      {Object.entries(stats.byCountry).map(([country, count]) => (
        <span key={country}>
          {country}: <strong className="text-gray-900">{count}</strong>
        </span>
      ))}
      {Object.entries(stats.avgRate).map(([currency, avg]) => (
        <span key={currency}>
          Tarifa media {currency}: <strong className="text-gray-900">{avg.toFixed(2)}</strong>
        </span>
      ))}
    </div>
  );
};
