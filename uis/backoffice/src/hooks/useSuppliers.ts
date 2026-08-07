"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getApiErrorMessage, getSuppliers } from "@/lib/suppliersApi";
import type { Category, Country, Supplier } from "@/types/supplier";

type FetchStatus = "loading" | "success" | "error";

export const useSuppliers = () => {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [error, setError] = useState<string | null>(null);

  const country = (searchParams.get("country") as Country | null) ?? undefined;
  const category = (searchParams.get("category") as Category | null) ?? undefined;

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset to loading before re-fetching on filter change
    setStatus("loading");
    setError(null);

    getSuppliers({ country, category }, controller.signal)
      .then((data) => {
        setSuppliers(data);
        setStatus("success");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(getApiErrorMessage(err));
        setStatus("error");
      });

    return () => controller.abort();
  }, [country, category]);

  const replaceSupplier = (updated: Supplier) => {
    setSuppliers((prev) => prev.map((supplier) => (supplier.id === updated.id ? updated : supplier)));
  };

  const appendSupplier = (created: Supplier) => {
    setSuppliers((prev) => [...prev, created]);
  };

  return { status, suppliers, error, replaceSupplier, appendSupplier };
};
