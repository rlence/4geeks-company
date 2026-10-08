# Memoria del agente de gerentes — Hito 8, parte 1

## Alcance y arquitectura

El agente existente de `support_agent/` mantiene su identidad y sus rutas RAG/MCP. La memoria episódica usa `services/api/.agent-runtime/memory.sqlite`, separada de `checkpoints.sqlite` y de la colección Qdrant `brasaland_knowledge`. El RAG documental y las incidencias actuales siguen siendo fuentes distintas. El repositorio expone `read_relevant`, `create_proposal`, `resolve_proposal`, `revise_pending`, `expire_pending` y `consolidate`. No se usa VectorDB porque el conjunto es pequeño y los filtros son estructurados; un knowledge graph no aporta a usuario/local/categoría; fine-tuning impediría revocar una corrección individual.

SQLite tiene una tabla de versión de esquema, WAL, índices de lectura, unicidad de recuerdo por `(owner_id, scope_key, category, subject_key)`, una propuesta pendiente por conversación y transacciones `BEGIN IMMEDIATE`. El upsert del recuerdo y la decisión auditada se confirman en la misma transacción. El límite es 100 recuerdos activos por usuario; al alcanzarlo se rechaza una nueva clave en vez de borrar silenciosamente. El servicio serializa turnos de una conversación dentro del proceso; antes de usar varias réplicas se debe migrar a un almacén compartido y un bloqueo distribuido. El directorio `.agent-runtime/` requiere volumen persistente y copia de seguridad en despliegue.

## Identidad y contrato

`POST /agent/query` acepta `question` y un `conversation_id` UUID opcional. Con bearer válido, el servidor usa `user.doc_id` de TinyDB, crea un identificador opaco en el primer turno y verifica su propietario en cada turno siguiente. La respuesta incluye `answer` y `conversation_id`; `X-Agent-Run-Id` sigue identificando la corrida. El cliente debe reenviar el identificador. Una petición anónima conserva el contrato anterior `{answer}` y nunca lee o escribe memoria. Enviar un `conversation_id` sin autenticación devuelve 401; uno ajeno o inexistente devuelve 409. El bearer que llega al MCP de incidencias sigue siendo el validado por la API.

El `conversation_id` es el `thread_id` del checkpoint LangGraph. Un `run_id` distinto identifica cada petición y su traza. La traza de un turno autenticado guarda solo nodos, ruta y estado, sin pregunta, respuesta ni salida cruda del evaluador; la auditoría de memoria guarda el hecho permitido, una cita breve del usuario, el hash de la pregunta, el hash del mensaje de decisión, usuario y fechas. Una pregunta que coincida con los filtros de contenido sensible se ejecuta sin checkpoint persistente y no se evalúa para memoria.

## Flujo de consentimiento

1. Si hay propuesta pendiente, el mismo agente clasifica el siguiente mensaje mediante una salida JSON validada: `approve`, `reject`, `edit`, `unrelated` o `ambiguous`, con confianza y una posible pregunta adicional. Se exige confianza ≥ 0,8 y, para `approve`, el campo `explicit_approval=true`. Si falla el clasificador o falta esa señal, se descarta la propuesta.
2. `approve` guarda el hecho y la decisión en una transacción. `reject` deja solo el registro auditable. `edit` sin aprobación explícita modifica la propuesta pendiente y pide confirmación de la versión exacta; con aprobación clara guarda esa versión. `unrelated` descarta y atiende la nueva pregunta. Ambigüedad o confianza baja descartan.
3. Las propuestas vencen a las 24 horas y quedan auditadas como `expired` al siguiente acceso. Nunca se aprueban por silencio.
4. Tras resolver una propuesta, el mismo turno atiende `remaining_question` si existe. Mientras una propuesta está pendiente no se crea otra.
5. Antes de responder, el repositorio recupera como máximo cinco recuerdos activos del usuario. Las preferencias de comunicación son personales; los hechos operativos solo se consultan cuando la pregunta incluye un ID de local explícito. Al generar, documentos, datos MCP y recuerdos se presentan por separado. El recuerdo se etiqueta como aprobado por el usuario y la fuente oficial prevalece en caso de discrepancia.
6. Después de una respuesta completada, el mismo agente ejecuta la autoevaluación estructurada. Esta integración usa una llamada adicional al modelo para preservar el generador RAG actual; no introduce un segundo agente. La propuesta se valida otra vez en código y se muestra dentro de la misma respuesta. Si el evaluador falla, la respuesta original sigue disponible sin propuesta.

## Política de Brasaland

Se admiten `schedule`, `supplier_delivery`, `local_exception`, `resolved_escalation` y `communication_preference`. La propuesta debe incluir un fragmento exacto del mensaje del usuario y un `subject_key` estable. Los hechos operativos requieren el ID 1–14 escrito como «local N», «location N» o «sede N» por el usuario; «Medellín» sin ID exige aclaración, porque este repositorio no tiene un mapeo fiable de nombres a IDs. Los recuerdos pertenecen solo al usuario que los aprobó: aún no se comparten entre gerentes.

El validador descarta preguntas o propuestas que indiquen datos personales de clientes, Brasa Points, nómina o compensación, identificadores de contacto y situaciones sin patrón estable. El evaluador debe descartar consultas puntuales y respuestas generadas por el agente. Una aprobación registra voluntad de recordar, no prueba la veracidad de un horario o proveedor. Ante contradicción con documentación actual, el prompt de evaluación exige no proponer; las memorias recuperadas se tratan como datos no confiables y no autorizan cambios en tickets, inventario o documentos. Las cifras COP/USD no se convierten ni se mezclan.

Ejemplos que **pueden proponer** tras confirmar el ID del local: «el proveedor del local 7 entrega los miércoles, no los martes»; «el local 4 ahora cierra a las 11 pm todos los viernes»; «la alerta de cero ventas del local 7 se debió dos veces a un corte programado». Una preferencia duradera como «envíame siempre los resúmenes en viñetas» también puede proponer. Ejemplos que **no proponen**: «¿cuál fue el ticket promedio de ayer?»; «gracias»; «traduce esto al inglés para Ashley»; una queja aislada de un cliente.

## Consolidación, caducidad y límites

Los hechos de horario, entrega y excepción se dejan de recuperar a los 90 días; las escalaciones resueltas, a los 30; preferencias de comunicación, a los 180. La caducidad marca el registro como `expired`; no afirma que el hecho haya cambiado. Una nueva propuesta aprobada para la misma clave reemplaza el hecho activo y deja la versión anterior en auditoría. `consolidate()` aplica vencimientos de forma idempotente y puede ejecutarse al iniciar, al acceder o desde una tarea programada. Las filas de auditoría no se purgan automáticamente: Operaciones debe fijar su plazo formal de retención antes de producción. Una solicitud de borrado requiere un flujo autenticado y auditable; no se ha expuesto todavía un endpoint de borrado.

## Evidencia reproducible

Las pruebas de `services/api/tests/test_agent_memory.py` simulan solamente el proveedor de generación y ejecutan el grafo, SQLite y el servicio reales. No son evidencia de calidad del modelo en producción.

| Ciclo | Turnos y comprobación |
| --- | --- |
| Aprobado | Corrección del proveedor del local 7 → propuesta pendiente → «Sí, recuérdalo» → auditoría `proposed, approved` y un recuerdo activo → cierre y reapertura del servicio → pregunta sobre el proveedor recupera «miércoles». |
| Rechazado | Misma corrección → propuesta pendiente → «No, no lo recuerdes» → auditoría `proposed, rejected`, cero recuerdos activos. |

Hay pruebas adicionales de edición que pide nueva confirmación, descarte por cambio de tema, vencimiento, deduplicación, rollback si falla la auditoría, aislamiento entre usuarios y exclusión de datos sensibles. `services/api/tests/test_agent.py` cubre además el contrato HTTP autenticado. Para reproducir desde la raíz del monorepo:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_agent_memory.py services/api/tests/test_agent.py -q
```

El 8 de octubre de 2026 se ejecutó además un ciclo temporal con el gateway real configurado: el clasificador de fuente y la recuperación RAG se fijaron a respuestas simuladas para aislar la memoria, mientras la autoevaluación, la clasificación del «sí» y la respuesta que usa el recuerdo llamaron al modelo real. La secuencia observada fue `proposed=True`, `approved=1`, `used_memory=True`; la respuesta posterior atribuyó el miércoles a un recuerdo aprobado por el usuario y aclaró que no había documento oficial. La base SQLite de esa prueba se creó en un directorio temporal y se eliminó al terminar. Esta evidencia verifica el contrato del modelo en ese caso, no la precisión de todas sus propuestas ni un flujo completo de proveedores reales.

Siguen pendientes la revisión humana de propuestas en español e inglés y una demostración estable con el RAG y el clasificador de fuentes reales. No se debe presentar la evidencia simulada como captura de una llamada real.
