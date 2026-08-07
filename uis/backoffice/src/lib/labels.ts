import type { Category, Country, SupplierStatus } from "@/types/supplier";

export const STATUS_LABELS: Record<SupplierStatus, string> = {
  active: "Activo",
  suspended: "Suspendido",
};

export const COUNTRY_LABELS: Record<Country, string> = {
  Colombia: "Colombia",
  USA: "USA",
};

export const CATEGORY_LABELS: Record<Category, string> = {
  carne: "Carne",
  verduras_y_hortalizas: "Verduras y hortalizas",
  salsas_y_condimentos: "Salsas y condimentos",
  bebidas: "Bebidas",
  packaging: "Packaging",
  productos_limpieza: "Productos de limpieza",
  lacteos: "Lácteos",
  carbon_y_combustible: "Carbón y combustible",
};

export const CATEGORY_OPTIONS = Object.keys(CATEGORY_LABELS) as Category[];
export const COUNTRY_OPTIONS = Object.keys(COUNTRY_LABELS) as Country[];

export const COUNTRY_CURRENCY: Record<Country, "COP" | "USD"> = {
  Colombia: "COP",
  USA: "USD",
};
