import { getCurrentUserId, getToken } from "@/lib/session";
import type {
  Ingredient,
  IngredientEntry,
  IngredientEntryInput,
  IngredientExit,
  IngredientExitInput,
  InventoryOrder,
} from "@/types/inventory";

const API_URL = process.env.NEXT_PUBLIC_INVENTORY_API_URL as string;

type ValidationDetail = { loc: (string | number)[]; msg: string; type: string };

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string | ValidationDetail[],
  ) {
    super(message);
  }
}

const request = async <T>(path: string, init?: RequestInit, signal?: AbortSignal): Promise<T> => {
  const token = getToken();
  const headers: HeadersInit = { "Content-Type": "application/json", ...init?.headers };
  if (token) (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_URL}${path}`, { ...init, signal, headers });

  if (!response.ok) {
    let detail: string | ValidationDetail[] | undefined;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = undefined;
    }
    throw new ApiError(`Error ${response.status} al comunicarse con la API`, response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
};

export const getApiErrorMessage = (error: unknown): string => {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (Array.isArray(error.detail)) return error.detail.map((item) => item.msg).join(" — ");
  }
  return error instanceof Error ? error.message : "Ha ocurrido un error inesperado";
};

export const getIngredients = (signal?: AbortSignal): Promise<Ingredient[]> =>
  request<Ingredient[]>("/inventory/products", undefined, signal);

export const getIngredient = (id: number, signal?: AbortSignal): Promise<Ingredient> =>
  request<Ingredient>(`/inventory/products/${id}`, undefined, signal);

export type IngredientEntryFormInput = Omit<IngredientEntryInput, "user_uuid">;
export type IngredientExitFormInput = Omit<IngredientExitInput, "user_uuid">;

export const createInboundOrder = (input: IngredientEntryFormInput): Promise<IngredientEntry> =>
  request<IngredientEntry>("/inventory/orders/inbound", {
    method: "POST",
    body: JSON.stringify({ ...input, user_uuid: getCurrentUserId() ?? "" }),
  });

export const createOutboundOrder = (input: IngredientExitFormInput): Promise<IngredientExit> =>
  request<IngredientExit>("/inventory/orders/outbound", {
    method: "POST",
    body: JSON.stringify({ ...input, user_uuid: getCurrentUserId() ?? "" }),
  });

export const getOrders = (signal?: AbortSignal): Promise<InventoryOrder[]> =>
  request<InventoryOrder[]>("/inventory/orders", undefined, signal);
