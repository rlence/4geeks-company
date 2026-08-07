import type { Supplier, SupplierCreateInput, SupplierListFilters, SupplierStatus } from "@/types/supplier";

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

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
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    signal,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

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

export const getSuppliers = (filters: SupplierListFilters, signal?: AbortSignal): Promise<Supplier[]> => {
  const params = new URLSearchParams();
  if (filters.country) params.set("country", filters.country);
  if (filters.category) params.set("category", filters.category);
  const query = params.toString();
  return request<Supplier[]>(`/suppliers${query ? `?${query}` : ""}`, undefined, signal);
};

export const createSupplier = (input: SupplierCreateInput): Promise<Supplier> =>
  request<Supplier>("/suppliers", { method: "POST", body: JSON.stringify(input) });

export const updateSupplierRate = (id: number, rate_per_unit: number): Promise<Supplier> =>
  request<Supplier>(`/suppliers/${id}/rate`, {
    method: "PATCH",
    body: JSON.stringify({ rate_per_unit }),
  });

export const updateSupplierStatus = (id: number, status: SupplierStatus): Promise<Supplier> =>
  request<Supplier>(`/suppliers/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
