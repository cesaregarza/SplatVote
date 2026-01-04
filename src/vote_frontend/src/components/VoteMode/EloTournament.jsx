import React, { useState, useCallback } from 'react';
import CommentBox from '../shared/CommentBox';

function EloTournament({ items, onVote, loading }) {
  const [selected, setSelected] = useState(null);
  const [comment, setComment] = useState(null);

  // Items are already shuffled by VoteContainer, just take the first two
  const itemA = items.length >= 2 ? items[0] : null;
  const itemB = items.length >= 2 ? items[1] : null;

  const handleSelect = useCallback((winnerId) => {
    if (loading) return;
    setSelected(winnerId);
  }, [loading]);

  const handleKeyDown = useCallback((winnerId) => (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleSelect(winnerId);
    }
  }, [handleSelect]);

  const handleSubmit = () => {
    if (!selected || !itemA || !itemB) return;
    // Winner first, loser second
    const loserId = selected === itemA.id ? itemB.id : itemA.id;
    onVote([selected, loserId], comment);
  };

  if (!itemA || !itemB) {
    return (
      <div className="text-center py-10 text-slate-400">
        Not enough items for a matchup.
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <p className="text-center text-slate-300 mb-8">
        Which one do you prefer? Click to select.
      </p>
      <div className="flex justify-center items-center gap-8">
        {/* Item A */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => handleSelect(itemA.id)}
          onKeyDown={handleKeyDown(itemA.id)}
          aria-pressed={selected === itemA.id}
          aria-label={`Select ${itemA.name}`}
          className={`
            flex-1 max-w-xs p-6 rounded-2xl cursor-pointer transition-all duration-200 border border-white/5
            ${selected === itemA.id
              ? 'bg-slate-900/80 ring-2 ring-fuchsia-400/50 shadow-[0_0_22px_rgba(217,70,239,0.25)]'
              : 'bg-slate-900/50 hover:bg-slate-900/70'}
            ${loading ? 'opacity-50 cursor-not-allowed' : ''}
            focus:outline-none focus:ring-2 focus:ring-fuchsia-400/50
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
          <h3 className="text-center font-semibold text-white text-xl">
            {itemA.name}
          </h3>
        </div>

        {/* VS */}
        <div className="text-4xl font-semibold text-fuchsia-300">
          VS
        </div>

        {/* Item B */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => handleSelect(itemB.id)}
          onKeyDown={handleKeyDown(itemB.id)}
          aria-pressed={selected === itemB.id}
          aria-label={`Select ${itemB.name}`}
          className={`
            flex-1 max-w-xs p-6 rounded-2xl cursor-pointer transition-all duration-200 border border-white/5
            ${selected === itemB.id
              ? 'bg-slate-900/80 ring-2 ring-fuchsia-400/50 shadow-[0_0_22px_rgba(217,70,239,0.25)]'
              : 'bg-slate-900/50 hover:bg-slate-900/70'}
            ${loading ? 'opacity-50 cursor-not-allowed' : ''}
            focus:outline-none focus:ring-2 focus:ring-fuchsia-400/50
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
          <h3 className="text-center font-semibold text-white text-xl">
            {itemB.name}
          </h3>
        </div>
      </div>

      <div className="text-center mt-8">
        <CommentBox onSubmit={setComment} />
        <button
          onClick={handleSubmit}
          disabled={!selected || loading}
          className="mt-6 px-8 py-3 bg-fuchsia-600 text-white text-lg font-semibold rounded-full
                     hover:bg-fuchsia-500 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all"
        >
          {loading ? 'Submitting...' : 'Confirm Choice'}
        </button>
      </div>
    </div>
  );
}

export default EloTournament;
