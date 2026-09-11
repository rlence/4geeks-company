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

// Misma convención que COUNTRY_CURRENCY en services/api/models.py —
// usada para completar el campo `currency` requerido por
// inbound_order_created (event-schemas.json) a partir de Ingredient.country.
export const COUNTRY_CURRENCY: Record<CountryCode, "COP" | "USD"> = {
  CO: "COP",
  US: "USD",
};

export const REASON_LABELS: Record<ExitReason, string> = {
  consumption: "Consumo",
  waste: "Merma",
};

export const REASON_OPTIONS = Object.keys(REASON_LABELS) as ExitReason[];

export const LOCATION_OPTIONS = Array.from({ length: 14 }, (_, index) => index + 1);

// Umbral arbitrario para la demo (no viene del backend): reutilizado por
// StockBadge.tsx (nivel visual) y por la instrumentación de telemetría de
// stock_threshold_triggered — no hay campo de stock mínimo en el spec de
// Ingredient, ver docs/telemetry/telemetry-plan.md.
export const LOW_STOCK_THRESHOLD = 20;
