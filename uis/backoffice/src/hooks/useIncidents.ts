"use client";
import { useEffect, useState } from "react";
import { getIncidents } from "@/lib/incidentsApi";
import type { IncidentPage } from "@/types/incident";

export function useIncidents(statusFilter: string, category: string, offset: number) {
  const [state, setState] = useState<{ status: "loading" | "success" | "error"; data: IncidentPage | null; error: string }>({ status: "loading", data: null, error: "" });
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ limit: "20", offset: String(offset) });
    if (statusFilter) params.set("status", statusFilter);
    if (category) params.set("category", category);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reinicio al cambiar los filtros de red
    setState({ status: "loading", data: null, error: "" });
    getIncidents(params, controller.signal).then(data => setState({ status: "success", data, error: "" })).catch(error => {
      if (!controller.signal.aborted) setState({ status: "error", data: null, error: error instanceof Error ? error.message : "Error al cargar" });
    });
    return () => controller.abort();
  }, [statusFilter, category, offset]);
  return state;
}
