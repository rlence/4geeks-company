import { getToken } from "@/lib/session";
import type { Incident, IncidentInput, IncidentPage, IncidentStatus } from "@/types/incident";

async function request<T>(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const token = getToken();
  if (!token) throw new Error("Inicia sesión para gestionar tus incidencias.");
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/incidents${path}`, {
    ...init, signal, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    if (response.status === 401) throw new Error("Tu sesión ha caducado. Vuelve a iniciar sesión.");
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "No se pudo completar la operación. Revisa los datos e inténtalo de nuevo.");
  }
  return response.json();
}
export const getIncidents = (filters: URLSearchParams, signal: AbortSignal) => request<IncidentPage>(`?${filters}`, {}, signal);
export const getIncident = (id: string, signal: AbortSignal) => request<Incident>(`/${encodeURIComponent(id)}`, {}, signal);
export const createIncident = (input: IncidentInput) => request<Incident>("", { method: "POST", body: JSON.stringify(input) });
export const changeIncidentStatus = (id: number, status: IncidentStatus, expected_version: number) => request<Incident>(`/${id}/status`, { method: "PATCH", body: JSON.stringify({ status, expected_version }) });
