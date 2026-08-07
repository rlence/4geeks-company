# Regla: importar, no copiar código entre hitos

**Alcance:** siempre activa — aplica a todo el monorepo, en cualquier sesión.

## Regla

Nunca copiar código de un paquete o app de un hito ya entregado (por ejemplo `packages/data-utils` o `uis/talent-pipeline-tracker`) a otro lugar del monorepo. Si una funcionalidad nueva necesita esa lógica, se **importa** desde su ubicación original.

## Por qué

Evita que existan dos copias del mismo código que puedan divergir con el tiempo, y respeta que esos hitos ya fueron evaluados como entregas cerradas — modificarlos o duplicarlos invalida esa evaluación.

## Cómo aplicarla

- Antes de escribir una función que "ya existe en otro sitio del repo", buscarla primero en `packages/` y en apps de hitos anteriores.
- Si el paquete de origen vive fuera del directorio del proyecto que lo consume (por ejemplo, una app Next.js en `uis/` importando desde `packages/`), resolver el import correctamente en la configuración del proyecto (p. ej. `experimental.externalDir` en Next.js) en vez de copiar los archivos. En este monorepo, `experimental.externalDir` solo funciona con el compilador **webpack** de Next.js (no con Turbopack, el default desde Next 16) — ver `uis/backoffice/next.config.ts` como referencia funcional, incluyendo el `extensionAlias` necesario para paquetes con resolución NodeNext (`.js` → `.ts`).
- Si de verdad hace falta una versión distinta de esa lógica (comportamiento diferente, no solo mismo código), es una decisión de diseño que se documenta explícitamente, no una copia silenciosa.
