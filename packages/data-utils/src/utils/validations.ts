import type { Location, MenuItem, SaleTransaction } from "../types/models.js";

export const validateMenuItem = (item: MenuItem): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (item.basePrice.USD <= 0 || item.basePrice.COP <= 0) {
    errors.push("basePrice debe ser mayor a 0 en ambas monedas");
  }
  if (item.ingredientCost.USD <= 0 || item.ingredientCost.COP <= 0) {
    errors.push("ingredientCost debe ser mayor a 0 en ambas monedas");
  }
  if (item.prepTimeMinutes <= 0 || item.prepTimeMinutes > 60) {
    errors.push("prepTimeMinutes debe estar entre 1 y 60");
  }
  if (!item.name.trim()) {
    errors.push("name no debe estar vacío");
  }
  if (!item.isAvailableInColombia && !item.isAvailableInUSA) {
    errors.push("El ítem debe estar disponible en al menos un país");
  }

  return { valid: errors.length === 0, errors };
};

export const validateSaleTransaction = (sale: SaleTransaction): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (sale.quantity <= 0) {
    errors.push("quantity debe ser mayor a 0");
  }
  if (sale.totalPrice.USD <= 0 || sale.totalPrice.COP <= 0) {
    errors.push("totalPrice debe ser mayor a 0 en ambas monedas");
  }
  if (!sale.waiterName.trim()) {
    errors.push("waiterName no debe estar vacío");
  }

  return { valid: errors.length === 0, errors };
};

export const validateLocation = (location: Location): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];
  const currentYear = new Date().getFullYear();

  if (location.openingYear < 2008 || location.openingYear > currentYear) {
    errors.push(`openingYear debe estar entre 2008 y ${currentYear}`);
  }
  if (location.seatingCapacity <= 0) {
    errors.push("seatingCapacity debe ser mayor a 0");
  }
  if (location.staffCount <= 0) {
    errors.push("staffCount debe ser mayor a 0");
  }
  if (location.monthlyRentCost.USD <= 0 || location.monthlyRentCost.COP <= 0) {
    errors.push("monthlyRentCost debe ser mayor a 0 en ambas monedas");
  }
  if (location.averageMonthlyUtilities.USD <= 0 || location.averageMonthlyUtilities.COP <= 0) {
    errors.push("averageMonthlyUtilities debe ser mayor a 0 en ambas monedas");
  }

  return { valid: errors.length === 0, errors };
};
