import { useState, useEffect, useCallback } from 'react';
import { interpreterService } from '../services/interpreterService';
import { toast } from 'sonner';

export const useInterpreters = () => {
  const [interpreters, setInterpreters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [totalItems, setTotalItems] = useState(0);

  // Pagination & Filters State
  const [filters, setFilters] = useState({
    page: 1,
    search: '',
    state: '',
    language: '',
    is_blocked: null, // null means all, true means blocked, false means active
    is_on_mission: null, // Future filter constraint implementation
    ordering: '-user__date_joined'
  });

  const fetchInterpreters = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await interpreterService.getInterpreters(filters);
      
      // Standard DRF Pagination format: { count, next, previous, results }
      if (response && response.results) {
        setInterpreters(response.results);
        setTotalItems(response.count);
      } else if (Array.isArray(response)) {
          // Fallback if not paginated
          setInterpreters(response);
          setTotalItems(response.length);
      } else {
          setInterpreters([]);
          setTotalItems(0);
      }

    } catch (err) {
      console.error('Failed to fetch interpreters:', err);
      setError('Failed to load interpreters. Please try again.');
      toast.error('Failed to load interpreters data.');
      setInterpreters([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchInterpreters();
  }, [fetchInterpreters]);

  // Expose methods to change filters easily
  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value, page: 1 })); // Reset page on filter change
  };

  const setPage = (page) => {
    setFilters(prev => ({ ...prev, page }));
  };

  const refreshAction = () => {
    fetchInterpreters();
  };

  return {
    interpreters,
    totalItems,
    loading,
    error,
    filters,
    updateFilter,
    setPage,
    refreshAction
  };
};
