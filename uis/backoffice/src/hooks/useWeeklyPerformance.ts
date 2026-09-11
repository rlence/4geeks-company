"use client";

import { useEffect, useState } from "react";
import { getApiErrorMessage, getWeeklyLocationPerformance } from "@/lib/reportingApi";
import type { WeeklyLocationPerformanceReport } from "@/types/reporting";

type FetchStatus = "loading" | "success" | "error";

export const useWeeklyPerformance = () => {
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [report, setReport] = useState<WeeklyLocationPerformanceReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    getWeeklyLocationPerformance(undefined, controller.signal)
      .then((data) => {
        setReport(data);
        setStatus("success");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(getApiErrorMessage(err));
        setStatus("error");
      });

    return () => controller.abort();
  }, []);

  return { status, report, error };
};
