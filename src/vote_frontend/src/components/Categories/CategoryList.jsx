import React, { useEffect, useState } from 'react';
import { useVoteAPI } from '../../hooks/useVoteAPI';
import CategoryCard from './CategoryCard';

function CategoryList() {
  const [categories, setCategories] = useState([]);
  const { fetchCategories, loading, error } = useVoteAPI();

  useEffect(() => {
    fetchCategories().then(setCategories);
  }, [fetchCategories]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-fuchsia-400"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-rose-300 text-lg">{error}</p>
        <button
          onClick={() => fetchCategories().then(setCategories)}
          className="mt-4 rounded-full bg-fuchsia-600 px-6 py-2 text-white hover:bg-fuchsia-500"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-10 rounded-2xl border border-white/5 bg-slate-900/60 px-6 py-8 shadow-[0_24px_60px_rgba(2,6,23,0.45)]">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          Community polls
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">
          Vote on your favorites
        </h1>
        <p className="mt-2 max-w-2xl text-slate-300">
          Pick a category, cast your vote, and watch the rankings update as the
          community weighs in.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {categories.map(category => (
          <CategoryCard key={category.id} category={category} />
        ))}
      </div>
      {categories.length === 0 && (
        <p className="text-center text-slate-400 py-10">
          No categories available yet.
        </p>
      )}
    </div>
  );
}

export default CategoryList;
