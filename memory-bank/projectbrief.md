# Project Brief — Brasaland

## Qué es Brasaland

Brasaland es una cadena de restaurantes de cocina a la brasa con **14 locales en Colombia y Estados Unidos (Florida)**. Factura ~$6M/año y hoy opera con herramientas pensadas para un único restaurante local (WhatsApp, Excel, tarjetas de sello físicas), no para una cadena multipaís con dos monedas (COP/USD), dos idiomas y dos zonas horarias.

Este monorepo es el núcleo técnico de **Brasaland Digital**, la unidad tecnológica interna de la empresa. Todo lo que se construye aquí — sitio web, herramientas internas, agentes, automatizaciones — vive en este mismo repositorio y debe ser coherente entre sí.

## Departamentos y problemas que resolvemos

### 🍖 Operaciones de restaurante

Responsable: Felipe Guerrero.

Cada uno de los 14 locales opera de forma aislada. No hay visibilidad centralizada de ventas en tiempo real (cubiertos servidos, ticket medio). Los pedidos de ingredientes se hacen por WhatsApp o teléfono sin datos de stock detrás, lo que provoca exceso de inventario en unos locales y roturas de stock en otros. No hay alertas cuando un local abierto no reporta ventas.

Lo que se necesita resolver:
- Ver ventas y cubiertos en tiempo real, por local y consolidado, en COP y USD.
- Saber cuándo un local se está quedando sin un ingrediente clave.
- Sugerir automáticamente pedidos de reposición en vez de depender de la intuición del encargado.
- Alertar cuando un local abierto lleva tiempo sin registrar ventas.

### 🎓 Formación y estándares de calidad

Responsable: Jake Morrison.

Las recetas y estándares de preparación viven en un Google Drive compartido difícil de navegar. Cuando cambia una receta, comunicarlo a los 14 locales en dos idiomas lleva días y genera confusión sobre qué versión está vigente. El onboarding de personal de cocina (con alta rotación) es manual.

Lo que se necesita resolver:
- Publicar una nueva versión de receta y saber qué locales la han confirmado.
- Buscar recetas por texto, categoría o ingrediente, en el idioma del usuario con fallback a español.
- Dar de alta a un empleado nuevo con un itinerario de onboarding con progreso visible.
- Conectar recetas con ingredientes reales para, a futuro, descontar stock automáticamente al vender un plato (puente entre Formación y Operaciones).

## Objetivo del proyecto

> Dar visibilidad y control en tiempo real a Operaciones de restaurante (ventas, stock y pedidos sugeridos por local) y estandarizar la Formación (recetas versionadas y onboarding) a través de los 14 locales de Brasaland en Colombia y EE. UU., cerrando la brecha entre lo que pasa en cada local y lo que sabe la sede en Medellín.

Se considera alcanzado cuando, sin llamadas ni hojas de Excel, se puede responder:
- **Operaciones:** ¿cuánto llevamos vendido hoy, por local y consolidado? ¿qué local se está quedando sin un ingrediente? ¿qué local abierto no ha reportado ventas?
- **Formación:** ¿qué versión de una receta está vigente en cada local? ¿qué locales aún no la han confirmado? ¿en qué punto de su onboarding está cada empleado nuevo?

## Encargo activo (Hito 3 — vigente en `CONTEXT.md`)

Ashley Turner (People Manager) necesitaba reemplazar una hoja de Google Sheets propensa a pérdida de datos por una herramienta de selección de personal (Talent Pipeline Tracker) para gestionar candidaturas al puesto de Asistente de Dirección: listado con filtros, detalle con cambio de estado/etapa, notas internas, alta y edición de candidatos. Ya implementado en `uis/talent-pipeline-tracker` (Hito 3, entregado).

## Fuentes

- [`CONTEXT.md`](../CONTEXT.md) — contexto detallado del encargo activo (selección de personal).
- [`company-choice.md`](../company-choice.md) — panorama completo de la empresa y los dos departamentos.
