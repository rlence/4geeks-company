import type { Location, MenuItem } from "../types/models.js";

export const findLocationById = (locations: Location[], id: string): Location | null =>
  locations.find((location) => location.id === id) ?? null;

export const findMenuItemByName = (items: MenuItem[], name: string): MenuItem | null => {
  const target = name.toLowerCase();
  return items.find((item) => item.name.toLowerCase() === target) ?? null;
};

export const binarySearchLocationByCapacity = (
  sortedLocations: Location[],
  targetCapacity: number
): number => {
  let low = 0;
  let high = sortedLocations.length - 1;

  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    // mid siempre está en [low, high] ⊆ [0, length - 1] mientras el bucle corre
    const midCapacity = sortedLocations[mid]!.seatingCapacity;

    if (midCapacity === targetCapacity) return mid;
    if (midCapacity < targetCapacity) low = mid + 1;
    else high = mid - 1;
  }
  return -1;
};
