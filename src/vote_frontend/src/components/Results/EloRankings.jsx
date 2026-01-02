import React from 'react';

function EloRankings({ results }) {
  if (!results || results.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400">
        No matches played yet. Be the first to vote!
      </div>
    );
  }

  // Sort by ELO rating
  const sorted = [...results].sort((a, b) => (b.elo_rating || 0) - (a.elo_rating || 0));
  const maxElo = Math.max(...sorted.map(r => r.elo_rating || 1500));
  const minElo = Math.min(...sorted.map(r => r.elo_rating || 1500));
  const eloRange = maxElo - minElo || 1;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-gray-800 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="py-3 px-4 text-left">Rank</th>
              <th className="py-3 px-4 text-left">Item</th>
              <th className="py-3 px-4 text-center">ELO</th>
              <th className="py-3 px-4 text-center">Games</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((result, index) => {
              const eloNormalized = ((result.elo_rating || 1500) - minElo) / eloRange;
              const isTop3 = index < 3;

              return (
                <tr
                  key={result.item_id}
                  className={`border-t border-gray-700 ${isTop3 ? 'bg-gray-750' : ''}`}
                >
                  <td className="py-3 px-4">
                    <div className={`
                      w-8 h-8 flex items-center justify-center rounded-full font-bold
                      ${index === 0 ? 'bg-yellow-500 text-black' : ''}
                      ${index === 1 ? 'bg-gray-400 text-black' : ''}
                      ${index === 2 ? 'bg-orange-600 text-white' : ''}
                      ${index > 2 ? 'bg-gray-600' : ''}
                    `}>
                      {index + 1}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      {result.image_url && (
                        <img
                          src={result.image_url}
                          alt={result.item_name}
                          className="w-10 h-10 object-contain"
                        />
                      )}
                      <span className="font-medium text-white">{result.item_name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <span className="font-bold text-splat-orange text-lg">
                        {Math.round(result.elo_rating || 1500)}
                      </span>
                      <div className="w-16 bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-splat-purple h-2 rounded-full"
                          style={{ width: `${eloNormalized * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-center text-gray-400">
                    {result.games_played || 0}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default EloRankings;
