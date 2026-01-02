import React from 'react';
import { Link } from 'react-router-dom';

const MODE_LABELS = {
  single_choice: 'Single Choice',
  elo_tournament: 'Head-to-Head',
  ranked_list: 'Ranked List',
};

const MODE_ICONS = {
  single_choice: '🎯',
  elo_tournament: '⚔️',
  ranked_list: '📊',
};

function CategoryCard({ category }) {
  return (
    <div className="bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition-shadow">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-2xl">{MODE_ICONS[category.comparison_mode]}</span>
          <span className="text-xs bg-splat-purple px-2 py-1 rounded-full">
            {MODE_LABELS[category.comparison_mode]}
          </span>
        </div>
        <h2 className="text-xl font-bold text-white mb-2">
          {category.name}
        </h2>
        {category.description && (
          <p className="text-gray-400 text-sm mb-4 line-clamp-2">
            {category.description}
          </p>
        )}
        <div className="flex gap-3">
          <Link
            to={`/vote/${category.id}`}
            className="flex-1 text-center py-2 bg-splat-orange text-white rounded-lg
                       hover:bg-orange-600 transition-colors font-medium"
          >
            Vote
          </Link>
          <Link
            to={`/results/${category.id}`}
            className="flex-1 text-center py-2 bg-gray-700 text-white rounded-lg
                       hover:bg-gray-600 transition-colors font-medium"
          >
            Results
          </Link>
        </div>
      </div>
    </div>
  );
}

export default CategoryCard;
