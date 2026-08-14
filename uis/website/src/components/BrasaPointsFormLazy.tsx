"use client";

import dynamic from "next/dynamic";

// `next/dynamic` con `ssr: false` no está permitido dentro de un Server
// Component (page.tsx sigue siendo uno, exporta `metadata`) — este
// wrapper cliente es lo que habilita diferir la carga.
export const BrasaPointsForm = dynamic(
  () => import("./BrasaPointsForm").then((mod) => mod.BrasaPointsForm),
  {
    ssr: false,
    loading: () => <p className="mt-10 text-sm text-gray-400">Cargando formulario…</p>,
  },
);
