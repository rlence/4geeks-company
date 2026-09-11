import { LOW_STOCK_THRESHOLD } from "@/lib/inventoryLabels";

interface StockBadgeProps {
  currentStock: number;
}

export const StockBadge = ({ currentStock }: StockBadgeProps) => {
  if (currentStock <= 0) {
    return (
      <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">Sin stock</span>
    );
  }
  if (currentStock < LOW_STOCK_THRESHOLD) {
    return (
      <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
        Stock bajo
      </span>
    );
  }
  return (
    <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
      Stock saludable
    </span>
  );
};
