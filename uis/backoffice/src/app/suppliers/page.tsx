"use client";

import dynamic from "next/dynamic";
import { Suspense, useMemo, useState } from "react";
import { SupplierFilters } from "@/components/suppliers/SupplierFilters";
import { SupplierSummary } from "@/components/suppliers/SupplierSummary";
import { SupplierTable } from "@/components/suppliers/SupplierTable";
import { useSuppliers } from "@/hooks/useSuppliers";

// SupplierForm solo se renderiza cuando el usuario hace clic en
// "+ Nuevo proveedor" — la mayoría de las visitas a esta página son
// para mirar/filtrar el directorio, no para dar de alta un proveedor.
// Diferimos su JS (validación, estado de campos, submit) fuera del
// bundle inicial de la ruta.
const SupplierForm = dynamic(
  () => import("@/components/suppliers/SupplierForm").then((mod) => mod.SupplierForm),
  {
    ssr: false,
    loading: () => (
      <button disabled className="whitespace-nowrap rounded bg-orange-700/50 px-4 py-2 text-sm text-white">
        + Nuevo proveedor
      </button>
    ),
  },
);

const SuppliersPageContent = () => {
  const { status, suppliers, error, replaceSupplier, appendSupplier } = useSuppliers();
  const [searchTerm, setSearchTerm] = useState("");

  // Este SÍ depende de searchTerm — se recalcula en cada letra tipeada
  // a propósito, es lo que hace el filtro. El array de dependencias
  // correcto es lo que distingue este caso del de SupplierSummary.
  const visibleSuppliers = useMemo(
    () => suppliers.filter((supplier) => supplier.name.toLowerCase().includes(searchTerm.toLowerCase())),
    [suppliers, searchTerm],
  );

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="mb-1 text-2xl font-bold">Directorio de Proveedores</h1>
      <p className="mb-4 text-gray-600">Compras y Proveedores · Lucía Fernández</p>

      <div className="mb-4 flex items-center justify-between gap-4">
        <SupplierFilters />
        <SupplierForm onCreated={appendSupplier} />
      </div>

      {status === "loading" && <p>Cargando proveedores…</p>}
      {status === "error" && <p className="text-red-600">{error}</p>}

      {status === "success" && (
        <>
          <SupplierSummary suppliers={suppliers} />
          <input
            type="search"
            placeholder="Buscar por nombre…"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            className="mb-4 w-full max-w-xs rounded border px-3 py-2 text-sm"
          />
          <SupplierTable suppliers={visibleSuppliers} onSupplierUpdated={replaceSupplier} />
          {visibleSuppliers.length === 0 && (
            <p className="mt-4 text-gray-500">No hay proveedores con estos filtros.</p>
          )}
        </>
      )}
    </main>
  );
};

export default function SuppliersPage() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-5xl p-6">Cargando…</main>}>
      <SuppliersPageContent />
    </Suspense>
  );
}
