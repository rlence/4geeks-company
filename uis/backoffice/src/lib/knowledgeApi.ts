import type { KnowledgeQueryResponse } from "@/types/knowledge";
import { reportApiLatency, track } from "@/lib/telemetry";

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export const getApiErrorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : "Ha ocurrido un error inesperado";

export const askKnowledgeBase = async (
  question: string,
  signal?: AbortSignal,
): Promise<KnowledgeQueryResponse> => {
  const path = "/knowledge/query";
  const start = performance.now();

  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  reportApiLatency("POST", path, performance.now() - start, !response.ok);

  if (!response.ok) {
    if (response.status >= 500) {
      track("api_request_failed", { route: path, method: "POST", status_code: response.status });
    }
    // 503 es el caso esperado cuando Qdrant o el proveedor de modelos no
    // responden: se distingue para que el gerente sepa que es un problema
    // del servicio, no que la base de conocimiento no tenga el dato.
    const message =
      response.status === 503
        ? "La base de conocimiento no está disponible en este momento. Inténtalo de nuevo en unos minutos."
        : `Error ${response.status} al consultar la base de conocimiento`;
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as KnowledgeQueryResponse;
};
