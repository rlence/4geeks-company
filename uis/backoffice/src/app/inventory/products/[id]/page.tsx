"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { getIngredient, getApiErrorMessage } from "@/lib/inventoryApi";
import { CATEGORY_LABELS, COUNTRY_LABELS } from "@/lib/inventoryLabels";
import type { Ingredient } from "@/types/inventory";

type State = { status: "loading" } | { status: "success"; ingredient: Ingredient } | { status: "error"; message: string };

export default function IngredientDetail() {
  const { id } = useParams<{ id: string }>();
  const ready = useRequireAuth();
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reinicio de la consulta al cambiar de ingrediente
    setState({ status: "loading" });
    const ingredientId = Number(id);
    if (!Number.isSafeInteger(ingredientId) || ingredientId <= 0) {
      setState({ status: "error", message: "Identificador de ingrediente inválido." });
      return () => controller.abort();
    }
    getIngredient(ingredientId, controller.signal)
      .then(ingredient => { if (!controller.signal.aborted) setState({ status: "success", ingredient }); })
      .catch(error => { if (!controller.signal.aborted) setState({ status: "error", message: getApiErrorMessage(error) }); });
    return () => controller.abort();
  }, [id, ready]);
  if (!ready) return null;
  return (
    <main className="mx-auto max-w-3xl p-6">
      <Link href="/inventory/products" className="text-orange-700 hover:underline">Volver al inventario</Link>
      {state.status === "loading" && <p className="mt-4">Cargando ingrediente…</p>}
      {state.status === "error" && <p className="mt-4 text-red-600" role="alert">{state.message}</p>}
      {state.status === "success" && <>
        <h1 className="mt-4 text-2xl font-bold">{state.ingredient.name}</h1>
        <p className="mt-2 text-gray-600">{state.ingredient.sku} · {CATEGORY_LABELS[state.ingredient.category]} · {COUNTRY_LABELS[state.ingredient.country]}</p>
        <p className="my-6 text-xl">Stock actual: {state.ingredient.current_stock} {state.ingredient.unit}</p>
        <p className="text-gray-600">Saldo de entradas menos consumos y mermas para este ingrediente en toda la cadena.</p>
        <nav className="mt-6 flex gap-6">
          <Link className="text-orange-700 hover:underline" href={`/inventory/orders/inbound?ingredient_id=${state.ingredient.id}`}>Registrar entrada</Link>
          <Link className="text-orange-700 hover:underline" href={`/inventory/orders/outbound?ingredient_id=${state.ingredient.id}`}>Registrar salida</Link>
        </nav>
      </>}
    </main>
  );
}
