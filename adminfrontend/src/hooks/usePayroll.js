/**
 * usePayroll — fetches KPIs, stubs, and payments in parallel.
 * Stale-while-revalidate: module-level cache survives component unmount / tab switch.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { payrollService } from '../services/payrollService';

let _cache = null;
let _cacheTs = 0;
const CACHE_TTL = 30_000; // 30 s

export function usePayroll() {
  const [data, setData]           = useState(_cache || null);
  const [isLoading, setIsLoading] = useState(!_cache);
  const [error, setError]         = useState(null);

  const isMounted = useRef(true);
  useEffect(() => { isMounted.current = true; return () => { isMounted.current = false; }; }, []);

  const fetchAll = useCallback(async (forceRefresh = false) => {
    const cacheValid = _cache && Date.now() - _cacheTs < CACHE_TTL;
    if (cacheValid && !forceRefresh) {
      setData(_cache);
      setIsLoading(false);
      return;
    }

    if (!_cache) setIsLoading(true);

    try {
      setError(null);
      const [kpisRes, stubsRes, paymentsRes] = await Promise.all([
        payrollService.getKPIs(),
        payrollService.getStubs({ page_size: 50 }),
        payrollService.getPayments({ page_size: 50 }),
      ]);

      if (!isMounted.current) return;

      const fresh = {
        kpis:     kpisRes.data,
        stubs:    stubsRes.data,
        payments: paymentsRes.data,
      };

      _cache   = fresh;
      _cacheTs = Date.now();
      setData(fresh);
    } catch (err) {
      if (!isMounted.current) return;
      console.error('[usePayroll] Failed to fetch payroll data:', err);
      setError(err);
    } finally {
      if (isMounted.current) setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const refresh = () => {
    _cache = null;
    fetchAll(true);
  };

  return { data, isLoading, error, refresh };
}

export default usePayroll;
