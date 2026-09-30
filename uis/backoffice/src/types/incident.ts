export type IncidentStatus = "open" | "in_progress" | "resolved";
export type IncidentCategory = "operations" | "technical" | "other";
export interface Incident {
  id: number; title: string; description: string; category: IncidentCategory;
  status: IncidentStatus; origin: string; created_by: string; created_at: string;
  updated_at: string; resolved_at: string | null; version: number;
}
export type IncidentInput = Pick<Incident, "title" | "description" | "category">;
export interface IncidentPage { items: Incident[]; total: number; limit: number; offset: number }
export const statusLabels: Record<IncidentStatus, string> = { open: "Abierta", in_progress: "En progreso", resolved: "Resuelta" };
export const categoryLabels: Record<IncidentCategory, string> = { operations: "Operaciones", technical: "Técnica", other: "Otra" };
