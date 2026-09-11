"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { LOCATION_OPTIONS, LOW_STOCK_THRESHOLD, REASON_LABELS, REASON_OPTIONS } from "@/lib/inventoryLabels";
import { createOutboundOrder, getApiErrorMessage } from "@/lib/inventoryApi";
import { useIngredients } from "@/hooks/useIngredients";
import { track } from "@/lib/telemetry";
import type { ExitReason } from "@/types/inventory";

type Status = "idle" | "submitting" | "success" | "error";

const emptyState = {
  ingredient_id: "",
  quantity: "",
  reason: "consumption" as ExitReason,
  unit_cost: "",
  location_id: "1",
};

export const OutboundOrderForm = () => {
  const searchParams = useSearchParams();
  const { status: ingredientsStatus, ingredients, error: ingredientsError } = useIngredients();

  const [form, setForm] = useState(() => ({
    ...emptyState,
    ingredient_id: searchParams.get("ingredient_id") ?? "",
  }));
  const [clientError, setClientError] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [quantityServerError, setQuantityServerError] = useState<string | null>(null);

  const selectedIngredient = useMemo(
    () => ingredients.find((ingredient) => ingredient.id === Number(form.ingredient_id)) ?? null,
    [ingredients, form.ingredient_id],
  );

  const quantityExceedsStock =
    selectedIngredient !== null && Number(form.quantity) > 0 && Number(form.quantity) > selectedIngredient.current_stock;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setClientError(null);
    setQuantityServerError(null);

    const ingredientId = Number(form.ingredient_id);
    const quantity = Number(form.quantity);
    const unitCost = Number(form.unit_cost);

    if (!ingredientId) {
      setClientError("Selecciona un ingrediente");
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setClientError("La cantidad debe ser un número mayor a 0");
      return;
    }
    if (form.reason === "waste" && (!Number.isFinite(unitCost) || unitCost <= 0)) {
      setClientError("El costo unitario es requerido para registrar merma");
      return;
    }
    if (quantityExceedsStock) {
      track("inventory_order_validation_failed", {
        location_id: Number(form.location_id),
        product_id: ingredientId,
        order_type: "outbound",
        reason: "quantity_exceeds_stock",
      });
      setClientError("La cantidad supera el stock disponible — corrígela antes de enviar");
      return;
    }

    setStatus("submitting");
    try {
      await createOutboundOrder({
        ingredient_id: ingredientId,
        quantity,
        reason: form.reason,
        location_id: Number(form.location_id),
      });

      const locationId = Number(form.location_id);
      const country = selectedIngredient?.country ?? null;
      const productCategory = selectedIngredient?.category ?? null;
      const unit = selectedIngredient?.unit ?? null;

      track("outbound_order_created", {
        location_id: locationId,
        country,
        product_id: ingredientId,
        product_category: productCategory,
        quantity,
        unit,
        reason: form.reason,
      });

      if (form.reason === "waste") {
        track("stock_waste_registered", {
          location_id: locationId,
          country,
          product_id: ingredientId,
          product_category: productCategory,
          quantity,
          unit,
          unit_cost: unitCost,
        });
      }

      if (selectedIngredient) {
        const newStock = selectedIngredient.current_stock - quantity;
        if (newStock < LOW_STOCK_THRESHOLD) {
          track("stock_threshold_triggered", {
            location_id: locationId,
            country,
            product_id: ingredientId,
            product_category: productCategory,
            current_stock: newStock,
            threshold: LOW_STOCK_THRESHOLD,
            unit,
          });
        }
      }

      setForm(emptyState);
      setStatus("success");
    } catch (err) {
      setQuantityServerError(getApiErrorMessage(err));
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

      {selectedIngredient && (
        <p className="text-sm text-gray-600">
          Stock disponible: <strong>{selectedIngredient.current_stock}</strong> {selectedIngredient.unit}
        </p>
      )}

      <label className="flex flex-col gap-1 text-sm">
        Cantidad
        <input
          type="number"
          step="0.01"
          min="0.01"
          value={form.quantity}
          onChange={(event) => setForm((prev) => ({ ...prev, quantity: event.target.value }))}
          className="rounded border px-3 py-2"
        />
        {quantityExceedsStock && (
          <span className="text-sm text-amber-700">
            La cantidad introducida supera el stock disponible ({selectedIngredient?.current_stock}{" "}
            {selectedIngredient?.unit}).
          </span>
        )}
        {quantityServerError && <span className="text-sm text-red-600">{quantityServerError}</span>}
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Motivo
        <select
          value={form.reason}
          onChange={(event) => setForm((prev) => ({ ...prev, reason: event.target.value as ExitReason }))}
          className="rounded border px-3 py-2"
        >
          {REASON_OPTIONS.map((reason) => (
            <option key={reason} value={reason}>
              {REASON_LABELS[reason]}
            </option>
          ))}
        </select>
      </label>

      {form.reason === "waste" && (
        <label className="flex flex-col gap-1 text-sm">
          Costo unitario de la merma
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={form.unit_cost}
            onChange={(event) => setForm((prev) => ({ ...prev, unit_cost: event.target.value }))}
            className="rounded border px-3 py-2"
          />
        </label>
      )}

      <label className="flex flex-col gap-1 text-sm">
        Local
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

      {status === "success" && <p className="text-sm text-green-700">Salida registrada correctamente.</p>}
      {clientError && <p className="text-sm text-red-600">{clientError}</p>}

      <button
        type="submit"
        disabled={status === "submitting"}
        className="rounded bg-orange-700 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {status === "submitting" ? "Guardando…" : "Registrar salida"}
      </button>
    </form>
  );
};
