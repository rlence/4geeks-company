"use client";

import { Suspense } from "react";
import { OutboundOrderForm } from "@/components/inventory/OutboundOrderForm";
import { useRequireAuth } from "@/hooks/useRequireAuth";

const OutboundOrderPageContent = () => {
  const ready = useRequireAuth();
  if (!ready) return null;

  return (
    <main className="mx-auto max-w-lg p-6">
      <h1 className="mb-1 text-2xl font-bold">Registrar Salida de Ingredientes</h1>
      <p className="mb-4 text-gray-600">Consumo o merma</p>
      <OutboundOrderForm />
    </main>
  );
};

export default function OutboundOrderPage() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-lg p-6">Cargando…</main>}>
      <OutboundOrderPageContent />
    </Suspense>
  );
}
