/**
 * telemetry.ts registra un setInterval y un listener de visibilitychange en
 * el momento del import (efecto de módulo) que nunca se desregistran — por
 * diseño, es un singleton pensado para vivir toda la sesión de la pestaña.
 * Por eso todo este archivo comparte UNA sola instancia del módulo (cargada
 * una vez en beforeAll, con fake timers ya activos) en vez de reimportarlo
 * por test: reimportar dejaría listeners huérfanos acumulándose sobre el
 * mismo `document` de jsdom (compartido por todos los tests del archivo) y
 * contaminaría las aserciones de tests posteriores.
 */
import type { track as trackType } from "@/lib/telemetry";

let track: typeof trackType;
const originalFetch = global.fetch;

beforeAll(() => {
  jest.useFakeTimers();
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  ({ track } = require("@/lib/telemetry"));
});

afterAll(() => {
  jest.useRealTimers();
});

beforeEach(() => {
  window.localStorage.clear();
  global.fetch = jest.fn().mockResolvedValue({ ok: true });
  Object.defineProperty(navigator, "sendBeacon", { value: jest.fn(), writable: true, configurable: true });
});

afterEach(() => {
  // Drena cualquier evento que este test haya dejado en cola, para que el
  // próximo test empiece con la cola compartida vacía.
  jest.advanceTimersByTime(10_000);
  global.fetch = originalFetch;
});

describe("track() envelope", () => {
  it("does not call fetch before the batch threshold is reached", () => {
    track("backoffice_section_viewed", { route: "/suppliers" });

    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("flushes a single batch with a well-formed envelope once 20 events queue up", () => {
    for (let i = 0; i < 20; i += 1) {
      track("backoffice_section_viewed", { route: `/route-${i}` });
    }

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [, init] = (global.fetch as jest.Mock).mock.calls[0];
    const body = JSON.parse(init.body);

    expect(body.events).toHaveLength(20);
    const [firstEvent] = body.events;
    expect(firstEvent).toMatchObject({
      event_type: "backoffice_section_viewed",
      schemaVersion: "1.0.0",
      requestId: null,
      userId: null,
      properties: { route: "/route-0" },
    });
    expect(firstEvent.eventId).toMatch(/^[0-9a-f-]{36}$/);
    expect(firstEvent.sessionId).toMatch(/^[0-9a-f-]{36}$/);
    expect(() => new Date(firstEvent.timestamp).toISOString()).not.toThrow();
  });

  it("reuses the same sessionId across events, persisted in localStorage", () => {
    track("backoffice_section_viewed", { route: "/a" });
    const storedSessionId = window.localStorage.getItem("brasaland_telemetry_session_id");

    for (let i = 0; i < 19; i += 1) track("backoffice_section_viewed", { route: `/${i}` });

    const [, init] = (global.fetch as jest.Mock).mock.calls[0];
    const { events } = JSON.parse(init.body);
    expect(events.every((event: { sessionId: string }) => event.sessionId === storedSessionId)).toBe(true);
  });
});

describe("batch timer (10s)", () => {
  it("flushes a partial queue after 10 seconds even without reaching 20 events", () => {
    track("backoffice_section_viewed", { route: "/suppliers" });
    expect(global.fetch).not.toHaveBeenCalled();

    jest.advanceTimersByTime(10_000);

    expect(global.fetch).toHaveBeenCalledTimes(1);
  });
});

describe("reliable flush via sendBeacon", () => {
  it("sends the pending queue through navigator.sendBeacon when the tab becomes hidden", () => {
    track("backoffice_section_viewed", { route: "/suppliers" });

    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));

    expect(navigator.sendBeacon).toHaveBeenCalledTimes(1);
    expect(global.fetch).not.toHaveBeenCalled();

    const [, blob] = (navigator.sendBeacon as jest.Mock).mock.calls[0];
    expect(blob).toBeInstanceOf(Blob);
  });

  it("does not call sendBeacon when the queue is empty", () => {
    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));

    expect(navigator.sendBeacon).not.toHaveBeenCalled();
  });
});

describe("retry with exponential backoff", () => {
  it("retries a failed batch up to 3 times, then drops it", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });

    for (let i = 0; i < 20; i += 1) track("backoffice_section_viewed", { route: `/${i}` });
    await jest.advanceTimersByTimeAsync(0); // deja resolver la promesa del fetch inicial

    expect(global.fetch).toHaveBeenCalledTimes(1);

    await jest.advanceTimersByTimeAsync(1_000);
    expect(global.fetch).toHaveBeenCalledTimes(2);

    await jest.advanceTimersByTimeAsync(2_000);
    expect(global.fetch).toHaveBeenCalledTimes(3);

    await jest.advanceTimersByTimeAsync(4_000);
    expect(global.fetch).toHaveBeenCalledTimes(4);

    // Se agotaron los 3 reintentos (4 llamadas en total) — un avance más no
    // debe generar una quinta llamada, el batch se descarta.
    await jest.advanceTimersByTimeAsync(10_000);
    expect(global.fetch).toHaveBeenCalledTimes(4);
  });
});
