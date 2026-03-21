/**
 * useDashboard — fetches all dashboard data in parallel.
 * Stale-while-revalidate: serves the previous response instantly on revisit,
 * then fetches fresh data in the background.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { dashboardService } from "@/services/dashboardService";

// Module-level cache — survives component unmount / tab switch
let _cache = null;
let _cacheTs = 0;
const CACHE_TTL = 60_000; // 60 s

export function useDashboard() {
  const [data, setData]           = useState(_cache || null);
  const [isLoading, setIsLoading] = useState(!_cache);
  const [error, setError]         = useState(null);

  const isMounted = useRef(true);
  useEffect(() => { isMounted.current = true; return () => { isMounted.current = false; }; }, []);

  const fetch = useCallback(async (forceRefresh = false) => {
    const cacheValid = _cache && Date.now() - _cacheTs < CACHE_TTL;
    if (cacheValid && !forceRefresh) {
      setData(_cache);
      setIsLoading(false);
      return;
    }

    // Only show full-page spinner if there is no stale data
    if (!_cache) setIsLoading(true);

    try {
      setError(null);
      const [kpisRes, alertsRes, chartRes, missionsRes] = await Promise.all([
        dashboardService.getKPIs(),
        dashboardService.getAlerts(),
        dashboardService.getRevenueChart(),
        dashboardService.getTodayMissions(),
      ]);

      if (!isMounted.current) return;

      const fresh = {
        kpis:     kpisRes.data,
        alerts:   alertsRes.data,
        chart:    chartRes.data,
        missions: missionsRes.data,
      };

      _cache  = fresh;
      _cacheTs = Date.now();
      setData(fresh);
    } catch (err) {
      if (!isMounted.current) return;
      console.error("[useDashboard] Failed to fetch dashboard data:", err);
      setError(err);
    } finally {
      if (isMounted.current) setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const refetch = () => {
    _cache = null;
    fetch(true);
  };

  return { data, isLoading, error, refetch };
}

export default useDashboard;
