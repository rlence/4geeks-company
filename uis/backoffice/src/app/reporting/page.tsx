"use client";

import { useWeeklyPerformance } from "@/hooks/useWeeklyPerformance";
import { COUNTRY_LABELS } from "@/lib/inventoryLabels";
import type { CountryCode } from "@/types/inventory";

const formatMoney = (amount: number, currency: string) =>
  new Intl.NumberFormat("es-CO", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);

const formatRatio = (ratio: number) => `${(ratio * 100).toFixed(1)}%`;

export default function ReportingPage() {
  const { status, report, error } = useWeeklyPerformance();

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="mb-1 text-2xl font-bold">Reporte Semanal de Costo y Merma por Local</h1>
      <p className="mb-4 text-gray-600">Para Mariana (CEO) y Felipe (Director de Operaciones)</p>

      {status === "loading" && <p>Cargando reporte…</p>}
      {status === "error" && <p className="text-red-600">{error}</p>}

      {status === "success" && report && (
        <>
          <p className="mb-4 text-sm text-gray-600">
            Semana del:{" "}
            <strong>{report.week_start ?? "sin datos todavía"}</strong>
          </p>

          {report.locations.length === 0 ? (
            <p className="text-gray-500">Sin datos para esta semana.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-4 py-3">Local</th>
                    <th className="px-4 py-3">País</th>
                    <th className="px-4 py-3">Costo de compra por local</th>
                    <th className="px-4 py-3">Costo de merma por local</th>
                    <th className="px-4 py-3">Ratio de merma</th>
                    <th className="px-4 py-3">Frecuencia de quiebre de stock</th>
                    <th className="px-4 py-3">Frecuencia de alertas de precio</th>
                  </tr>
                </thead>
                <tbody>
                  {report.locations.map((location) => (
                    <tr key={location.location_id} className="border-b border-gray-100 last:border-0">
                      <td className="px-4 py-3 font-medium">Local {location.location_id}</td>
                      <td className="px-4 py-3">{COUNTRY_LABELS[location.country as CountryCode]}</td>
                      <td className="px-4 py-3">{formatMoney(location.total_purchase_cost, location.currency)}</td>
                      <td className="px-4 py-3">{formatMoney(location.total_waste_cost, location.currency)}</td>
                      <td className="px-4 py-3">{formatRatio(location.waste_ratio)}</td>
                      <td className="px-4 py-3">{location.stockout_events_count}</td>
                      <td className="px-4 py-3">{location.price_alert_events_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </main>
  );
}
