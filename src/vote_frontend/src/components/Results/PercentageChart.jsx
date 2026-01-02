import React from 'react';

function PercentageChart({ results, totalVotes }) {
  if (!results || results.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400">
        No votes yet. Be the first to vote!
      </div>
    );
  }

  const maxPercentage = Math.max(...results.map(r => r.percentage), 1);

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {results.map((result, index) => (
        <div key={result.item_id} className="bg-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-4 mb-2">
            <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-splat-purple rounded-full font-bold">
              {index + 1}
            </div>
            {result.image_url && (
              <img
                src={result.image_url}
                alt={result.item_name}
                className="w-10 h-10 object-contain"
              />
            )}
            <div className="flex-1">
              <h3 className="font-bold text-white">{result.item_name}</h3>
              <p className="text-gray-400 text-sm">
                {result.vote_count} vote{result.vote_count !== 1 ? 's' : ''}
                {result.average_rank && ` • Avg rank: ${result.average_rank}`}
              </p>
            </div>
            <div className="text-xl font-bold text-splat-orange">
              {result.percentage.toFixed(1)}%
            </div>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-3">
            <div
              className="bg-gradient-to-r from-splat-orange to-splat-purple h-3 rounded-full transition-all duration-500"
              style={{ width: `${(result.percentage / maxPercentage) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export default PercentageChart;
