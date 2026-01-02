import React, { useState } from 'react';

function CommentBox({ onSubmit, maxLength = 1000 }) {
  const [comment, setComment] = useState('');
  const [isOpen, setIsOpen] = useState(false);

  const handleSubmit = () => {
    if (comment.trim()) {
      onSubmit(comment.trim());
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="text-gray-400 hover:text-white transition-colors text-sm"
      >
        + Add a comment (optional)
      </button>
    );
  }

  return (
    <div className="mt-4 space-y-2">
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value.slice(0, maxLength))}
        placeholder="Share why you voted this way..."
        className="w-full p-3 bg-gray-800 border border-gray-600 rounded-lg text-white
                   placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-splat-orange"
        rows={3}
      />
      <div className="flex justify-between items-center">
        <span className="text-gray-500 text-sm">
          {comment.length}/{maxLength}
        </span>
        <div className="space-x-2">
          <button
            onClick={() => setIsOpen(false)}
            className="px-3 py-1 text-gray-400 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!comment.trim()}
            className="px-4 py-1 bg-splat-orange text-white rounded-lg
                       hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Add Comment
          </button>
        </div>
      </div>
    </div>
  );
}

export default CommentBox;
