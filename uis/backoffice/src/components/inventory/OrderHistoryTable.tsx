import { REASON_LABELS } from "@/lib/inventoryLabels";
import type { InventoryOrder } from "@/types/inventory";

interface OrderHistoryTableProps {
  orders: InventoryOrder[];
}

const TypeBadge = ({ type }: { type: InventoryOrder["type"] }) =>
  type === "inbound" ? (
    <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">Entrada</span>
  ) : (
    <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800">Salida</span>
  );

export const OrderHistoryTable = ({ orders }: OrderHistoryTableProps) => (
  <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
    <table className="w-full text-left text-sm">
      <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
        <tr>
          <th className="px-4 py-3">Tipo</th>
          <th className="px-4 py-3">Ingrediente</th>
          <th className="px-4 py-3">Cantidad</th>
          <th className="px-4 py-3">Detalle</th>
          <th className="px-4 py-3">Fecha</th>
          <th className="px-4 py-3">Registrado por</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {orders.map((order) => (
          <tr key={`${order.type}-${order.id}`}>
            <td className="px-4 py-3">
              <TypeBadge type={order.type} />
            </td>
            <td className="px-4 py-3 font-medium">{order.ingredient_name}</td>
            <td className="px-4 py-3">
              {order.quantity} {order.unit}
            </td>
            <td className="px-4 py-3 text-gray-600">
              {order.type === "inbound" ? order.supplier_name : order.reason && REASON_LABELS[order.reason]}
            </td>
            <td className="px-4 py-3 text-gray-500">{new Date(order.created_at).toLocaleString()}</td>
            <td className="px-4 py-3 text-gray-500">{order.user_uuid}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
