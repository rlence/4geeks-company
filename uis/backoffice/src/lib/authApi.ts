import type {
  ChangePasswordInput,
  ForgotPasswordInput,
  LoginInput,
  ResetPasswordInput,
  TokenResponse,
} from "@/types/auth";
import { getToken } from "@/lib/session";

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

const request = async <T>(path: string, init?: RequestInit, authenticated = false): Promise<T> => {
  const headers: HeadersInit = { "Content-Type": "application/json", ...init?.headers };
  if (authenticated) {
    const token = getToken();
    if (token) (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });

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

export const login = (input: LoginInput): Promise<TokenResponse> =>
  request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(input) });

export const forgotPassword = (input: ForgotPasswordInput): Promise<void> =>
  request<void>("/auth/forgot-password", { method: "POST", body: JSON.stringify(input) });

export const resetPassword = (input: ResetPasswordInput): Promise<void> =>
  request<void>("/auth/reset-password", { method: "POST", body: JSON.stringify(input) });

export const changePassword = (input: ChangePasswordInput): Promise<void> =>
  request<void>("/auth/change-password", { method: "POST", body: JSON.stringify(input) }, true);
