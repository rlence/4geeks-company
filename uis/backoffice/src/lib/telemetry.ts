import { getCurrentUserId } from "@/lib/session";

const ENDPOINT = process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT as string;

const SCHEMA_VERSION = "1.0.0";
const BATCH_SIZE = 20;
const FLUSH_INTERVAL_MS = 10_000;
const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 1_000;

const SESSION_ID_KEY = "brasaland_telemetry_session_id";

interface TelemetryEnvelope {
  eventId: string;
  timestamp: string;
  sessionId: string;
  userId: string | null;
  event_type: string;
  schemaVersion: string;
  requestId: string | null;
  properties: Record<string, unknown>;
}

// UUID de sesión de navegador, separado del JWT a propósito: sobrevive
// una rotación de token (login/reset) sin perder la agrupación de eventos
// de la misma sesión de trabajo. Ver docs/telemetry/telemetry-plan.md §4.1.
const getSessionId = (): string => {
  let id = window.localStorage.getItem(SESSION_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(SESSION_ID_KEY, id);
  }
  return id;
};

let queue: TelemetryEnvelope[] = [];

const send = (batch: TelemetryEnvelope[], attempt = 0): void => {
  if (batch.length === 0) return;

  fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ events: batch }),
  })
    .then((response) => {
      if (!response.ok) throw new Error(`telemetry endpoint respondió ${response.status}`);
    })
    .catch(() => {
      if (attempt >= MAX_RETRIES) return;
      const delay = RETRY_BASE_DELAY_MS * 2 ** attempt;
      setTimeout(() => send(batch, attempt + 1), delay);
    });
};

const flush = (): void => {
  if (queue.length === 0) return;
  const batch = queue;
  queue = [];
  send(batch);
};

if (typeof window !== "undefined") {
  setInterval(flush, FLUSH_INTERVAL_MS);

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "hidden" || queue.length === 0) return;
    const batch = queue;
    queue = [];
    const blob = new Blob([JSON.stringify({ events: batch })], { type: "application/json" });
    navigator.sendBeacon(ENDPOINT, blob);
  });
}

// Agregación de latencia de API: no se emite un evento por request (con
// tráfico real serían miles/día) — se acumula por (method, route) y se
// hace flush como un único api_latency_recorded resumen cada 60s, mismo
// diseño que docs/telemetry/telemetry-plan.md §4.3/§5.2 (movido al
// frontend porque toda la captura de este proyecto vive ahí).
const LATENCY_FLUSH_INTERVAL_MS = 60_000;
const latencyBuffer = new Map<string, { durations: number[]; errors: number }>();

const percentile = (sorted: number[], p: number): number => {
  if (sorted.length === 0) return 0;
  const index = Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length));
  return sorted[index];
};

const flushLatencyBuffer = (): void => {
  latencyBuffer.forEach(({ durations, errors }, key) => {
    const [method, route] = key.split(" ", 2);
    const sorted = [...durations].sort((a, b) => a - b);
    track("api_latency_recorded", {
      route,
      method,
      count: sorted.length,
      p50_ms: Math.round(percentile(sorted, 50)),
      p95_ms: Math.round(percentile(sorted, 95)),
      error_count: errors,
    });
  });
  latencyBuffer.clear();
};

if (typeof window !== "undefined") {
  setInterval(flushLatencyBuffer, LATENCY_FLUSH_INTERVAL_MS);
}

export const reportApiLatency = (method: string, route: string, durationMs: number, isError: boolean): void => {
  if (typeof window === "undefined") return;
  const key = `${method} ${route}`;
  const bucket = latencyBuffer.get(key) ?? { durations: [], errors: 0 };
  bucket.durations.push(durationMs);
  if (isError) bucket.errors += 1;
  latencyBuffer.set(key, bucket);
};

export const track = (eventType: string, properties: Record<string, unknown>): void => {
  if (typeof window === "undefined") return;

  queue.push({
    eventId: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    userId: getCurrentUserId(),
    event_type: eventType,
    schemaVersion: SCHEMA_VERSION,
    requestId: null,
    properties,
  });

  if (queue.length >= BATCH_SIZE) flush();
};
