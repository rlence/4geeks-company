# Brasaland — Sitio Web Público (Hito 1)

Landing page pública + formulario de registro al programa de fidelización "Brasa Points".
Ver contexto completo en [`/CONTEXT.md`](../../CONTEXT.md) y el plan en [`/context/plans/hito1.md`](../../context/plans/hito1.md).

## Stack

- HTML5 semántico, sin framework ni build step.
- Tailwind CSS vía CDN.
- JavaScript vanilla (sin librerías externas).
- Un solo idioma: español.

## Estructura

```
uis/website/
├── index.html        landing page
├── application.html  formulario de registro Brasa Points
├── validation.js       validaciones y campos país→ciudad→ubicación dependientes
└── README.md
```

## Cómo levantarlo (compatible con Codespaces)

Desde la raíz del repositorio:

```bash
npx http-server uis/website -p 3000 -a 0.0.0.0
```

Luego abre `http://localhost:3000` (o la URL/puerto reenviado por Codespaces).

## Notas

- El envío del formulario es simulado: no hay backend conectado.
- Los nombres de campos, ciudades y ubicaciones deben coincidir exactamente con `CONTEXT.md`.
