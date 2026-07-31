import type {
  Country,
  CountryMetrics,
  Location,
  MenuItem,
  PaymentMethod,
  SaleTransaction,
  WasteReason,
  WasteRecord,
} from "../types/models.js";
import { filterSalesByLocation } from "./collections.js";
import { daysSinceOpening, isSameDay, round2, USD_TO_COP_RATE } from "./format.js";

// --- Financieros ---

export const calculateDailyRevenue = (
  sales: SaleTransaction[],
  date: Date,
  currency: "USD" | "COP"
): number => {
  const total = sales
    .filter((sale) => isSameDay(sale.timestamp, date))
    .reduce((sum, sale) => sum + sale.totalPrice[currency], 0);
  return round2(total);
};

export const calculateLocationMargin = (
  sales: SaleTransaction[],
  menuItems: MenuItem[],
  locationId: string,
  currency: "USD" | "COP"
): number => {
  const locationSales = filterSalesByLocation(sales, locationId);
  const totalRevenue = locationSales.reduce((sum, sale) => sum + sale.totalPrice[currency], 0);
  if (totalRevenue === 0) return 0;

  const totalIngredientCost = locationSales.reduce((sum, sale) => {
    const menuItem = menuItems.find((item) => item.id === sale.itemId);
    const unitCost = menuItem ? menuItem.ingredientCost[currency] : 0;
    return sum + unitCost * sale.quantity;
  }, 0);

  return round2(((totalRevenue - totalIngredientCost) / totalRevenue) * 100);
};

export const calculateWasteCost = (
  wasteRecords: WasteRecord[],
  locationId: string,
  currency: "USD" | "COP"
): number => {
  const total = wasteRecords
    .filter((record) => record.locationId === locationId)
    .reduce((sum, record) => sum + record.cost[currency], 0);
  return round2(total);
};

export const convertCurrency = (
  amount: number,
  fromCurrency: "USD" | "COP",
  toCurrency: "USD" | "COP"
): number => {
  if (fromCurrency === toCurrency) return amount;
  const amountInUSD = fromCurrency === "USD" ? amount : amount / USD_TO_COP_RATE;
  const converted = toCurrency === "USD" ? amountInUSD : amountInUSD * USD_TO_COP_RATE;
  return round2(converted);
};

// --- Scoring de performance de locación ---

export const scoreLocationPerformance = (
  location: Location,
  sales: SaleTransaction[],
  wasteRecords: WasteRecord[],
  menuItems: MenuItem[]
): number => {
  const locationSales = filterSalesByLocation(sales, location.id);
  const locationWaste = wasteRecords.filter((record) => record.locationId === location.id);

  const totalRevenueUSD = locationSales.reduce((sum, sale) => sum + sale.totalPrice.USD, 0);
  const totalWasteCostUSD = locationWaste.reduce((sum, record) => sum + record.cost.USD, 0);

  const avgDailyRevenueUSD = totalRevenueUSD / daysSinceOpening(location.openingYear);
  const revenueScore = Math.min(40, (avgDailyRevenueUSD / 1000) * 40);

  const efficiencyScore = Math.min(30, (locationSales.length / location.seatingCapacity) * 30);

  const wastePercentage = totalRevenueUSD === 0 ? 0 : (totalWasteCostUSD / totalRevenueUSD) * 100;
  const wasteScore = Math.max(0, 20 - wastePercentage * 2);

  const marginScore = Math.min(10, calculateLocationMargin(sales, menuItems, location.id, "USD") / 10);

  return round2(revenueScore + efficiencyScore + wasteScore + marginScore);
};

export const rankLocationsByPerformance = (
  locations: Location[],
  sales: SaleTransaction[],
  wasteRecords: WasteRecord[],
  menuItems: MenuItem[]
): Array<{ location: Location; score: number }> =>
  locations
    .map((location) => ({
      location,
      score: scoreLocationPerformance(location, sales, wasteRecords, menuItems),
    }))
    .sort((a, b) => b.score - a.score);

// --- Agregaciones y reportes ---

export const countSalesByPaymentMethod = (sales: SaleTransaction[]): Record<PaymentMethod, number> => {
  const counts: Record<PaymentMethod, number> = {
    Cash: 0,
    "Credit card": 0,
    "Debit card": 0,
    "Digital wallet": 0,
  };
  sales.forEach((sale) => {
    counts[sale.paymentMethod] += 1;
  });
  return counts;
};

export const calculateAverageTicket = (sales: SaleTransaction[], currency: "USD" | "COP"): number => {
  if (sales.length === 0) return 0;
  const total = sales.reduce((sum, sale) => sum + sale.totalPrice[currency], 0);
  return round2(total / sales.length);
};

export const findTopSellingItems = (
  sales: SaleTransaction[],
  menuItems: MenuItem[],
  topN: number
): Array<{ item: MenuItem; totalSold: number }> => {
  const soldByItemId = new Map<string, number>();
  sales.forEach((sale) => {
    soldByItemId.set(sale.itemId, (soldByItemId.get(sale.itemId) ?? 0) + sale.quantity);
  });

  return menuItems
    .map((item) => ({ item, totalSold: soldByItemId.get(item.id) ?? 0 }))
    .sort((a, b) => b.totalSold - a.totalSold)
    .slice(0, topN);
};

export const groupWasteByReason = (wasteRecords: WasteRecord[]): Record<WasteReason, WasteRecord[]> => {
  const groups: Record<WasteReason, WasteRecord[]> = {
    Expired: [],
    "Cooking error": [],
    "Customer return": [],
    Damage: [],
    Other: [],
  };
  wasteRecords.forEach((record) => {
    groups[record.reason].push(record);
  });
  return groups;
};

export const calculateCountryComparison = (
  sales: SaleTransaction[],
  locations: Location[],
  _menuItems: MenuItem[]
): { Colombia: CountryMetrics; USA: CountryMetrics } => {
  const buildMetrics = (country: Country): CountryMetrics => {
    const countryLocations = locations.filter((location) => location.country === country);
    const locationIds = new Set(countryLocations.map((location) => location.id));
    const countrySales = sales.filter((sale) => locationIds.has(sale.locationId));
    const totalLocations = countryLocations.length;

    const totalRevenueUSD = countrySales.reduce((sum, sale) => sum + sale.totalPrice.USD, 0);
    const totalRevenueCOP = countrySales.reduce((sum, sale) => sum + sale.totalPrice.COP, 0);

    return {
      totalLocations,
      totalRevenue: { USD: round2(totalRevenueUSD), COP: round2(totalRevenueCOP) },
      averageRevenuePerLocation: {
        USD: round2(totalLocations === 0 ? 0 : totalRevenueUSD / totalLocations),
        COP: round2(totalLocations === 0 ? 0 : totalRevenueCOP / totalLocations),
      },
      totalSales: countrySales.length,
    };
  };

  return { Colombia: buildMetrics("Colombia"), USA: buildMetrics("USA") };
};
