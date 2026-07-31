import { sampleLocations, sampleMenuItems, sampleSales, sampleWasteRecords } from "./data/sampleData.js";
import {
  filterActiveLocations,
  filterMenuItemsByCategory,
  filterSalesByDateRange,
  filterSalesByLocation,
  sortLocationsByCapacity,
  sortMenuItemsByPrice,
} from "./utils/collections.js";
import { binarySearchLocationByCapacity, findLocationById, findMenuItemByName } from "./utils/search.js";
import {
  calculateAverageTicket,
  calculateCountryComparison,
  calculateDailyRevenue,
  calculateLocationMargin,
  calculateWasteCost,
  convertCurrency,
  countSalesByPaymentMethod,
  findTopSellingItems,
  groupWasteByReason,
  rankLocationsByPerformance,
  scoreLocationPerformance,
} from "./utils/transformations.js";
import { validateLocation, validateMenuItem, validateSaleTransaction } from "./utils/validations.js";

console.log("=== Colecciones ===");
console.log("Ventas en Medellín:", filterSalesByLocation(sampleSales, "LOC-MEDELLIN-01").length);
console.log(
  "Ventas 15-mar-2024:",
  filterSalesByDateRange(sampleSales, new Date("2024-03-15"), new Date("2024-03-15")).length
);
console.log("Ítems de categoría Meat:", filterMenuItemsByCategory(sampleMenuItems, "Meat").map((i) => i.name));
console.log("Locaciones activas:", filterActiveLocations(sampleLocations).length);

const sortedByCapacity = sortLocationsByCapacity(sampleLocations, "asc");
console.log("Locaciones por capacidad (asc):", sortedByCapacity.map((l) => l.seatingCapacity));
console.log("Ítems por precio USD (desc):", sortMenuItemsByPrice(sampleMenuItems, "USD", "desc").map((i) => i.name));

console.log("\n=== Búsqueda ===");
console.log("findLocationById existente:", findLocationById(sampleLocations, "LOC-MEDELLIN-01")?.name);
console.log("findLocationById inexistente:", findLocationById(sampleLocations, "LOC-NO-EXISTE"));
console.log("findMenuItemByName case-insensitive:", findMenuItemByName(sampleMenuItems, "picanha 250g")?.id);
console.log("binarySearch capacidad 100:", binarySearchLocationByCapacity(sortedByCapacity, 100));
console.log("binarySearch capacidad inexistente:", binarySearchLocationByCapacity(sortedByCapacity, 999));

console.log("\n=== Financieros ===");
console.log("Ingreso diario 15-mar (USD):", calculateDailyRevenue(sampleSales, new Date("2024-03-15"), "USD"));
console.log("Margen Medellín (USD):", calculateLocationMargin(sampleSales, sampleMenuItems, "LOC-MEDELLIN-01", "USD"));
console.log("Costo desperdicio Medellín (USD):", calculateWasteCost(sampleWasteRecords, "LOC-MEDELLIN-01", "USD"));
console.log("100 USD a COP:", convertCurrency(100, "USD", "COP"));
console.log("400000 COP a USD:", convertCurrency(400000, "COP", "USD"));

console.log("\n=== Scoring de performance ===");
console.log(
  "Score Medellín:",
  scoreLocationPerformance(sampleLocations[0]!, sampleSales, sampleWasteRecords, sampleMenuItems)
);
console.log(
  "Ranking:",
  rankLocationsByPerformance(sampleLocations, sampleSales, sampleWasteRecords, sampleMenuItems).map(
    (r) => `${r.location.name}: ${r.score}`
  )
);

console.log("\n=== Agregaciones y reportes ===");
console.log("Ventas por método de pago:", countSalesByPaymentMethod(sampleSales));
console.log("Ticket promedio (USD):", calculateAverageTicket(sampleSales, "USD"));
console.log(
  "Top 2 ítems más vendidos:",
  findTopSellingItems(sampleSales, sampleMenuItems, 2).map((t) => `${t.item.name}: ${t.totalSold}`)
);
console.log(
  "Desperdicio por razón:",
  Object.entries(groupWasteByReason(sampleWasteRecords)).map(([reason, records]) => `${reason}: ${records.length}`)
);
console.log("Comparación por país:", calculateCountryComparison(sampleSales, sampleLocations, sampleMenuItems));

console.log("\n=== Validaciones ===");
console.log("Ítem válido:", validateMenuItem(sampleMenuItems[0]!));
console.log(
  "Ítem inválido (2 errores esperados):",
  validateMenuItem({ ...sampleMenuItems[0]!, name: "", prepTimeMinutes: 90 })
);
console.log("Venta válida:", validateSaleTransaction(sampleSales[0]!));
console.log(
  "Venta inválida:",
  validateSaleTransaction({ ...sampleSales[0]!, quantity: 0, waiterName: "" })
);
console.log("Locación válida:", validateLocation(sampleLocations[0]!));
console.log(
  "Locación inválida:",
  validateLocation({ ...sampleLocations[0]!, openingYear: 1990, seatingCapacity: 0 })
);
