# Plan de Telemetría — Brasaland

Respuesta al RFI del equipo de gestión: qué datos vale la pena capturar hoy — y cuáles podrían ser valiosos mañana — antes de escribir una sola línea de instrumentación sobre el sistema de gestión de inventario y el resto del backoffice.

**Regla de oro aplicada a cada evento de este catálogo:** *"Capturamos `[event_type]` porque necesitamos saber `[hipótesis]`, lo que nos permite tomar la decisión `[decisión concreta]`."* Todo evento que no completa esta frase se descarta — ver [§6 Riesgos y exclusiones](#6-riesgos-y-exclusiones).

Los `propertiesSchema` completos (allowlist validable) de cada evento viven en [`event-schemas.json`](./event-schemas.json), no duplicados aquí. Este documento cubre el catálogo, el envelope, la estrategia de entrega y los riesgos.

---

## 0. Estado real del sistema al momento de este diseño

Este plan se diseñó contra el código del monorepo, no solo contra el enunciado del brief:

- **El backend `/inventory` no existe todavía** en `services/api` (solo `/auth` y `/suppliers`). El **frontend sí existe** (`uis/backoffice/src/app/inventory/**`) y ya fija los nombres de campo reales contra una API pendiente de construir. Este catálogo usa esos nombres (`Ingredient`, `location_id`, `ExitReason`) para no forzar una reinstrumentación cuando `/inventory` se construya.
- El CONTEXT de negocio nombra las entidades como `Product`/`InboundOrder`/`OutboundOrder`; el código real las nombra `Ingredient`/`IngredientEntry`/`IngredientExit`. Los `event_type` de este catálogo siguen el CONTEXT (es la nomenclatura de negocio evaluada), pero las `properties` internas siguen el código (`product_id` como nombre de campo de negocio, mapeado 1:1 al `ingredient_id` que ya existe en el frontend).
- `product_category` usa la taxonomía de `Ingredient` (`meat | produce | sauce | beverage | packaging | cleaning`, `uis/backoffice/src/lib/inventoryLabels.ts`) — **no** la de `Supplier` (`Category` en `services/api/models.py`, 8 valores distintos en español). Son dos taxonomías distintas que ya conviven en el repo para dos entidades distintas; este catálogo usa la de producto/ingrediente.
- **`country` no puede resolverse hoy en ningún punto del código** — `location_id` existe (`1..14`), pero no hay una tabla `Location` que lo mapee a país/ciudad. Se documenta como prerequisito de instrumentación en [§6](#6-riesgos-y-exclusiones), no se resuelve en este proyecto.
- **`stock_waste_registered.reason`** (enum `expired | kitchen_error | theft_suspected`) requiere un campo nuevo en `OutboundOrderForm.tsx` — el `ExitReason` que existe hoy (`consumption | waste`) es más grueso y sirve para `outbound_order_created`, no para el sub-motivo de merma. Ver [§6](#6-riesgos-y-exclusiones).
- **La arquitectura prevista para `/inventory` (aún sin construir) usa Supabase (Postgres) vía SQLModel** para `Ingredient`/`IngredientEntry`/`IngredientExit` — TinyDB se queda solo para usuarios (`CONTEXT.md` raíz, `database.py # Cliente TinyDB + motor SQLModel`, regla de negocio 4: "Sin tabla de usuarios en Supabase"). No hay ninguna configuración de Supabase en el repo hoy — es la arquitectura objetivo del hito bloqueado, no algo ya construido. Esto importa para el mecanismo de captura de eventos, ver [§4.4](#44-por-qué-emisión-desde-la-api-y-no-triggers-de-supabase).

---

## 1. Entidades (fuente: CONTEXT de negocio)

| Entidad | Significado |
|---|---|
| `Product` (código: `Ingredient`) | Ingrediente o insumo (carne, vegetal, salsa, empaque…). Unidad de medida + categoría. |
| `InboundOrder` (código: `IngredientEntry`) | Mercancía recibida de un proveedor en un local. |
| `OutboundOrder` (código: `IngredientExit`) | Consumo de ingredientes en preparación, o merma. |
| `location` | Uno de los 14 locales, país (`CO`/`US`) + ciudad. |
| `supplier` | Uno de ~20 proveedores, distintos por país. |

---

## 2. Catálogo de eventos

18 eventos: 6 obligatorios (piso del CONTEXT, no negociables) + 12 identificados (oportunidades exploradas más allá del mínimo), cubriendo 5 categorías.

### 2.1 Obligatorios — negocio/inventario (6)

| `event_type` | Hipótesis | Decisión que habilita |
|---|---|---|
| `inbound_order_created` | Necesitamos saber cuánto y qué se compra, por local y proveedor | Consolidar compras entre locales para negociar mejores precios (Lucía) |
| `outbound_order_created` | Necesitamos saber qué ingredientes se consumen más y a qué ritmo, por local | Ajustar la sugerencia automática de pedidos a proveedores (Felipe) |
| `stock_waste_registered` | Necesitamos saber cuánto producto se pierde, por qué razón, y en qué local | Priorizar auditorías de merma en los locales con peor indicador (Felipe) |
| `stock_threshold_triggered` | Necesitamos saber con qué frecuencia un local se queda corto de un ingrediente clave | Ajustar el umbral mínimo o la frecuencia de reabastecimiento (Felipe) |
| `direct_stock_edit_rejected` | Necesitamos saber si el personal intenta saltarse el control de trazabilidad | Reforzar capacitación o permisos en los locales donde ocurre más (Jake) |
| `ingredient_price_variance_detected` | Necesitamos saber cuándo un ingrediente clave sube de precio de forma anómala | Alertar a Lucía y Mariana para renegociar o buscar proveedor alterno |

### 2.2 Identificados — negocio/inventario adicional (2)

| `event_type` | Hipótesis | Decisión que habilita |
|---|---|---|
| `inventory_order_validation_failed` | Necesitamos saber si el formulario de salida deja llegar intentos de registrar más cantidad de la que hay en stock | Decidir si ese límite debe aplicarse también server-side antes de construir `/inventory` |
| `inventory_product_created` | Necesitamos saber con qué frecuencia se da de alta un ingrediente nuevo en el catálogo | Detectar si el catálogo crece distinto por país (señal para estandarización de recetas) |

### 2.3 Identificados — autenticación (4)

| `event_type` | Hipótesis | Decisión que habilita |
|---|---|---|
| `login_attempt_failed` | Necesitamos saber cuántos intentos fallidos hay y con qué frecuencia | Detectar patrones de fuerza bruta contra `POST /auth/login` |
| `login_succeeded` | Necesitamos saber cuántas sesiones activas hay | Dimensionar capacitación de uso del sistema por local |
| `session_expired` | Necesitamos saber si los usuarios pierden trabajo por expiración del JWT a mitad de una orden | Decidir si el TTL del token es demasiado corto para un turno de cocina |
| `password_reset_requested` | Necesitamos saber la frecuencia de reseteos de contraseña | Decidir si el onboarding de nuevos empleados necesita mejor comunicación de credenciales |

### 2.4 Identificados — rendimiento (2)

| `event_type` | Hipótesis | Decisión que habilita |
|---|---|---|
| `api_latency_recorded` | Necesitamos saber qué endpoints son lentos bajo uso real | Priorizar optimización de backend |
| `page_load_recorded` | Necesitamos saber si las vistas de inventario cargan lento para operadores con mala conexión | Priorizar optimización de frontend por país |

### 2.5 Identificados — errores (2)

| `event_type` | Hipótesis | Decisión que habilita |
|---|---|---|
| `frontend_error_captured` | Necesitamos saber qué errores de JS no capturados ocurren en producción | Priorizar fixes por frecuencia real, no por reportes manuales |
| `api_request_failed` | Necesitamos saber cuándo la API devuelve 5xx | Detectar una caída de `services/api` antes de que operaciones lo reporte por Slack |

### 2.6 Identificados — navegación (2)

| `event_type` | Hipótesis | Decisión que habilita |
|---|---|---|
| `backoffice_section_viewed` | Necesitamos saber qué secciones visitan más los operadores | Priorizar qué parte del backoffice pulir primero |
| `inventory_flow_abandoned` | Necesitamos saber si un operador abre un formulario de orden y no llega a enviarlo | Detectar si hay fricción (ej. bloqueos de validación) que empuja a abandonar |

---

## 3. Event Envelope

Todo evento, sin excepción, sigue este envelope (definido formalmente en `event-schemas.json` → `envelope`):

| Campo | Tipo | Descripción |
|---|---|---|
| `eventId` | `string` (UUIDv4) | Identificador único, generado en el punto de emisión |
| `timestamp` | `string` (ISO 8601, UTC) | Momento de ocurrencia, no de envío/flush |
| `sessionId` | `string` (UUIDv4) | Sesión de navegador — independiente del JWT (ver 4.1) |
| `userId` | `string \| null` | `sub` del JWT; `null` en eventos no autenticados (`login_attempt_failed`) |
| `event_type` | `string` (`entidad_acción`) | Ej. `inbound_order_created` |
| `schemaVersion` | `string` (semver) | `"1.0.0"` para este catálogo |
| `requestId` | `string \| null` | Correlación frontend↔backend↔logs; `null` en eventos client-side puros |
| `properties` | `object` | Payload específico, validado contra el `propertiesSchema` del evento en `event-schemas.json` |

Cada `event_type` tiene su allowlist como JSON Schema draft-07 (`additionalProperties: false`) en `event-schemas.json` — ninguna clave fuera de la lista debe emitirse.

---

## 4. Ejemplos de instrumentación

Fragmentos de referencia para el desarrollador que instrumente esto — **no implementados en este proyecto** (el entregable de hoy es solo diseño).

### 4.1 Frontend — envelope y emisión (`uis/backoffice`)

```ts
// uis/backoffice/src/lib/telemetry.ts (ejemplo)
import { getCurrentUserId } from "@/lib/session";

export interface TelemetryEnvelope<T extends Record<string, unknown>> {
  eventId: string;
  timestamp: string;
  sessionId: string;
  userId: string | null;
  event_type: string;
  schemaVersion: string;
  requestId: string | null;
  properties: T;
}

const SESSION_KEY = "brasaland_telemetry_session_id";

// UUID nuevo por sesión de navegador, separado del JWT a propósito:
// el token puede rotar (login/reset) sin perder la agrupación de eventos
// de la misma sesión de trabajo, y evita mandar el JWT crudo a un store
// de analítica que puede tener menor nivel de seguridad que el de auth.
const getSessionId = (): string => {
  let id = window.localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(SESSION_KEY, id);
  }
  return id;
};

export const buildEvent = <T extends Record<string, unknown>>(
  eventType: string,
  properties: T,
  requestId: string | null = null,
): TelemetryEnvelope<T> => ({
  eventId: crypto.randomUUID(),
  timestamp: new Date().toISOString(),
  sessionId: getSessionId(),
  userId: getCurrentUserId(),
  event_type: eventType,
  schemaVersion: "1.0.0",
  requestId,
  properties,
});
```

Uso dentro de `OutboundOrderForm.tsx` (`handleSubmit`, líneas 39-74 actuales):

```tsx
// Tras el bloque de validación cliente (línea 58, quantityExceedsStock):
if (quantityExceedsStock) {
  emitTelemetryEvent(
    buildEvent("inventory_order_validation_failed", {
      location_id: Number(form.location_id),
      product_id: ingredientId,
      order_type: "outbound",
      reason: "quantity_exceeds_stock",
    }),
  );
  setClientError("La cantidad supera el stock disponible — corrígela antes de enviar");
  return;
}

// Tras un createOutboundOrder exitoso (línea 67-68):
emitTelemetryEvent(
  buildEvent("outbound_order_created", {
    location_id: Number(form.location_id),
    country: null, // se resuelve server-side — ver §6, nunca hardcodear en el cliente
    product_id: ingredientId,
    product_category: selectedIngredient?.category ?? null,
    quantity,
    unit: selectedIngredient?.unit ?? null,
    reason: form.reason,
  }),
);
```

### 4.2 Backend — validación con allowlist (Pydantic, estilo `services/api/models.py`)

```python
# services/api/telemetry_models.py (ejemplo)
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class OutboundOrderCreatedProperties(BaseModel):
    # extra="forbid" es el allowlist: cualquier clave fuera de estas
    # seis hace que Pydantic rechace el evento en vez de guardarlo.
    model_config = ConfigDict(extra="forbid")

    location_id: int
    country: Literal["CO", "US"]
    product_id: int
    product_category: str
    quantity: float = Field(gt=0)
    unit: str
    reason: Literal["consumption", "waste"]
```

### 4.3 Backend — agregación de latencia (extiende el `timing_middleware` real de `services/api/main.py`)

```python
# services/api/main.py — extensión ilustrativa del middleware ya existente
from collections import defaultdict

_latency_buffer: dict[tuple[str, str], list[float]] = defaultdict(list)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000

    logger.info(f"{request.method} {request.url.path} → {response.status_code} | {duration:.1f}ms")

    # No se emite un evento por request (ver §5.2, throttle). Se acumula
    # y un job de background hace flush cada 60s como un único
    # api_latency_recorded por ruta.
    key = (request.method, request.url.path)
    _latency_buffer[key].append(duration)
    return response
```

### 4.4 Por qué emisión desde la API y no triggers de Supabase

La arquitectura objetivo de `/inventory` (§0) pone `Ingredient`/`IngredientEntry`/`IngredientExit` en Supabase (Postgres), que ofrece captura nativa de cambios de datos (Database Webhooks / Realtime sobre `postgres_changes`). Se descarta como mecanismo de captura de este catálogo, por dos razones concretas:

1. **Mecanismo inconsistente entre entidades del mismo backend.** `/suppliers` y `/auth` se quedan en TinyDB — sin equivalente a webhooks de Postgres. Apoyarse en triggers de Supabase solo para inventario dejaría dos estrategias de captura distintas conviviendo en `services/api`, en vez de un único patrón de emisión aplicable a cualquier tabla presente o futura.
2. **No cubre todo el catálogo por diseño.** `direct_stock_edit_rejected` es, por definición, un intento que nunca llega a escribirse — un trigger de `INSERT` no puede dispararse sobre una fila que el sistema rechazó antes de tocar la tabla. `stock_threshold_triggered` es una condición calculada después de un `IngredientExit` legítimo, no una tabla propia con su propio evento de DB. Un mecanismo basado en triggers de Postgres cubriría como máximo `inbound_order_created` / `outbound_order_created` / `inventory_product_created`, y aun esos necesitarían un paso de enriquecimiento posterior (`sessionId`, `requestId`, `userId` de la request no existen a nivel de fila de base de datos).

**Decisión:** todo evento se emite desde el código de aplicación (handler de FastAPI tras el commit, o el punto de rechazo en la validación), igual sobre TinyDB que sobre la futura tabla en Supabase — el mecanismo de captura no depende del motor de persistencia subyacente.

---

## 5. Estrategia de entrega

### 5.1 Stream vs. batch — justificado por urgencia de la decisión, no por preferencia técnica

| `event_type` | Entrega | Justificación |
|---|---|---|
| `inbound_order_created` | Batch | Consolidar compras (Lucía) es análisis semanal/mensual, no requiere verlo en segundos |
| `outbound_order_created` | Batch | La sugerencia automática de reabastecimiento se recalcula en lotes periódicos |
| `stock_waste_registered` | Batch | Priorizar auditorías es una decisión de gestión semanal |
| `stock_threshold_triggered` | Batch | Ajustar el umbral mínimo es una revisión periódica de configuración |
| `direct_stock_edit_rejected` | **Stream** | Rechazos repetidos en una ventana corta son señal de un bypass activo en curso — verlo al día siguiente pierde la ventana de intervención |
| `ingredient_price_variance_detected` | **Stream** | Alertar antes de que se emitan más órdenes al precio anómalo — cada hora de retraso es costo real |
| `inventory_order_validation_failed` | Batch | Señal de fricción de UX, se analiza agregada |
| `inventory_product_created` | Batch | Alta de catálogo, sin urgencia operativa |
| `login_attempt_failed` | **Stream** | Detectar fuerza bruta requiere ver los intentos según ocurren |
| `login_succeeded` | Batch | Conteo de sesiones activas, análisis agregado |
| `session_expired` | Batch | Ajuste de TTL es una revisión de configuración periódica |
| `password_reset_requested` | Batch | Sin urgencia operativa conocida hoy |
| `api_latency_recorded` | Batch (agregado) | Ya es un agregado de 60s por diseño (§5.2) — sin un umbral de alerta definido hoy, un pico aislado no justifica verlo en vivo |
| `page_load_recorded` | Batch | Análisis de rendimiento por país, sin acción inmediata definida |
| `frontend_error_captured` | Batch | No hay on-call ni alerting configurado hoy — sirve como insumo agregado, no señal de página |
| `api_request_failed` | **Stream** | Un 5xx sostenido indica posible caída de `services/api` — vale más detectarlo en minutos que al día siguiente |
| `backoffice_section_viewed` | Batch | Analítica de navegación, sin urgencia |
| `inventory_flow_abandoned` | Batch | Señal de fricción de producto, se revisa agregada |

### 5.2 Throttle / debounce

- **`api_latency_recorded`**: no se emite un evento por request (con tráfico real serían miles/día solo de `GET /suppliers`). Se agrega en memoria por `(method, route)` y se hace *flush* como un único evento resumen cada 60 segundos (ver código en §4.3). Ventana elegida por ser lo bastante corta para no perder visibilidad de una degradación sin generar volumen desproporcionado.
- **`inventory_flow_abandoned`**: requiere debounce de intención, no de frecuencia — se dispara solo si el formulario estuvo abierto más de 10 segundos sin submit y el usuario navega fuera (`beforeunload` o cambio de ruta), no en cada tecla o cambio de campo.
- El resto de eventos del catálogo son 1:1 con una acción de usuario discreta (una orden, un login, un rechazo) — no necesitan throttle porque su frecuencia natural ya es baja.

---

## 6. Riesgos y exclusiones

**Excluido:**
- Capturar el JWT completo en cualquier evento — `sessionId` es un UUID separado, generado client-side, nunca el token.
- Nombres de empleados o datos de clientes en `properties` — restricción explícita del CONTEXT; ningún `propertiesSchema` los incluye. `userId` es el único identificador de persona (id numérico interno, no PII directamente identificable fuera del sistema).
- Conversión de moneda en la capa de telemetría — los montos se reportan en la moneda del local; la comparación cross-currency es trabajo del futuro pipeline de reporting ejecutivo.
- Captura de IP o user-agent detallado — no hay hoy una decisión de negocio que lo requiera (regla de oro incumplida); se reconsidera si aparece una necesidad real de detección de fraude/abuso.
- `product_deleted` / `location_deleted` — ni el backend planeado ni el frontend actual exponen borrado de productos o locales; no se instrumenta una acción que no existe.

**Datos sensibles y anonimización:**
- `login_attempt_failed` y `password_reset_requested` incluyen `email_hash` (`sha256` del email en minúsculas, calculado client-side) en vez del email en texto plano — documentado en `event-schemas.json` (`pii: true`, campo `piiNote`).

**Riesgos aceptados, sin resolver en este proyecto (documentación, no bloqueo):**
- `country` no puede resolverse hoy en ningún punto del código — depende de un futuro modelo `Location` (id → país/ciudad) que no existe. El catálogo asume que existirá; hasta entonces, `country` no puede instrumentarse correctamente en los eventos de inventario.
- `stock_waste_registered.reason` (`expired | kitchen_error | theft_suspected`) requiere un campo nuevo en `OutboundOrderForm.tsx` (`waste_reason`, condicional a `reason === "waste"`) que no existe en el formulario actual — queda como prerequisito de instrumentación, no como parte de este entregable.

**Extensión aditiva — Hito 6 Parte 1 (Pipeline de Desempeño de Negocio):**
- `unit_cost` se agregó como campo `required` a `inbound_order_created` y `stock_waste_registered` en `event-schemas.json` — el reporte semanal de costo/merma por local (`reporting.weekly_location_performance`, ver `data/pipelines/PIPELINE_DESIGN.md`) necesita un valor monetario por unidad que el catálogo original de Project 6 no capturaba. Es una extensión de un evento obligatorio existente, no un `event_type` nuevo — el envelope y el resto de `properties` no cambian. En `inbound_order_created` viaja junto a `currency`; en `stock_waste_registered` la moneda se deriva de `country` (misma convención `COUNTRY_CURRENCY` de `services/api/models.py`) en vez de duplicar el campo.

---

## 7. Referencias

- Entidades y métricas obligatorias: CONTEXT de negocio (Brasaland).
- Allowlists completas por evento: [`event-schemas.json`](./event-schemas.json).
- Código real referenciado: `services/api/main.py` (`timing_middleware`), `services/api/routes/auth.py`, `services/api/models.py`, `uis/backoffice/src/types/inventory.ts`, `uis/backoffice/src/lib/inventoryLabels.ts`, `uis/backoffice/src/lib/session.ts`, `uis/backoffice/src/components/inventory/OutboundOrderForm.tsx`.
- Arquitectura objetivo de `/inventory` (pendiente de construir): `CONTEXT.md` raíz (brief de Hito 5 — SQLModel + Supabase para las tablas de inventario, TinyDB solo para usuarios).
