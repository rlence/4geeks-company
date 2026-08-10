import Link from "next/link";
import { StockBadge } from "@/components/inventory/StockBadge";
import { CATEGORY_LABELS, COUNTRY_LABELS } from "@/lib/inventoryLabels";
import type { Ingredient } from "@/types/inventory";

interface ProductTableProps {
  ingredients: Ingredient[];
}

export const ProductTable = ({ ingredients }: ProductTableProps) => (
  <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
    <table className="w-full text-left text-sm">
      <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
        <tr>
          <th className="px-4 py-3">Ingrediente</th>
          <th className="px-4 py-3">SKU</th>
          <th className="px-4 py-3">Categoría</th>
          <th className="px-4 py-3">País</th>
          <th className="px-4 py-3">Stock actual</th>
          <th className="px-4 py-3">Nivel</th>
          <th className="px-4 py-3">Acciones</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {ingredients.map((ingredient) => (
          <tr key={ingredient.id}>
            <td className="px-4 py-3 font-medium">{ingredient.name}</td>
            <td className="px-4 py-3 text-gray-500">{ingredient.sku}</td>
            <td className="px-4 py-3">{CATEGORY_LABELS[ingredient.category]}</td>
            <td className="px-4 py-3">{COUNTRY_LABELS[ingredient.country]}</td>
            <td className="px-4 py-3">
              {ingredient.current_stock} {ingredient.unit}
            </td>
            <td className="px-4 py-3">
              <StockBadge currentStock={ingredient.current_stock} />
            </td>
            <td className="px-4 py-3">
              <div className="flex gap-3">
                <Link
                  href={`/inventory/orders/inbound?ingredient_id=${ingredient.id}`}
                  className="text-orange-700 hover:underline"
                >
                  Registrar entrada
                </Link>
                <Link
                  href={`/inventory/orders/outbound?ingredient_id=${ingredient.id}`}
                  className="text-orange-700 hover:underline"
                >
                  Registrar salida
                </Link>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
