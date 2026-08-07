"use client";

import { Suspense } from "react";
import { SupplierFilters } from "@/components/suppliers/SupplierFilters";
import { SupplierForm } from "@/components/suppliers/SupplierForm";
import { SupplierTable } from "@/components/suppliers/SupplierTable";
import { useSuppliers } from "@/hooks/useSuppliers";

const SuppliersPageContent = () => {
  const { status, suppliers, error, replaceSupplier, appendSupplier } = useSuppliers();

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
          <SupplierTable suppliers={suppliers} onSupplierUpdated={replaceSupplier} />
          {suppliers.length === 0 && <p className="mt-4 text-gray-500">No hay proveedores con estos filtros.</p>}
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
