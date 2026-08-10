import type { CountryCode, ExitReason, IngredientCategory } from "@/types/inventory";

export const CATEGORY_LABELS: Record<IngredientCategory, string> = {
  meat: "Carne",
  produce: "Verduras y hortalizas",
  sauce: "Salsas",
  beverage: "Bebidas",
  packaging: "Packaging",
  cleaning: "Productos de limpieza",
};

export const CATEGORY_OPTIONS = Object.keys(CATEGORY_LABELS) as IngredientCategory[];

export const COUNTRY_LABELS: Record<CountryCode, string> = {
  CO: "Colombia",
  US: "Estados Unidos",
};

export const COUNTRY_OPTIONS = Object.keys(COUNTRY_LABELS) as CountryCode[];

export const REASON_LABELS: Record<ExitReason, string> = {
  consumption: "Consumo",
  waste: "Merma",
};

export const REASON_OPTIONS = Object.keys(REASON_LABELS) as ExitReason[];

export const LOCATION_OPTIONS = Array.from({ length: 14 }, (_, index) => index + 1);
