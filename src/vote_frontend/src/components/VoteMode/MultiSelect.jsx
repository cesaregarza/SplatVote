import React, { useMemo, useState } from 'react';
import ItemCard from '../shared/ItemCard';
import CommentBox from '../shared/CommentBox';

function MultiSelect({ category, items, onVote, loading }) {
  const [selected, setSelected] = useState([]);
  const [comment, setComment] = useState(null);

  const maxChoices = useMemo(() => {
    const configured = category?.settings?.max_choices;
    if (typeof configured === 'number' && configured > 0) {
      return configured;
    }
    return null;
  }, [category]);

  const handleToggle = (itemId) => {
    setSelected((prev) => {
      if (prev.includes(itemId)) {
        return prev.filter((id) => id !== itemId);
      }
      if (maxChoices && prev.length >= maxChoices) {
        return prev;
      }
      return [...prev, itemId];
    });
  };

  const handleSubmit = () => {
    if (selected.length > 0) {
      onVote(selected, comment);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <p className="text-center text-slate-300 mb-2">
        Select one or more options:
      </p>
      {maxChoices && (
        <p className="text-center text-slate-400 mb-6">
          Choose up to {maxChoices}
        </p>
      )}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
        {items.map((item) => (
          <ItemCard
            key={item.id}
            item={item}
            selected={selected.includes(item.id)}
            onClick={() => handleToggle(item.id)}
            disabled={loading}
          />
        ))}
      </div>
      <div className="text-center">
        <CommentBox onSubmit={setComment} />
        <button
          onClick={handleSubmit}
          disabled={selected.length < 1 || loading}
          className="mt-6 px-8 py-3 bg-fuchsia-600 text-white text-lg font-semibold rounded-full
                     hover:bg-fuchsia-500 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all"
        >
          {loading ? 'Submitting...' : 'Submit Vote'}
        </button>
      </div>
    </div>
  );
}

export default MultiSelect;
