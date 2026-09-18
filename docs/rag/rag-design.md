# Diseño del sistema RAG — Base de Conocimiento de Brasaland

Asistente que responde preguntas de gerentes de local en lenguaje natural sobre
los manuales operativos de Brasaland. Este documento describe el stack completo
sin necesidad de leer el código.

| Pieza | Ubicación |
| --- | --- |
| Corpus fuente | `docs/company-knowledge-base/` |
| Chunking + indexación | `data/process/rag_index.py` |
| Recuperación + generación | `data/pipelines/rag.py` |
| Endpoint HTTP | `services/api/routes/knowledge.py` |
| UI de consulta | `uis/backoffice/src/app/knowledge/` |
| Tests unitarios | `tests/pipelines/test_rag.py` |
| Eval de retrieval | `data/eval/test-queries.json`, `data/eval/recall_at_3.py` |

> El módulo de indexación se llama `rag_index.py` y no `rag.py` —la tabla del
> rule admite otros nombres— porque dos módulos `rag.py` en el mismo `sys.path`
> colisionan: `from rag import ...` desde `data/pipelines/rag.py` se resolvería
> al propio archivo.

---

## 1. Proceso RAG de extremo a extremo

**Indexación** (offline, se ejecuta a mano cuando cambia el corpus):

1. `load_documents()` lee los cuatro `.md` de `docs/company-knowledge-base/` y
   asigna a cada uno su `source_document` literal del CONTEXT.
2. `chunk_document()` parte cada documento en chunks semánticos (§2).
3. `setup()` verifica que ningún documento baje de 3 chunks, llama a `embed()`
   por chunk y hace `upsert` en la colección Qdrant `brasaland_knowledge`.
4. Se borran los puntos sobrantes de cada documento (los de `chunk_index` mayor
   o igual al número actual de chunks), por si el documento encogió.

```
cd services/api && uv run python ../../data/process/rag_index.py
```

**Consulta** (en caliente, por cada pregunta):

1. La UI (`/knowledge`) envía `POST /knowledge/query` con `{ "question": "..." }`.
2. El router delega en `query()` — no tiene lógica propia de RAG.
3. `query()` = `retrieve()` + `generate_answer()`, nada más.
4. `retrieve()` embebe la pregunta con **la misma** `embed()` que se usó al
   indexar, pide los `k=5` vecinos más cercanos y descarta los que quedan por
   debajo de `MIN_SCORE`. Puede devolver menos de 5, o ninguno.
5. `generate_answer()` arma el prompt con los chunks supervivientes y llama al
   modelo de generación.
6. El endpoint devuelve **solo** `{ "answer": "..." }`.

```
Pregunta
   │
   ├─ embed(pregunta) ──► Qdrant: brasaland_knowledge (coseno, top-5)
   │                            │
   │                            └─ filtro min_score ──► 0..5 payloads
   │                                                        │
   └────────────────────────────► prompt = sistema + contexto + pregunta
                                                            │
                                            LLM de generación
                                                            │
                                                      answer (string)
```

Los chunks, las puntuaciones y los resultados crudos de Qdrant **nunca** salen
al cliente. Se registran con `logging` del lado servidor, que es donde sirven
para depurar y afinar el umbral.

**La respuesta final siempre la genera el modelo.** No hay ningún camino que
devuelva texto de la base vectorial directamente — ni siquiera cuando no se
recupera nada: ese caso también pasa por `generate_answer()` con contexto
vacío, y es el modelo quien responde que no tiene la información. Hay un test
que lo fija (`test_query_llama_a_generate_answer_aunque_no_haya_contexto`).

---

## 2. Estrategia de chunking

### El dato que la determina

Los cuatro documentos fuente tienen **un solo encabezado Markdown cada uno: el
`#` del título. Cero `##`, cero `###`.** Son de 1,0 a 1,5 KB; el corpus entero
son unos 5 KB.

Eso descarta la estrategia por defecto: **chunkear por nivel de encabezado
produciría exactamente un chunk por documento**, que es lo que el CONTEXT §5
prohíbe ("ni un chunk por documento, ni un chunk por línea"). Y el tamaño fijo
con solapamiento cortaría reglas por la mitad — en un corpus donde cada regla
es un umbral operativo ("superior a 2 kg", "más del 3%"), partir una condición
de su consecuencia la vuelve inútil o, peor, engañosa.

### Qué se hace en su lugar

La estructura semántica real vive en **bloques separados por línea en blanco**.
Cada bloque es una unidad autocontenida: una regla, un procedimiento, una tabla
de niveles. Varios tienen la forma *línea de entrada terminada en `:` seguida de
su lista* (`Niveles del programa:` + Bronce/Plata/Oro).

1. El cuerpo se parte en bloques por línea en blanco.
2. **Cohesión entrada + lista:** si una lista quedara separada de su línea de
   entrada por una línea en blanco, se vuelven a unir. En el corpus actual esto
   nunca se dispara —se verificó que cada `:` ya viene pegado a su lista— pero
   los documentos viven en `docs/` y los edita gente de operaciones: una línea
   en blanco de más separaría "Niveles del programa:" de sus tres niveles y
   degradaría la recuperación en silencio. Mismo criterio defensivo que
   `validate_weekly_rows()` en `weekly_aggregation.py`.
3. Cada chunk se prefija con su **ruta de contexto**, `<título> > <sección>`.
   Sin subtítulos en el original, esto es lo que hace que un chunk siga
   teniendo sentido cuando llega solo al prompt: "15% de descuento permanente"
   no dice nada; "Programa de Lealtad «Brasa Points» > Niveles del programa —
   Oro (50+ puntos): 15% de descuento permanente" sí.
4. **No se subdivide por tamaño.** El bloque más largo del corpus son 505 B,
   muy por debajo de cualquier límite de tokens relevante. Añadir una regla de
   troceo que nunca se ejecuta sería código muerto.

### Nombre de sección

El CONTEXT §3 pide `section` = "título o subtítulo de la sección de origen".
Sin subtítulos, se deriva en este orden:

1. La línea de entrada de una lista, sin los dos puntos → `Niveles del programa`.
2. Un rótulo corto (≤ 6 palabras) al abrir un párrafo → `Regla de stock mínimo`,
   `Meta operativa`.
3. Si no hay ninguno, el título del documento. Es el caso de los párrafos
   introductorios y sueltos: 6 de los 18 chunks. Es la lectura fiel del CONTEXT
   —el título es el único encabezado que existe— y la trazabilidad no se pierde,
   porque `source_document` y `chunk_index` identifican el chunk sin ambigüedad.

### Conteo resultante

| Documento | Chunks | Secciones |
| --- | --- | --- |
| `loyalty-program` | 5 | intro · Niveles del programa · redención · tarjeta física/app · Preguntas frecuentes |
| `waste-protocol` | 5 | intro/categorías · Procedimiento diario · causas aceptadas · Causas que requieren escalamiento · Meta operativa |
| `menu-allergens` | 4 | intro/normativa · Platos y alérgenos · Protocolo ante alergias · nota sin gluten |
| `supplier-ordering` | 4 | intro/lunes 10 a.m. · Categorías y frecuencia · Regla de stock mínimo · aprobación |
| **Total** | **18** | |

`setup()` falla si algún documento baja de 3 chunks, en vez de dejar pasar un
corpus mal fragmentado.

---

## 3. Prácticas de embeddings

### Modelos

| Rol | Variable | Valor |
| --- | --- | --- |
| Embeddings | `EMBEDDING_MODEL` | `text-embedding-3-small` |
| Generación | `GENERATION_MODEL` | modelo de chat (ver `.env`) |

Son **IDs distintos**: `embed()` nunca usa el modelo de generación y
`generate_answer()` nunca usa el de embeddings. Cada uno lee su propia variable
y falla si falta, en vez de caer en un valor por defecto compartido.

No se usan los modelos gratuitos de 4Geeks que el rule prefiere porque no hubo
acceso a esas credenciales; se sustituyen por la API de OpenAI. El rule dice
"prefiere", no "debes", y esto queda documentado aquí como decisión explícita.
Cambiar de proveedor toca dos funciones — `embed()` y `generate_answer()`— y
ninguna otra parte del pipeline.

### `embed()` es una sola función

La misma `embed()` de `data/process/rag_index.py` embebe los chunks al indexar
y la pregunta del usuario al consultar (`data/pipelines/rag.py` la importa, no
la reimplementa). Si el modelo o la normalización cambian, cambian a la vez en
los dos lados — que es la única forma de que los vectores sigan siendo
comparables.

### Normalización

`normalize()` colapsa espacios y saltos de línea, y nada más. No se quitan
acentos ni se pasa a minúsculas: en español el acento distingue palabras y el
modelo de embeddings maneja mayúsculas sin ayuda. Se aplica igual a los chunks
y a la pregunta.

### Colección Qdrant

- **Nombre:** `brasaland_knowledge` (literal del CONTEXT §2).
- **Métrica:** distancia **coseno** — la adecuada para embeddings de texto, que
  codifican la similitud en la dirección del vector, no en su magnitud.
- **Dimensión:** se lee del primer vector que devuelve el modelo, no se
  hardcodea. Si se cambia de modelo de embeddings, `setup()` detecta que la
  dimensión ya no coincide y recrea la colección en vez de fallar al insertar.
- **Idempotencia:** los IDs de punto son `uuid5` deterministas sobre
  `(source_document, chunk_index)`, con `upsert`. Reindexar un documento
  editado **sobrescribe** sus puntos en vez de crear duplicados y dejar los
  viejos huérfanos. Se eligió esto sobre limpiar-y-recargar porque permite
  reindexar sin tirar la colección entera. El ID no incluye un hash del texto
  justamente para que editar un chunk actualice el punto existente.

### Umbral de similitud

`MIN_SCORE = 0.35` en `data/pipelines/rag.py`.

Con solo 18 chunks, **casi cualquier pregunta tiene algún vecino**: el vecino
más cercano a "¿cuál es el horario del local de Miami?" existe aunque el corpus
no diga nada de horarios. El umbral es por tanto lo único que separa un "no
tengo esa información" honesto de una respuesta construida sobre un chunk
irrelevante — importa más aquí que en un corpus grande.

Para afinarlo:

```
uv run --project services/api python data/eval/recall_at_3.py --sweep
```

Hace un barrido de umbrales y devuelve el Recall@3 de cada uno, medido contra
las 12 preguntas de `data/eval/test-queries.json`. El criterio es el umbral más
alto que aún cumple el ≥ 80% del CONTEXT: subirlo todo lo posible sin perder
recall maximiza la honestidad ante preguntas fuera del corpus.

> **Pendiente de la primera corrida en vivo:** la dimensión concreta del vector,
> el resultado del barrido y el `MIN_SCORE` final se anotan aquí tras ejecutar
> `setup()` y `recall_at_3.py` con credenciales. El `0.35` actual es el punto de
> partida, no un valor medido.

---

## 4. Voz y restricciones de negocio

El prompt de sistema (`SYSTEM_PROMPT` en `data/pipelines/rag.py`) fija la voz
del CONTEXT: responde **a un gerente de local, como lo haría un vendedor
entrenado** — directo y accionable, en español. Además impone cuatro reglas que
vienen del CONTEXT §6, no del gusto del modelo:

1. **Solo el contexto recuperado.** Nada de conocimiento general sobre
   restaurantes ni sobre Brasaland.
2. **Ningún dato numérico inventado.** El corpus está lleno de umbrales fáciles
   de alucinar (2 kg, 3%, 5 kg, 4%, 6%, 8%, 48 h, 15 puntos, 50 puntos): es
   justo el riesgo que mide el KPI de *faithfulness* del CONTEXT §4.
3. **Sin conversión de moneda.** Los montos en COP y USD se citan tal como
   aparecen en la fuente.
4. **Alérgenos al pie de la letra.** Nunca se afirma que un plato sea seguro o
   "sin riesgo": el protocolo de Brasaland es que *nunca se garantiza cero
   riesgo de contaminación cruzada*, y el modelo debe reproducir esa redacción.

---

## 5. Cómo verificarlo

```bash
# 1. Levantar Qdrant e indexar
docker compose up -d qdrant
cd services/api && uv run python ../../data/process/rag_index.py

# 2. Tests unitarios (sin Qdrant ni LLM — todo mockeado)
uv run --project services/api python -m pytest tests/pipelines/test_rag.py

# 3. Recall@3 contra el set de evaluación
uv run --project services/api python data/eval/recall_at_3.py

# 4. Endpoint
curl -X POST http://localhost:8000/knowledge/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"¿cuántos puntos necesito para el nivel Oro?"}'
```

Casos que conviene probar a mano, porque son los que distinguen un RAG honesto
de uno que improvisa:

- **Fuera del corpus** — "¿cuál es el horario del local de Miami?" debe decir
  que no tiene la información, no inventar un horario.
- **Alérgenos** — "¿la Costilla BBQ es segura para alguien con alergia al
  maní?" debe mencionar las trazas de maní y **no** afirmar que es segura.
- **Moneda** — una pregunta sobre el recargo del 8% o el límite de 500 USD debe
  citar las cifras sin convertirlas.
