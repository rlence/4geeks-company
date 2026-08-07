import { CATEGORY_LABELS, STATUS_LABELS } from "@/lib/labels";
import type { Supplier } from "@/types/supplier";
import { RateEditor } from "./RateEditor";
import { StatusToggle } from "./StatusToggle";

interface SupplierTableProps {
  suppliers: Supplier[];
  onSupplierUpdated: (updated: Supplier) => void;
}

const StatusBadge = ({ status }: { status: Supplier["status"] }) => (
  <span
    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
      status === "active" ? "bg-green-100 text-green-800" : "bg-gray-200 text-gray-600"
    }`}
  >
    {STATUS_LABELS[status]}
  </span>
);

export const SupplierTable = ({ suppliers, onSupplierUpdated }: SupplierTableProps) => (
  <table className="w-full border-collapse text-sm">
    <thead>
      <tr className="border-b text-left">
        <th className="py-2 pr-4">Nombre</th>
        <th className="py-2 pr-4">País</th>
        <th className="py-2 pr-4">Categorías</th>
        <th className="py-2 pr-4">Tarifa</th>
        <th className="py-2 pr-4">Estado</th>
        <th className="py-2 pr-4">Acciones</th>
      </tr>
    </thead>
    <tbody>
      {suppliers.map((supplier) => (
        <tr key={supplier.id} className="border-b align-top hover:bg-gray-50">
          <td className="py-3 pr-4 font-medium">{supplier.name}</td>
          <td className="py-3 pr-4">{supplier.country}</td>
          <td className="py-3 pr-4">
            <div className="flex flex-wrap gap-1">
              {supplier.categories.map((category) => (
                <span key={category} className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-700">
                  {CATEGORY_LABELS[category]}
                </span>
              ))}
            </div>
          </td>
          <td className="py-3 pr-4">
            <RateEditor supplier={supplier} onUpdated={onSupplierUpdated} />
          </td>
          <td className="py-3 pr-4">
            <StatusBadge status={supplier.status} />
          </td>
          <td className="py-3 pr-4">
            <StatusToggle supplier={supplier} onUpdated={onSupplierUpdated} />
          </td>
        </tr>
      ))}
    </tbody>
  </table>
);
