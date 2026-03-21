import { useState, useEffect, useCallback, useRef } from 'react';
import { interpreterService } from '../services/interpreterService';
import { toast } from 'sonner';

// Module-level cache: survives React re-mounts / tab switches within the same session
let _cache = null;
let _cacheTs = 0;
const CACHE_TTL = 30_000; // 30 s — show stale, revalidate in background

export const useInterpreters = () => {
  const [interpreters, setInterpreters] = useState(_cache?.results || []);
  const [loading, setLoading]           = useState(!_cache);
  const [error, setError]               = useState(null);
  const [totalItems, setTotalItems]     = useState(_cache?.count || 0);

  const [filters, setFilters] = useState({
    page: 1,
    search: '',
    state: '',
    language: '',
    is_blocked: null,
    is_on_mission: null,
    ordering: '-user__date_joined',
  });

  const isMounted = useRef(true);
  useEffect(() => { isMounted.current = true; return () => { isMounted.current = false; }; }, []);

  const fetchInterpreters = useCallback(async (forceRefresh = false) => {
    // If we have a fresh cache and this is not a forced refresh, skip
    const cacheValid = _cache && Date.now() - _cacheTs < CACHE_TTL;
    if (cacheValid && !forceRefresh) {
      setInterpreters(_cache.results || []);
      setTotalItems(_cache.count || 0);
      setLoading(false);
      return;
    }

    // Only show spinner on first load (no stale data to show)
    if (!_cache) setLoading(true);

    try {
      setError(null);
      const response = await interpreterService.getInterpreters(filters);

      if (!isMounted.current) return;

      if (response?.results) {
        _cache  = response;
        _cacheTs = Date.now();
        setInterpreters(response.results);
        setTotalItems(response.count);
      } else if (Array.isArray(response)) {
        _cache  = { results: response, count: response.length };
        _cacheTs = Date.now();
        setInterpreters(response);
        setTotalItems(response.length);
      } else {
        setInterpreters([]);
        setTotalItems(0);
      }
    } catch (err) {
      if (!isMounted.current) return;
      console.error('Failed to fetch interpreters:', err);
      setError('Failed to load interpreters. Please try again.');
      toast.error('Failed to load interpreters data.');
      setInterpreters([]);
    } finally {
      if (isMounted.current) setLoading(false);
    }
  }, [filters]);

  useEffect(() => { fetchInterpreters(); }, [fetchInterpreters]);

  const updateFilter = (key, value) => {
    _cache = null; // Invalidate cache on filter change
    setFilters(prev => ({ ...prev, [key]: value, page: 1 }));
  };

  const setPage = (page) => setFilters(prev => ({ ...prev, page }));

  // Force a fresh fetch and update cache
  const refreshAction = () => {
    _cache = null;
    fetchInterpreters(true);
  };

  return { interpreters, totalItems, loading, error, filters, updateFilter, setPage, refreshAction };
};
