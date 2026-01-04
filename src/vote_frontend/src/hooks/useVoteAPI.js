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
   * Upsert a single vote choice (for tournament_tiers mode).
   * Does not set loading state to avoid UI flicker on rapid clicks.
   */
  const submitVoteUpsert = useCallback(async (categoryId, fingerprint, choices) => {
    try {
      const response = await fetch(`${API_BASE}/vote/upsert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category_id: categoryId,
          fingerprint,
          choices,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to save vote');
      }
      return data;
    } catch (e) {
      throw e;
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
  const fetchResults = useCallback(async (categoryId, fingerprint = null) => {
    setLoading(true);
    setError(null);
    try {
      const query = fingerprint ? `?fingerprint=${fingerprint}` : '';
      const response = await fetch(`${API_BASE}/results/${categoryId}${query}`);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Failed to fetch results');
      return data;
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
    submitVoteUpsert,
    checkVoteStatus,
    fetchResults,
  };
}

export default useVoteAPI;
