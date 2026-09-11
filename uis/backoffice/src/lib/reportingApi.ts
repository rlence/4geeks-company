import type { WeeklyLocationPerformanceReport } from "@/types/reporting";
import { reportApiLatency, track } from "@/lib/telemetry";

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

const request = async <T>(path: string, signal?: AbortSignal): Promise<T> => {
  const start = performance.now();
  const response = await fetch(`${API_URL}${path}`, { signal });
  reportApiLatency("GET", path, performance.now() - start, !response.ok);

  if (!response.ok) {
    if (response.status >= 500) {
      track("api_request_failed", { route: path, method: "GET", status_code: response.status });
    }
    throw new ApiError(`Error ${response.status} al comunicarse con la API`, response.status);
  }
  return (await response.json()) as T;
};

export const getApiErrorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : "Ha ocurrido un error inesperado";

export const getWeeklyLocationPerformance = (
  weekStart?: string,
  signal?: AbortSignal,
): Promise<WeeklyLocationPerformanceReport> => {
  const query = weekStart ? `?week_start=${encodeURIComponent(weekStart)}` : "";
  return request<WeeklyLocationPerformanceReport>(`/reporting/weekly-location-performance${query}`, signal);
};
