import type { Location, MenuCategory, MenuItem, SaleTransaction } from "../types/models.js";
import { endOfDay, startOfDay } from "./format.js";

export const filterSalesByLocation = (sales: SaleTransaction[], locationId: string): SaleTransaction[] =>
  sales.filter((sale) => sale.locationId === locationId);

export const filterSalesByDateRange = (
  sales: SaleTransaction[],
  startDate: Date,
  endDate: Date
): SaleTransaction[] => {
  const start = startOfDay(startDate);
  const end = endOfDay(endDate);
  return sales.filter((sale) => sale.timestamp >= start && sale.timestamp <= end);
};

export const filterMenuItemsByCategory = (items: MenuItem[], category: MenuCategory): MenuItem[] =>
  items.filter((item) => item.category === category);

export const filterActiveLocations = (locations: Location[]): Location[] =>
  locations.filter((location) => location.status === "Active");

export const sortLocationsByCapacity = (locations: Location[], order: "asc" | "desc"): Location[] => {
  const sorted = [...locations].sort((a, b) => a.seatingCapacity - b.seatingCapacity);
  return order === "asc" ? sorted : sorted.reverse();
};

export const sortMenuItemsByPrice = (
  items: MenuItem[],
  currency: "USD" | "COP",
  order: "asc" | "desc"
): MenuItem[] => {
  const sorted = [...items].sort((a, b) => a.basePrice[currency] - b.basePrice[currency]);
  return order === "asc" ? sorted : sorted.reverse();
};
