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
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-splat-orange"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-500 text-lg">{error}</p>
        <button
          onClick={() => fetchCategories().then(setCategories)}
          className="mt-4 px-6 py-2 bg-splat-orange text-white rounded-lg hover:bg-orange-600"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-8 text-center">
        Vote on Your Favorites
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {categories.map(category => (
          <CategoryCard key={category.id} category={category} />
        ))}
      </div>
      {categories.length === 0 && (
        <p className="text-center text-gray-400 py-10">
          No categories available yet.
        </p>
      )}
    </div>
  );
}

export default CategoryList;
