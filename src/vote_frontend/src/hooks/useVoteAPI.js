import { useState, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || '/api/v1';

/**
 * Custom hook for interacting with the Vote API.
 */
export function useVoteAPI() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Fetch all categories.
   */
  const fetchCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/categories`);
      if (!response.ok) throw new Error('Failed to fetch categories');
      const data = await response.json();
      return data.categories;
    } catch (e) {
      setError(e.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Fetch a single category with items.
   */
  const fetchCategory = useCallback(async (categoryId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/categories/${categoryId}`);
      if (!response.ok) throw new Error('Category not found');
      return await response.json();
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Submit a vote.
   */
  const submitVote = useCallback(async (categoryId, fingerprint, choices, comment = null) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category_id: categoryId,
          fingerprint,
          choices,
          comment,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to submit vote');
      }
      return data;
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Check vote status for a category.
   */
  const checkVoteStatus = useCallback(async (categoryId, fingerprint) => {
    try {
      const response = await fetch(
        `${API_BASE}/vote/status/${categoryId}?fingerprint=${fingerprint}`
      );
      if (!response.ok) return { has_voted: false };
      return await response.json();
    } catch {
      return { has_voted: false };
    }
  }, []);

  /**
   * Fetch results for a category.
   */
  const fetchResults = useCallback(async (categoryId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/results/${categoryId}`);
      if (!response.ok) throw new Error('Failed to fetch results');
      return await response.json();
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    fetchCategories,
    fetchCategory,
    submitVote,
    checkVoteStatus,
    fetchResults,
  };
}

export default useVoteAPI;
