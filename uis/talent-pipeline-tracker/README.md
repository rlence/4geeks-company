# Talent Pipeline Tracker — Brasaland

Frontend interno de People & Talent para gestionar el pipeline de candidaturas al puesto de **Asistente de Dirección** (Hito 3). Consume la API REST compartida del curso — no hay backend propio en este proyecto.

## Stack

- Next.js (App Router) + TypeScript
- Tailwind CSS
- `fetch` nativo con `async/await`, sin librerías de estado externas (solo hooks de componente)

## Cómo levantar el proyecto

1. Instala dependencias:

   ```bash
   npm install
   ```

2. Crea `.env.local` a partir de `.env.example` (ya incluye la URL pública de la API del curso):

   ```bash
   cp .env.example .env.local
   ```

3. Arranca el servidor de desarrollo:

   ```bash
   npm run dev
   ```

4. Abre [http://localhost:3000](http://localhost:3000).

## Variables de entorno

| Variable | Descripción |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL base de la API del Talent Tracker (`https://playground.4geeks.com/tracker/api/v1`) |

## Estructura

```
src/
├── app/                    # rutas (App Router): listado, detalle, alta, edición
├── components/             # filtros, formulario, panel de notas, controles de estado/etapa
├── hooks/                  # useCandidates (listado con filtros + paginación)
├── lib/                    # api.ts (wrapper fetch) y labels.ts (etiquetas de dominio)
└── types/                  # tipos TypeScript de los datos de la API
```
