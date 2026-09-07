"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { track } from "@/lib/telemetry";

const MAX_ERROR_MESSAGE_LENGTH = 500;

export const TelemetryBoot = () => {
  const pathname = usePathname();

  useEffect(() => {
    const onError = (event: ErrorEvent) => {
      track("frontend_error_captured", {
        route: window.location.pathname,
        message: event.message.slice(0, MAX_ERROR_MESSAGE_LENGTH),
      });
    };
    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      const message = event.reason instanceof Error ? event.reason.message : String(event.reason);
      track("frontend_error_captured", {
        route: window.location.pathname,
        message: message.slice(0, MAX_ERROR_MESSAGE_LENGTH),
      });
    };

    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onUnhandledRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
    };
  }, []);

  useEffect(() => {
    track("backoffice_section_viewed", { route: pathname });
  }, [pathname]);

  // Solo una vez: performance.getEntriesByType("navigation") describe la
  // carga completa del documento (hard navigation), no cada cambio de ruta
  // del router de Next — repetirlo por pathname reportaría el mismo valor
  // en cada navegación cliente-a-cliente.
  useEffect(() => {
    const [entry] = performance.getEntriesByType("navigation") as PerformanceNavigationTiming[];
    if (entry) {
      track("page_load_recorded", { route: window.location.pathname, load_time_ms: Math.round(entry.duration) });
    }
  }, []);

  return null;
};
