import React, { useState, useMemo } from 'react';
import CommentBox from '../shared/CommentBox';

function EloTournament({ items, onVote, loading }) {
  const [selected, setSelected] = useState(null);
  const [comment, setComment] = useState(null);

  // Pick two random items for the matchup
  const [itemA, itemB] = useMemo(() => {
    if (items.length < 2) return [null, null];
    const shuffled = [...items].sort(() => Math.random() - 0.5);
    return [shuffled[0], shuffled[1]];
  }, [items]);

  const handleSelect = (winnerId) => {
    setSelected(winnerId);
  };

  const handleSubmit = () => {
    if (!selected || !itemA || !itemB) return;
    // Winner first, loser second
    const loserId = selected === itemA.id ? itemB.id : itemA.id;
    onVote([selected, loserId], comment);
  };

  if (!itemA || !itemB) {
    return (
      <div className="text-center py-10 text-gray-400">
        Not enough items for a matchup.
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <p className="text-center text-gray-400 mb-8">
        Which one do you prefer? Click to select.
      </p>
      <div className="flex justify-center items-center gap-8">
        {/* Item A */}
        <div
          onClick={() => handleSelect(itemA.id)}
          className={`
            flex-1 max-w-xs p-6 rounded-2xl cursor-pointer transition-all duration-200
            ${selected === itemA.id
              ? 'bg-splat-orange ring-4 ring-yellow-400 scale-105'
              : 'bg-gray-800 hover:bg-gray-700'}
            ${loading ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          {itemA.image_url && (
            <div className="flex justify-center mb-4">
              <img
                src={itemA.image_url}
                alt={itemA.name}
                className="w-32 h-32 object-contain"
              />
            </div>
          )}
          <h3 className="text-center font-bold text-white text-xl">
            {itemA.name}
          </h3>
        </div>

        {/* VS */}
        <div className="text-4xl font-bold text-splat-purple">
          VS
        </div>

        {/* Item B */}
        <div
          onClick={() => handleSelect(itemB.id)}
          className={`
            flex-1 max-w-xs p-6 rounded-2xl cursor-pointer transition-all duration-200
            ${selected === itemB.id
              ? 'bg-splat-orange ring-4 ring-yellow-400 scale-105'
              : 'bg-gray-800 hover:bg-gray-700'}
            ${loading ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          {itemB.image_url && (
            <div className="flex justify-center mb-4">
              <img
                src={itemB.image_url}
                alt={itemB.name}
                className="w-32 h-32 object-contain"
              />
            </div>
          )}
          <h3 className="text-center font-bold text-white text-xl">
            {itemB.name}
          </h3>
        </div>
      </div>

      <div className="text-center mt-8">
        <CommentBox onSubmit={setComment} />
        <button
          onClick={handleSubmit}
          disabled={!selected || loading}
          className="mt-6 px-8 py-3 bg-splat-orange text-white text-lg font-bold rounded-xl
                     hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all transform hover:scale-105"
        >
          {loading ? 'Submitting...' : 'Confirm Choice'}
        </button>
      </div>
    </div>
  );
}

export default EloTournament;
