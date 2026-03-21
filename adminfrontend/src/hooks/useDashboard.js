/**
 * useDashboard — fetches all dashboard data in parallel on mount.
 * Returns { data: { kpis, alerts, chart, missions }, isLoading, error, refetch }
 */
import { useState, useEffect, useCallback } from "react";
import { dashboardService } from "@/services/dashboardService";

export function useDashboard() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(() => {
    setIsLoading(true);
    setError(null);

    Promise.all([
      dashboardService.getKPIs(),
      dashboardService.getAlerts(),
      dashboardService.getRevenueChart(),
      dashboardService.getTodayMissions(),
    ])
      .then(([kpisRes, alertsRes, chartRes, missionsRes]) => {
        setData({
          kpis: kpisRes.data,
          alerts: alertsRes.data,
          chart: chartRes.data,      // [{ month, revenue, expenses }]
          missions: missionsRes.data, // [{ id, status, start_time, interpreter, client, ... }]
        });
      })
      .catch((err) => {
        console.error("[useDashboard] Failed to fetch dashboard data:", err);
        setError(err);
      })
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, isLoading, error, refetch: fetch };
}

export default useDashboard;
