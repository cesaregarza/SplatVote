import React, { useState } from 'react';
import ItemCard from '../shared/ItemCard';
import CommentBox from '../shared/CommentBox';

function SingleChoice({ items, onVote, loading }) {
  const [selected, setSelected] = useState(null);
  const [comment, setComment] = useState(null);

  const handleSubmit = () => {
    if (selected) {
      onVote([selected], comment);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <p className="text-center text-gray-400 mb-6">
        Select one option:
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
        {items.map(item => (
          <ItemCard
            key={item.id}
            item={item}
            selected={selected === item.id}
            onClick={() => setSelected(item.id)}
            disabled={loading}
          />
        ))}
      </div>
      <div className="text-center">
        <CommentBox onSubmit={setComment} />
        <button
          onClick={handleSubmit}
          disabled={!selected || loading}
          className="mt-6 px-8 py-3 bg-splat-orange text-white text-lg font-bold rounded-xl
                     hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all transform hover:scale-105"
        >
          {loading ? 'Submitting...' : 'Submit Vote'}
        </button>
      </div>
    </div>
  );
}

export default SingleChoice;
