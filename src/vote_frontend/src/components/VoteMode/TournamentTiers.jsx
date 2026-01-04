import React, { useState } from 'react';

function TournamentCard({ item, tierOptions, selectedTier, onSelect, saving }) {
  const metadata = item.metadata || {};
  const displayName = metadata.display_name || item.name;
  const url = metadata.url;
  const winners = metadata.winners || [];

  return (
    <div className="rounded-2xl border border-white/5 bg-slate-900/60 p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-white text-lg truncate">{displayName}</h3>
            {saving && (
              <span className="text-xs text-fuchsia-400 animate-pulse">Saving...</span>
            )}
          </div>
          {url && (url.startsWith('https://') || url.startsWith('http://')) && (
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-slate-400 hover:text-fuchsia-300 mt-1 inline-block"
            >
              View results →
            </a>
          )}
          {winners.length > 0 && (
            <div className="mt-3 space-y-2">
              {winners.slice(0, 2).map((w, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className={`
                    flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
                    ${i === 0 ? 'bg-yellow-500/20 text-yellow-300' : 'bg-slate-700 text-slate-300'}
                  `}>
                    {w.placement}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{w.team?.name || 'Unknown'}</p>
                    {w.team?.players && (
                      <p className="text-xs text-slate-500 truncate">
                        {w.team.players.slice(0, 4).join(', ')}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {tierOptions.map((tier, index) => (
          <button
            key={tier}
            onClick={() => onSelect(item.id, index)}
            className={`
              px-3 py-1.5 rounded-lg text-sm font-semibold transition-all cursor-pointer
              ${selectedTier === index
                ? 'bg-fuchsia-600 text-white ring-2 ring-fuchsia-400/50'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}
            `}
          >
            {tier}
          </button>
        ))}
      </div>
    </div>
  );
}

function TournamentTiers({ category, items, onVote, loading }) {
  const [selections, setSelections] = useState({});
  const [savingItems, setSavingItems] = useState({});
  const [currentPage, setCurrentPage] = useState(0);

  const tierOptions = category.settings?.tier_options || ['X', 'S+', 'S', 'A', 'B', 'C', 'D'];
  const totalPages = category.settings?.pages || 3;
  const itemsPerPage = Math.ceil(items.length / totalPages);

  // Items are already shuffled by VoteContainer, just paginate
  const paginatedItems = [];
  for (let i = 0; i < totalPages; i += 1) {
    const start = i * itemsPerPage;
    const end = start + itemsPerPage;
    paginatedItems.push(items.slice(start, end));
  }

  const currentItems = paginatedItems[currentPage] || [];
  const votedCount = Object.keys(selections).length;

  const handleSelect = async (itemId, tierIndex) => {
    // Update local state immediately
    setSelections(prev => ({ ...prev, [itemId]: tierIndex }));
    setSavingItems(prev => ({ ...prev, [itemId]: true }));

    // Auto-submit this single vote
    try {
      await onVote([itemId, tierIndex], null);
    } catch (err) {
      console.error('Failed to save vote:', err);
    } finally {
      setSavingItems(prev => ({ ...prev, [itemId]: false }));
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages - 1) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handlePrev = () => {
    if (currentPage > 0) {
      setCurrentPage(currentPage - 1);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <div className="text-slate-400 text-sm">
          Page {currentPage + 1} of {totalPages}
        </div>
        <div className="text-slate-400 text-sm">
          {votedCount} / {items.length} rated
        </div>
      </div>

      <div className="space-y-4">
        {currentItems.map(item => (
          <TournamentCard
            key={item.id}
            item={item}
            tierOptions={tierOptions}
            selectedTier={selections[item.id]}
            onSelect={handleSelect}
            saving={savingItems[item.id]}
          />
        ))}
      </div>

      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={handlePrev}
          disabled={currentPage === 0}
          className="px-6 py-2 rounded-full bg-slate-800 text-white font-semibold
                     hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          Previous
        </button>

        <div className="flex gap-2">
          {Array.from({ length: totalPages }).map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentPage(i)}
              className={`w-3 h-3 rounded-full transition-all ${
                i === currentPage ? 'bg-fuchsia-500' : 'bg-slate-600 hover:bg-slate-500'
              }`}
            />
          ))}
        </div>

        <button
          onClick={handleNext}
          disabled={currentPage >= totalPages - 1}
          className="px-6 py-2 rounded-full bg-fuchsia-600 text-white font-semibold
                     hover:bg-fuchsia-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {currentPage >= totalPages - 1 ? 'Done!' : 'Next'}
        </button>
      </div>

      <p className="mt-4 text-center text-sm text-slate-500">
        Click a tier to save your vote instantly
      </p>
    </div>
  );
}

export default TournamentTiers;
