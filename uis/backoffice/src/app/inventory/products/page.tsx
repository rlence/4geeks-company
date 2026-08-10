"use client";

import { ProductTable } from "@/components/inventory/ProductTable";
import { useIngredients } from "@/hooks/useIngredients";
import { useRequireAuth } from "@/hooks/useRequireAuth";

export default function InventoryProductsPage() {
  const ready = useRequireAuth();
  const { status, ingredients, error } = useIngredients();

  if (!ready) return null;

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="mb-1 text-2xl font-bold">Inventario de Ingredientes</h1>
      <p className="mb-4 text-gray-600">Operaciones · Stock por ingrediente en toda la cadena</p>

      {status === "loading" && <p>Cargando ingredientes…</p>}
      {status === "error" && <p className="text-red-600">{error}</p>}

      {status === "success" && (
        <>
          <ProductTable ingredients={ingredients} />
          {ingredients.length === 0 && <p className="mt-4 text-gray-500">No hay ingredientes registrados.</p>}
        </>
      )}
    </main>
  );
}
