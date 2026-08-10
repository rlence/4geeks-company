"use client";

import { useEffect, useState } from "react";
import { getApiErrorMessage, getIngredients } from "@/lib/inventoryApi";
import type { Ingredient } from "@/types/inventory";

type FetchStatus = "loading" | "success" | "error";

export const useIngredients = () => {
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    getIngredients(controller.signal)
      .then((data) => {
        setIngredients(data);
        setStatus("success");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(getApiErrorMessage(err));
        setStatus("error");
      });

    return () => controller.abort();
  }, []);

  return { status, ingredients, error };
};
