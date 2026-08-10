"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { LOCATION_OPTIONS } from "@/lib/inventoryLabels";
import { createInboundOrder, getApiErrorMessage } from "@/lib/inventoryApi";
import { useIngredients } from "@/hooks/useIngredients";

type Status = "idle" | "submitting" | "success" | "error";

const emptyState = {
  ingredient_id: "",
  supplier_name: "",
  quantity: "",
  location_id: "1",
};

export const InboundOrderForm = () => {
  const searchParams = useSearchParams();
  const { status: ingredientsStatus, ingredients, error: ingredientsError } = useIngredients();

  const [form, setForm] = useState(() => ({
    ...emptyState,
    ingredient_id: searchParams.get("ingredient_id") ?? "",
  }));
  const [clientError, setClientError] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [serverError, setServerError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setClientError(null);
    setServerError(null);

    const ingredientId = Number(form.ingredient_id);
    const quantity = Number(form.quantity);

    if (!ingredientId) {
      setClientError("Selecciona un ingrediente");
      return;
    }
    if (!form.supplier_name.trim()) {
      setClientError("El nombre del proveedor es requerido");
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setClientError("La cantidad debe ser un número mayor a 0");
      return;
    }

    setStatus("submitting");
    try {
      await createInboundOrder({
        ingredient_id: ingredientId,
        supplier_name: form.supplier_name.trim(),
        quantity,
        location_id: Number(form.location_id),
      });
      setForm(emptyState);
      setStatus("success");
    } catch (err) {
      setServerError(getApiErrorMessage(err));
      setStatus("error");
    }
  };

  if (ingredientsStatus === "loading") return <p>Cargando ingredientes…</p>;
  if (ingredientsStatus === "error") return <p className="text-red-600">{ingredientsError}</p>;

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-gray-200 bg-white p-4">
      <label className="flex flex-col gap-1 text-sm">
        Ingrediente
        <select
          value={form.ingredient_id}
          onChange={(event) => setForm((prev) => ({ ...prev, ingredient_id: event.target.value }))}
          className="rounded border px-3 py-2"
        >
          <option value="">Selecciona un ingrediente</option>
          {ingredients.map((ingredient) => (
            <option key={ingredient.id} value={ingredient.id}>
              {ingredient.name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Proveedor
        <input
          type="text"
          value={form.supplier_name}
          onChange={(event) => setForm((prev) => ({ ...prev, supplier_name: event.target.value }))}
          className="rounded border px-3 py-2"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Cantidad recibida
        <input
          type="number"
          step="0.01"
          min="0.01"
          value={form.quantity}
          onChange={(event) => setForm((prev) => ({ ...prev, quantity: event.target.value }))}
          className="rounded border px-3 py-2"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Local receptor
        <select
          value={form.location_id}
          onChange={(event) => setForm((prev) => ({ ...prev, location_id: event.target.value }))}
          className="rounded border px-3 py-2"
        >
          {LOCATION_OPTIONS.map((id) => (
            <option key={id} value={id}>
              Local {id}
            </option>
          ))}
        </select>
      </label>

      {status === "success" && <p className="text-sm text-green-700">Entrega registrada correctamente.</p>}
      {clientError && <p className="text-sm text-red-600">{clientError}</p>}
      {serverError && <p className="text-sm text-red-600">{serverError}</p>}

      <button
        type="submit"
        disabled={status === "submitting"}
        className="rounded bg-orange-700 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {status === "submitting" ? "Guardando…" : "Registrar entrada"}
      </button>
    </form>
  );
};
