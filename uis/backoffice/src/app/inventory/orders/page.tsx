"use client";

import { OrderHistoryTable } from "@/components/inventory/OrderHistoryTable";
import { useInventoryOrders } from "@/hooks/useInventoryOrders";
import { useRequireAuth } from "@/hooks/useRequireAuth";

export default function InventoryOrdersPage() {
  const ready = useRequireAuth();
  const { status, orders, error } = useInventoryOrders();

  if (!ready) return null;

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="mb-1 text-2xl font-bold">Historial de Órdenes de Inventario</h1>
      <p className="mb-4 text-gray-600">Entradas y salidas registradas — solo lectura</p>

      {status === "loading" && <p>Cargando órdenes…</p>}
      {status === "error" && <p className="text-red-600">{error}</p>}

      {status === "success" && (
        <>
          <OrderHistoryTable orders={orders} />
          {orders.length === 0 && <p className="mt-4 text-gray-500">No hay órdenes registradas todavía.</p>}
        </>
      )}
    </main>
  );
}
