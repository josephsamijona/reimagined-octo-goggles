/**
 * useAssignments — paginated assignment list with server-side filters,
 * module-level cache (30s TTL, stale-while-revalidate), and stats.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { dispatchService } from '@/services/dispatchService';

// Module-level cache shared across mount/unmount cycles
let _listCache = null;
let _listCacheTs = 0;
let _statsCache = null;
let _statsCacheTs = 0;
const CACHE_TTL = 30_000; // 30s

const DEFAULT_PARAMS = {
  page: 1,
  page_size: 15,
  status: '',
  search: '',
  service_type: '',
  date_from: '',
  date_to: '',
  ordering: '-start_time',
  unassigned: '',
};

export function useAssignments() {
  const [params, setParamsState] = useState(DEFAULT_PARAMS);
  const [assignments, setAssignments] = useState([]);
  const [count, setCount] = useState(0);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const fetchList = useCallback(async (p, bust = false) => {
    const cacheKey = JSON.stringify(p);
    const now = Date.now();

    // Return cache if fresh and same params
    if (!bust && _listCache?.key === cacheKey && now - _listCacheTs < CACHE_TTL) {
      setAssignments(_listCache.assignments);
      setCount(_listCache.count);
      return;
    }

    // Cancel previous in-flight request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setIsLoading(true);
    setError(null);

    try {
      // Build clean params (omit empty strings)
      const clean = Object.fromEntries(
        Object.entries(p).filter(([, v]) => v !== '' && v !== null && v !== undefined)
      );
      const res = await dispatchService.getAssignments(clean);
      const body = res.data || {};
      const results = body.results || [];
      const total = body.count || 0;

      _listCache = { key: cacheKey, assignments: results, count: total };
      _listCacheTs = Date.now();

      setAssignments(results);
      setCount(total);
    } catch (err) {
      if (err?.code !== 'ERR_CANCELED') {
        setError(err);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchStats = useCallback(async (bust = false) => {
    const now = Date.now();
    if (!bust && _statsCache && now - _statsCacheTs < CACHE_TTL) {
      setStats(_statsCache);
      return;
    }
    setStatsLoading(true);
    try {
      const res = await dispatchService.getStats();
      _statsCache = res.data;
      _statsCacheTs = Date.now();
      setStats(res.data);
    } catch {
      // stats failure is non-fatal
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchList(params);
  }, [params, fetchList]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const setParams = useCallback((updates) => {
    setParamsState(prev => {
      const next = { ...prev, ...updates };
      // Reset to page 1 when filters change (not when only page changes)
      const filterChanged = Object.keys(updates).some(k => k !== 'page');
      return filterChanged ? { ...next, page: 1 } : next;
    });
  }, []);

  const refresh = useCallback(() => {
    _listCache = null;
    _statsCache = null;
    fetchList(params, true);
    fetchStats(true);
  }, [params, fetchList, fetchStats]);

  return {
    assignments,
    count,
    stats,
    isLoading,
    statsLoading,
    error,
    params,
    setParams,
    refresh,
  };
}

export default useAssignments;
