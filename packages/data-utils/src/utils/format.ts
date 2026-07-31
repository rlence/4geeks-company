export const USD_TO_COP_RATE = 4000;

export const round2 = (value: number): number => Math.round(value * 100) / 100;

export const startOfDay = (date: Date): Date => {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
};

export const endOfDay = (date: Date): Date => {
  const d = new Date(date);
  d.setHours(23, 59, 59, 999);
  return d;
};

export const isSameDay = (a: Date, b: Date): boolean =>
  a.getFullYear() === b.getFullYear() &&
  a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate();

export const daysSinceOpening = (openingYear: number): number => {
  const openedAt = new Date(openingYear, 0, 1);
  const msPerDay = 1000 * 60 * 60 * 24;
  const days = Math.floor((Date.now() - openedAt.getTime()) / msPerDay);
  return Math.max(1, days);
};
