interface StockBadgeProps {
  currentStock: number;
}

// Umbral arbitrario para la demo (no viene del backend): <=0 sin stock,
// <20 stock bajo independientemente de la unidad (kg/litro/unidad), por
// simplicidad — no hay campo de stock mínimo en el spec de Ingredient.
const LOW_STOCK_THRESHOLD = 20;

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
