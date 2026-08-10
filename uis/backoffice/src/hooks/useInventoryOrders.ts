"use client";

import { useEffect, useState } from "react";
import { getApiErrorMessage, getOrders } from "@/lib/inventoryApi";
import type { InventoryOrder } from "@/types/inventory";

type FetchStatus = "loading" | "success" | "error";

export const useInventoryOrders = () => {
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [orders, setOrders] = useState<InventoryOrder[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    getOrders(controller.signal)
      .then((data) => {
        setOrders(data);
        setStatus("success");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(getApiErrorMessage(err));
        setStatus("error");
      });

    return () => controller.abort();
  }, []);

  return { status, orders, error };
};
