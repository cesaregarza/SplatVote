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
        className="text-slate-300 hover:text-white transition-colors text-sm"
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
        className="w-full p-3 bg-slate-900/60 border border-white/10 rounded-lg text-white
                   placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-fuchsia-500/60"
        rows={3}
      />
      <div className="flex justify-between items-center">
        <span className="text-slate-400 text-sm">
          {comment.length}/{maxLength}
        </span>
        <div className="space-x-2">
          <button
            onClick={() => setIsOpen(false)}
            className="px-3 py-1 text-slate-300 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!comment.trim()}
            className="px-4 py-1 bg-fuchsia-600 text-white rounded-lg
                       hover:bg-fuchsia-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Add Comment
          </button>
        </div>
      </div>
    </div>
  );
}

export default CommentBox;
