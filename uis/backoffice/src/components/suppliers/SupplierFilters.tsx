"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CATEGORY_LABELS, COUNTRY_LABELS } from "@/lib/labels";

export const SupplierFilters = () => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const updateParam = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(key, value);
    else params.delete(key);
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <div className="flex flex-wrap gap-3">
      <select
        value={searchParams.get("country") ?? ""}
        onChange={(event) => updateParam("country", event.target.value)}
        className="rounded border px-3 py-2"
      >
        <option value="">Todos los países</option>
        {Object.entries(COUNTRY_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <select
        value={searchParams.get("category") ?? ""}
        onChange={(event) => updateParam("category", event.target.value)}
        className="rounded border px-3 py-2"
      >
        <option value="">Todas las categorías</option>
        {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
    </div>
  );
};
