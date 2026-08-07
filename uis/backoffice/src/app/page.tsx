import {
  sampleLocations,
  sampleMenuItems,
  sampleSales,
  sampleWasteRecords,
} from "../../../../packages/data-utils/src/data/sampleData.js";
import {
  findTopSellingItems,
  rankLocationsByPerformance,
} from "../../../../packages/data-utils/src/utils/transformations.js";

export default function BackofficeHome() {
  const ranking = rankLocationsByPerformance(sampleLocations, sampleSales, sampleWasteRecords, sampleMenuItems);
  const topItems = findTopSellingItems(sampleSales, sampleMenuItems, 3);

  return (
    <main className="mx-auto max-w-3xl space-y-10 px-6 py-10">
      <div>
        <h1 className="text-2xl font-bold">Panel de Operaciones</h1>
        <p className="mt-1 text-sm text-gray-500">
          Datos calculados con las utilidades de{" "}
          <code className="rounded bg-gray-100 px-1 py-0.5">packages/data-utils</code> (Hito 2), sobre los
          datos de ejemplo de las 14 ubicaciones de Brasaland.
        </p>
      </div>

      <section>
        <h2 className="text-lg font-semibold">Ranking de locaciones por performance</h2>
        <ol className="mt-4 divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
          {ranking.map((entry, index) => (
            <li key={entry.location.id} className="flex items-center justify-between px-4 py-3">
              <span>
                <span className="mr-3 text-sm text-gray-400">#{index + 1}</span>
                {entry.location.name}
              </span>
              <span className="font-semibold text-orange-700">{entry.score}</span>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h2 className="text-lg font-semibold">Top 3 ítems más vendidos</h2>
        <ol className="mt-4 divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
          {topItems.map((entry, index) => (
            <li key={entry.item.id} className="flex items-center justify-between px-4 py-3">
              <span>
                <span className="mr-3 text-sm text-gray-400">#{index + 1}</span>
                {entry.item.name}
              </span>
              <span className="font-semibold text-orange-700">{entry.totalSold} unidades</span>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
