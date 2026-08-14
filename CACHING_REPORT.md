# Informe de Caching — Brasaland

Rama: `feature/project-5-caching`. Alcance: `services/api` (backend), `uis/backoffice` y `uis/website` (frontend). `uis/talent-pipeline-tracker` queda fuera (protegido en `AGENTS.md`), y el backend `/inventory` que usan las vistas de inventario de `backoffice` no existe en este repo, así que tampoco entra.

## 1. Decisiones en el frontend

### Lazy Loading

**`SupplierForm`** (`uis/backoffice/src/components/suppliers/SupplierForm.tsx`, 191 líneas) — cargado con `next/dynamic` desde `uis/backoffice/src/app/suppliers/page.tsx`.

- **Por qué**: el formulario de alta solo se monta cuando el usuario hace clic en "+ Nuevo proveedor" (`open === true`). La mayoría de las visitas a `/suppliers` son para mirar/filtrar el directorio, no para dar de alta un proveedor — no tiene sentido pagar el costo de parsear/ejecutar la lógica de validación y estado del formulario en cada carga de la página.
- **Verificación real, no solo teórica**: inspeccioné el build de producción (`npm run build`) y confirmé que el string `"Registrar proveedor"` (que solo existe dentro de `SupplierForm.tsx`) aparece únicamente en un chunk separado (`538.6325f91a5b8022c8.js`), no en el bundle principal de la ruta `/suppliers`. El code-splitting funciona de verdad, no es solo sintaxis correcta.
- **Trade-off**: `ssr: false` — el botón "+ Nuevo proveedor" se ve de inmediato (fallback deshabilitado), el formulario real tarda un tick extra en estar interactivo la primera vez que se abre. Aceptable: es una acción explícita del usuario, no contenido que deba estar listo al pintar la página.

**`BrasaPointsForm`** (`uis/website/src/components/BrasaPointsForm.tsx`, 414 líneas — el componente más grande de todo el monorepo) — cargado con `next/dynamic` vía un wrapper cliente (`BrasaPointsFormLazy.tsx`) desde `uis/website/src/app/brasa-points/page.tsx`.

- **Por qué, con honestidad sobre el límite del caso**: a diferencia de `SupplierForm`, esta ruta ya está separada del bundle de `/` por el App Router de Next (la home nunca importa `BrasaPointsForm`, solo el teaser con un link). El ahorro acá **no es sacar el componente de otro bundle** — es diferir su hidratación dentro de su propia ruta, para que el encabezado y el párrafo introductorio de `/brasa-points` queden interactivos antes de pagar el costo de parsear la lógica de validación en tiempo real y los selects encadenados (país → ciudad → local) del formulario. Es un beneficio real pero menor que el de `SupplierForm`; lo documento así en vez de inflar la justificación.
- **Gotcha técnico real**: `page.tsx` es un Server Component (exporta `metadata`). `next/dynamic(..., { ssr: false })` no está permitido directo ahí — Next 16 App Router lo rechaza. Solución: un wrapper `"use client"` (`BrasaPointsFormLazy.tsx`) que hace el `dynamic()` y se importa desde el Server Component. Verificado en build: el string `"acceptTerms"` (interno del formulario) queda en chunks separados (`1id7_5mubympi.js`, `3a2gemycxvyhh.js`), no en el chunk de la página.

### `useMemo`

No había ningún cálculo derivado no trivial en el código existente antes de este cambio — los lookups estáticos de `uis/website/src/lib/formOptions.ts` (`COUNTRY_CITIES`, `CITY_LOCATIONS`) son indexado O(1) en objetos chicos y memoizarlos habría sido la "memoización prematura" que el propio rule pide evitar. En vez de forzar un `useMemo` sobre algo trivial, agregué una funcionalidad chica y real en `/suppliers` que sí lo justifica, apoyada en el volumen sembrado para la sección 2 (3015 proveedores):

**`SupplierSummary`** (`uis/backoffice/src/components/suppliers/SupplierSummary.tsx`, nuevo) — barra de resumen (total, conteo por país, tarifa promedio por moneda) calculada con `useMemo(() => {...}, [suppliers])`.

**Búsqueda local por nombre** en `SuppliersPageContent` (`uis/backoffice/src/app/suppliers/page.tsx`) — `visibleSuppliers` calculado con `useMemo(() => suppliers.filter(...), [suppliers, searchTerm])`.

- **Por qué la combinación de ambos demuestra el punto**: `searchTerm` vive como estado en el padre (`SuppliersPageContent`). Cada letra tipeada re-renderiza el padre y, con él, a `SupplierSummary` (es su hijo). Sin el `useMemo` en `SupplierSummary`, cada tecla recorrería las ~3000 filas para recalcular el resumen aunque `suppliers` no haya cambiado. Con el `useMemo` dependiendo solo de `[suppliers]`, React reutiliza el valor cacheado y **no** vuelve a ejecutar el `for` — el componente se re-renderiza (es barato) pero el cálculo costoso no.
- **El array de dependencias es la parte que importa**: `visibleSuppliers` depende de `[suppliers, searchTerm]` porque su cálculo SÍ debe repetirse en cada tecla (es literalmente el filtro). `stats` en `SupplierSummary` depende solo de `[suppliers]` porque no tiene relación con el texto de búsqueda. Son dos casos con la misma forma de código y dependencias distintas a propósito — el contraste es el argumento pedagógico.
- **Verificación**: no cuento con browser/Playwright en este entorno para grabar el Profiler de React DevTools. Recomiendo antes de dar el hito por cerrado: abrir `/suppliers`, React DevTools → Profiler → grabar mientras se escribe en el buscador → confirmar que `SupplierSummary` no dispara su callback de `useMemo` en cada tecla (se puede instrumentar temporalmente con un `console.count` dentro del callback, quitándolo antes de commitear).

## 2. Decisiones en el backend

Namespace de caché único (`_suppliers_cache`, `services/api/routes/suppliers.py`) para ambos endpoints, con `TTLCache` propia (`services/api/cache.py`, diccionario en memoria, sin dependencias nuevas — no hay Redis en el stack).

### `GET /suppliers` (list, filtros `country`/`category`) — caso fuerte

- **Coste**: TinyDB persiste todo en un JSON plano y hace scan lineal en `.all()`/`.search()`. Con los 15 proveedores originales, sub-5ms — no había nada que medir. Sembré volumen realista con `services/api/seed_bulk_suppliers.py` (3000 proveedores nuevos, países/categorías/tarifas variadas, no filas idénticas) para poder medir de verdad.
- **Medido con el middleware de timing** (`services/api/main.py`), sobre 3015 filas:

  | Petición | Cold (cache miss) | Cache hit |
  |---|---|---|
  | `GET /suppliers` | 29.8ms | 5.7ms / 5.3ms |
  | `GET /suppliers?country=Colombia` | 10.6ms | 3.1ms |

  ~5-6x más rápido en cache hit.
- **Frecuencia**: es la vista por defecto de `/suppliers`, se repite en cada carga/cambio de filtro del equipo de Compras.
- **TTL: 30 segundos.** Ver sección 3.
- **Invalidación**: `clear()` completo del namespace en `create_supplier`, `update_rate`, `update_status` y `delete_supplier`. Verificado con el middleware: tras un `PATCH /suppliers/5/rate`, el siguiente `GET /suppliers` volvió a costar 14.9ms (cache miss real, no un valor stale) y el que le siguió volvió a 5.0ms.

### `GET /suppliers/{id}` — caso más débil, documentado como tal

- **Coste real**: bajo. `suppliers_table.get(doc_id=...)` es esencialmente un lookup por clave en TinyDB, no un scan — medido en 4.6ms cold vs 0.4ms cacheado (~11x, pero sobre una base ya chica). No es un caso "cost-driven" como el de la lista.
- **Justificación honesta**: la razón real es **frecuencia**, no cálculo — si varias personas del equipo abren el mismo proveedor en una ráfaga corta (p. ej. un link compartido en Slack), cachear evita 10 lecturas idénticas a TinyDB por el precio de una. El costo de implementarlo es marginal (mismo namespace, misma invalidación) así que el trade-off vale la pena aunque el caso de "coste" del framework coste×frecuencia×estabilidad sea débil.
- **TTL y invalidación**: mismos que la lista (mismo namespace `_suppliers_cache`, mismo `clear()` en cualquier escritura).

## 3. Intercambios reconocidos (frescura vs. rendimiento)

**TTL de 30 segundos para todo `/suppliers`** (`SUPPLIERS_CACHE_TTL_SECONDS` en `services/api/routes/suppliers.py`): es un directorio interno de Compras y Proveedores, no un feed en vivo ni un sistema de pricing en tiempo real. Una tarifa o un estado (`active`/`suspended`) desactualizado hasta por 30 segundos es aceptable para este caso de uso — nadie toma una decisión de compra en la ventana de esos 30 segundos sin refrescar la página. Además, como cualquier escritura limpia la caché por completo (`_suppliers_cache.clear()`), la ventana real de staleness casi nunca llega a los 30 segundos completos: solo se acerca a ese máximo si nadie escribe nada en ese lapso, momento en el que la "desactualización" es, por definición, inexistente (no cambió nada).

**Decisión deliberada de invalidación total, no granular**: con `country` × `category` hay ~16 combinaciones posibles de cache-key para `list`, más una por cada `supplier_id` para `detail`. Invalidar solo la combinación afectada por una escritura sería más "óptimo" en teoría, pero mucho más frágil en la práctica — fácil de olvidar un caso si se agrega un filtro nuevo más adelante. Se prefirió correctitud simple (`clear()` completo) sobre invalidación fina.

## 4. Qué no se cacheó y por qué

- **`POST /auth/login`** (`services/api/routes/auth.py`): el costo de `bcrypt.checkpw` es una decisión de seguridad intencional, no un desperdicio de cómputo. Cachear el resultado de una verificación de contraseña (o el token emitido) no tiene sentido — el hash debe recalcularse en cada intento para no debilitar la resistencia a fuerza bruta, y una clave de caché mal acotada ahí sería directamente una fuga de sesiones entre usuarios.
- **`COUNTRY_CITIES` / `CITY_LOCATIONS`** en `uis/website/src/lib/formOptions.ts`: son objetos estáticos chicos con indexado O(1). Envolverlos en `useMemo` habría sido memoización prematura — el propio rule advierte contra esto explícitamente, y el "beneficio" hubiera sido cero mientras que el código gana una capa de indirección innecesaria.
- **`RateEditor` / `StatusToggle`** (`uis/backoffice/src/components/suppliers/`): son componentes chicos (~50-60 líneas) que se renderizan siempre, en cada fila visible de la tabla — no están detrás de ninguna condición ni fuera del viewport inicial. No hay nada que diferir: lazy-loadearlos solo agregaría un round-trip de red por cada fila sin ahorrar bundle real.

## 5. Cómo reproducir la medición

```bash
cd services/api
uv run python seed_bulk_suppliers.py   # 3000 proveedores de prueba, no se commitea (db.json en .gitignore)
uv run uvicorn main:app --port 8000    # logs de timing en stdout, un GET/PATCH/etc. por línea
```

Repetir el mismo `GET /suppliers` dos veces seguidas en `http://localhost:8000/docs` y comparar el `Xms` de la línea de log — la segunda debería ser sensiblemente más rápida. Un `PATCH /suppliers/{id}/rate` seguido de otro `GET /suppliers` debe volver a mostrar un tiempo "cold" (confirma que la invalidación funciona, no que la caché nunca vence).
