export type Country = "Colombia" | "USA";
export type Currency = "COP" | "USD";

export type Category =
  | "carne"
  | "verduras_y_hortalizas"
  | "salsas_y_condimentos"
  | "bebidas"
  | "packaging"
  | "productos_limpieza"
  | "lacteos"
  | "carbon_y_combustible";

export type SupplierStatus = "active" | "suspended";

export interface Supplier {
  id: number;
  name: string;
  country: Country;
  categories: Category[];
  rate_per_unit: number;
  currency: Currency;
  status: SupplierStatus;
  contact_email: string | null;
  notes: string | null;
  updated_at: string;
}

export interface SupplierCreateInput {
  name: string;
  country: Country;
  categories: Category[];
  rate_per_unit: number;
  currency: Currency;
  status: SupplierStatus;
  contact_email?: string;
  notes?: string;
}

export interface SupplierListFilters {
  country?: Country;
  category?: Category;
}
