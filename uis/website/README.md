# Brasaland — Sitio Web Público

Landing page pública + programa de fidelización "Brasa Points". Migrado en el Hito 4 del HTML estático del Hito 1 a Next.js + TypeScript, con componentes React reutilizables.

Ver contexto completo en [`/CONTEXT.md`](../../CONTEXT.md) y el plan en `context/plans/hito4.md` (fuera de este repositorio).

## Stack

- Next.js (App Router) + TypeScript.
- Tailwind CSS (vía el scaffold, no CDN).
- Sin librerías externas de gestión de estado ni de formularios.

## Estructura

```
uis/website/
└── src/
    ├── app/
    │   ├── layout.tsx          # metadata, JSON-LD de Restaurant
    │   ├── page.tsx             # "/" — landing pública
    │   └── brasa-points/
    │       └── page.tsx         # "/brasa-points" — registro al programa de fidelización
    ├── components/
    │   ├── NavBar.tsx
    │   ├── Hero.tsx
    │   ├── OurStory.tsx
    │   ├── WhatMakesUsUnique.tsx
    │   ├── Locations.tsx
    │   ├── Menu.tsx
    │   ├── BrasaPointsTeaser.tsx
    │   ├── Contact.tsx
    │   ├── Footer.tsx
    │   └── BrasaPointsForm.tsx  # "use client" — selects dependientes país→ciudad→ubicación + validación
    └── lib/
        └── formOptions.ts        # datos y validadores del formulario Brasa Points
```

## Cómo levantarlo

```bash
cd uis/website
npm install
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000).

## Notas

- El envío del formulario de Brasa Points sigue siendo simulado: no hay backend conectado.
- Los nombres de campos, ciudades y ubicaciones coinciden con los del Hito 1 original.
