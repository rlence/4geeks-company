"use client";

import { useCallback, useEffect, useState } from "react";
import { getApiErrorMessage, getIngredients } from "@/lib/inventoryApi";
import type { Ingredient } from "@/types/inventory";

type FetchStatus = "loading" | "success" | "error";

export const useIngredients = () => {
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => {
    setStatus("loading");
    setError(null);
    setRevision(value => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    getIngredients(controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        setIngredients(data);
        setStatus("success");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(getApiErrorMessage(err));
        setStatus("error");
      });

    return () => controller.abort();
  }, [revision]);

  return { status, ingredients, error, reload };
};
