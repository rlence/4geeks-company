"use client";

import { Suspense } from "react";
import { InboundOrderForm } from "@/components/inventory/InboundOrderForm";
import { useRequireAuth } from "@/hooks/useRequireAuth";

const InboundOrderPageContent = () => {
  const ready = useRequireAuth();
  if (!ready) return null;

  return (
    <main className="mx-auto max-w-lg p-6">
      <h1 className="mb-1 text-2xl font-bold">Registrar Entrada de Ingredientes</h1>
      <p className="mb-4 text-gray-600">Entrega recibida de un proveedor</p>
      <InboundOrderForm />
    </main>
  );
};

export default function InboundOrderPage() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-lg p-6">Cargando…</main>}>
      <InboundOrderPageContent />
    </Suspense>
  );
}
