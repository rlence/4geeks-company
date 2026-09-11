export interface WeeklyLocationPerformance {
  location_id: string;
  country: "CO" | "US";
  total_purchase_cost: number;
  total_waste_cost: number;
  waste_ratio: number;
  stockout_events_count: number;
  price_alert_events_count: number;
  currency: "COP" | "USD";
}

export interface WeeklyLocationPerformanceReport {
  week_start: string | null;
  locations: WeeklyLocationPerformance[];
}
