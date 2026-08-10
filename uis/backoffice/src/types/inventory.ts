export type CountryCode = "CO" | "US";

export type IngredientCategory = "meat" | "produce" | "sauce" | "beverage" | "packaging" | "cleaning";

export type ExitReason = "consumption" | "waste";

export interface Ingredient {
  id: number;
  name: string;
  sku: string;
  unit: string;
  category: IngredientCategory;
  country: CountryCode;
  current_stock: number;
}

export interface IngredientEntryInput {
  ingredient_id: number;
  quantity: number;
  supplier_name: string;
  location_id: number;
  user_uuid: string;
}

export interface IngredientEntry extends IngredientEntryInput {
  id: number;
  created_at: string;
}

export interface IngredientExitInput {
  ingredient_id: number;
  quantity: number;
  reason: ExitReason;
  location_id: number;
  user_uuid: string;
}

export interface IngredientExit extends IngredientExitInput {
  id: number;
  created_at: string;
}

export interface InventoryOrder {
  id: number;
  type: "inbound" | "outbound";
  ingredient_id: number;
  ingredient_name: string;
  quantity: number;
  unit: string;
  reason?: ExitReason;
  supplier_name?: string;
  location_id: number;
  created_at: string;
  user_uuid: string;
}
