# Harness del Manager support agent — Hito 8, parte 2

El agente existente conserva RAG, MCP de incidencias y memoria con consentimiento. La política `manager_support` procede del contexto de Brasaland para Hito 8 Parte 2: operaciones de 14 sedes, conversación casual breve con reconducción y rechazo de tareas personales, cambios de instrucciones y datos confidenciales.

## Límites de confianza

1. `AgentService._guarded_query` valida identidad/propietario y controla la pregunta antes de resolver consentimiento o consultar fuentes. Un ataque descarta una propuesta pendiente sin aprobarla. Entrada ambigua y clasificación semántica fallida piden precisión.
2. `guardrails/input.py` combina normalización Unicode, reglas deterministas y clasificación semántica para entradas no reconocidas. La decisión semántica se valida contra un enum cerrado; no puede anular un rechazo determinista. Saludos y hora de Tokio se resuelven localmente; otra trivia usa una llamada acotada, sin tools/memoria y con reconducción añadida por el servidor.
3. `guardrails/external.py` descarta documentos y recuerdos comprometidos antes de que el grafo pueda checkpointarlos. El adaptador MCP valida campos tipados, enums, IDs, fechas con zona y límites de colección. Los campos ajenos a la proyección autorizada se omiten. La reescritura RAG del router debe proceder de la pregunta y no contener instrucciones prohibidas.
4. `prompts.py` mantiene instrucciones de servidor separadas del contenido externo. El generador RAG admite `system_prompt` opcional y serializa documentos/pregunta como datos de usuario; `/knowledge/query` conserva su comportamiento previo. El harness de manager se aplica a `/agent/query`, no convierte `/knowledge/query` en un endpoint protegido para datos privados.
5. `guardrails/output.py` comprueba estructura, contenido sensible y fragmentos literales de prompts de servidor. Cada respuesta de nodo se valida antes de checkpointarla; el servicio valida la composición final, incluidos retornos de consentimiento. Propuestas y ediciones se validan antes de escribir; el repositorio vuelve a validar en la transacción de aprobación. No se autoevalúan respuestas que hayan sufrido un bloqueo de fuentes o salida.

La política prohíbe fórmulas madre, contratos/precios negociados de proveedores, nómina/desempeño ajeno y PII. Permite conservación, alérgenos, procedimientos y consultas operativas sin esos datos. La autorización sigue en API/MCP; mencionar un local o aprobar un recuerdo no concede acceso.

## Extracción gradual y persistencia

La migración de memoria v3 añade `security_context`, separada de propuestas y recuerdos: conversación, propietario, tema abstracto, contador y fecha. No guarda fórmulas, ingredientes ni transcripciones. El rechazo de una consulta sensible activa esa referencia; preguntas elípticas posteriores sobre cantidades/ingredientes se rechazan también, incluso tras reiniciar. La comprobación de propietario precede a leer o actualizar este estado. Se elimina al acceder cuando lleva 24 horas inactivo.

El bloqueo de conversación existente serializa dentro del proceso; SQLite usa transacciones. Esta implementación no ofrece coordinación distribuida entre varias réplicas. Las consultas anónimas no tienen continuidad entre peticiones: reciben protección por turno, sin correlación de identidad. Una consulta operativa clara puede continuar después de un bloqueo; no se bloquea toda la conversación.

## Respuestas y observabilidad

Un rechazo devuelve HTTP 200 con `answer`, `X-Agent-Run-Id` y `conversation_id` solo si existe identidad autenticada. Se conservan 401/409 para identidad/propiedad, 422 para entrada inválida y 503 para fallos internos.

Las trazas v4 añaden `guardrails`: agente, corrida, guardrail, categoría `structural|content|security`, acción `block|redirect`, motivo enumerado por código, versión y fecha. Tanto trazas anónimas como autenticadas omiten pregunta, respuesta y outputs crudos. La lectura de v1–v3 se conserva. Los checkpoints conservan estado validado; no se insertan payloads descartados por los filtros. Las excepciones externas no se registran en crudo.

```bash
services/api/.venv/bin/python scripts/summarize_agent_guardrails.py /ruta/a/traces-de-la-sesion
services/api/.venv/bin/python scripts/validate_agent_guardrails.py --output /tmp/guardrails-evidence.json
```

El resumen cuenta eventos por guardrail, categoría y acción, deduplica por corrida e informa archivos inválidos con salida no cero. No requiere endpoint de administración. `guardrails-evidence.json` es evidencia sintética explícita; sus UUID no son identidades de clientes.

## Compatibilidad y límites

- No hay nuevas dependencias ni cambios de permisos. Inventario en vivo todavía no está conectado al agente; se explica y se remite al gestor. Los procedimientos de inventario siguen pudiendo usar RAG.
- Los archivos históricos de trazas/checkpoints no se borran automáticamente. Antes de producción, revisar acceso y retención, y migrarlos/retirarlos mediante un procedimiento autorizado. Los antiguos evals de contenido sobre trazas v1–v3 siguen siendo históricos; una traza v4 no prueba grounding porque ya no contiene texto. Los nuevos tests inspeccionan resultados y mocks en memoria sin guardar secretos.
- Reglas deterministas y prompts no garantizan detección de toda paráfrasis, ofuscación o extracción entre cuentas. La clasificación semántica complementa entradas ambiguas; la calidad del proveedor requiere smoke y evaluación humana aparte.
- No se afirma aislamiento por local más allá de los permisos del backend, ni se proporciona PII porque el cliente alegue estar autorizado. `manager_support` no modifica tickets o inventario.
