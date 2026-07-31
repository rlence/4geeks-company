import { sampleLocations, sampleMenuItems, sampleSales, sampleWasteRecords } from "./data/sampleData.js";
import { filterSalesByLocation, sortLocationsByCapacity } from "./utils/collections.js";
import { binarySearchLocationByCapacity } from "./utils/search.js";
import { calculateCountryComparison, findTopSellingItems, rankLocationsByPerformance } from "./utils/transformations.js";
import { validateMenuItem } from "./utils/validations.js";

const output = document.querySelector<HTMLPreElement>("#output");

const render = (label: string, data: unknown): void => {
  if (!output) return;
  output.textContent = `${label}\n\n${JSON.stringify(data, null, 2)}`;
};

document.querySelector("#btn-filter")?.addEventListener("click", () => {
  render("Ventas en LOC-MEDELLIN-01", filterSalesByLocation(sampleSales, "LOC-MEDELLIN-01"));
});

document.querySelector("#btn-sort")?.addEventListener("click", () => {
  const sorted = sortLocationsByCapacity(sampleLocations, "asc");
  render("Locaciones ordenadas por capacidad (asc)", sorted);
});

document.querySelector("#btn-binary-search")?.addEventListener("click", () => {
  const sorted = sortLocationsByCapacity(sampleLocations, "asc");
  const index = binarySearchLocationByCapacity(sorted, 100);
  render("Índice de la locación con capacidad 100", { index });
});

document.querySelector("#btn-rank")?.addEventListener("click", () => {
  const ranking = rankLocationsByPerformance(sampleLocations, sampleSales, sampleWasteRecords, sampleMenuItems);
  render(
    "Ranking de performance",
    ranking.map((r) => ({ location: r.location.name, score: r.score }))
  );
});

document.querySelector("#btn-top-items")?.addEventListener("click", () => {
  const topItems = findTopSellingItems(sampleSales, sampleMenuItems, 3);
  render(
    "Top 3 ítems más vendidos",
    topItems.map((t) => ({ item: t.item.name, totalSold: t.totalSold }))
  );
});

document.querySelector("#btn-country")?.addEventListener("click", () => {
  render("Comparación por país", calculateCountryComparison(sampleSales, sampleLocations, sampleMenuItems));
});

document.querySelector("#btn-validate")?.addEventListener("click", () => {
  const invalidItem = { ...sampleMenuItems[0]!, name: "", prepTimeMinutes: 90 };
  render("Validación de un ítem inválido", validateMenuItem(invalidItem));
});
