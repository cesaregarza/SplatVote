import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useVoteAPI } from '../../hooks/useVoteAPI';
import { useFingerprint } from '../../hooks/useFingerprint';
import SingleChoice from './SingleChoice';
import EloTournament from './EloTournament';
import RankedList from './RankedList';

function VoteContainer() {
  const { categoryId } = useParams();
  const [category, setCategory] = useState(null);
  const [voteStatus, setVoteStatus] = useState(null);
  const [voteResult, setVoteResult] = useState(null);

  const { fetchCategory, checkVoteStatus, submitVote, loading, error } = useVoteAPI();
  const { fingerprint, loading: fpLoading } = useFingerprint();

  useEffect(() => {
    fetchCategory(categoryId).then(setCategory);
  }, [categoryId, fetchCategory]);

  useEffect(() => {
    if (fingerprint && categoryId) {
      checkVoteStatus(categoryId, fingerprint).then(setVoteStatus);
    }
  }, [categoryId, fingerprint, checkVoteStatus]);

  const handleVote = async (choices, comment) => {
    if (!fingerprint) return;
    const result = await submitVote(parseInt(categoryId), fingerprint, choices, comment);
    if (result?.success) {
      setVoteResult(result);
    }
  };

  if (loading || fpLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-fuchsia-400"></div>
      </div>
    );
  }

  if (error || !category) {
    return (
      <div className="text-center py-20">
        <p className="text-rose-300 text-lg">{error || 'Category not found'}</p>
        <Link to="/" className="mt-4 inline-block text-fuchsia-300 hover:underline">
          ← Back to categories
        </Link>
      </div>
    );
  }

  if (voteResult) {
    return (
      <div className="max-w-md mx-auto text-center py-20">
        <div className="inline-flex items-center rounded-full border border-fuchsia-500/30 bg-fuchsia-500/10 px-4 py-1 text-xs uppercase tracking-[0.3em] text-fuchsia-200">
          Vote recorded
        </div>
        <h2 className="mt-5 text-2xl font-semibold text-white">Thanks for voting</h2>
        <p className="mt-3 text-slate-300">{voteResult.message}</p>
        <div className="space-x-4">
          <Link
            to={`/results/${categoryId}`}
            className="mt-6 inline-block rounded-full bg-fuchsia-600 px-6 py-3 text-white hover:bg-fuchsia-500"
          >
            View Results
          </Link>
          <Link
            to="/"
            className="mt-6 inline-block rounded-full bg-white/5 px-6 py-3 text-white hover:bg-white/10"
          >
            More Categories
          </Link>
        </div>
      </div>
    );
  }

  if (voteStatus?.has_voted) {
    return (
      <div className="max-w-md mx-auto text-center py-20">
        <div className="inline-flex items-center rounded-full border border-slate-500/30 bg-slate-800/50 px-4 py-1 text-xs uppercase tracking-[0.3em] text-slate-300">
          Vote locked
        </div>
        <h2 className="mt-5 text-2xl font-semibold text-white">Already voted</h2>
        <p className="mt-3 text-slate-300">
          You've already cast your vote in this category.
        </p>
        <div className="space-x-4">
          <Link
            to={`/results/${categoryId}`}
            className="mt-6 inline-block rounded-full bg-fuchsia-600 px-6 py-3 text-white hover:bg-fuchsia-500"
          >
            View Results
          </Link>
          <Link
            to="/"
            className="mt-6 inline-block rounded-full bg-white/5 px-6 py-3 text-white hover:bg-white/10"
          >
            More Categories
          </Link>
        </div>
      </div>
    );
  }

  const VoteComponent = {
    single_choice: SingleChoice,
    elo_tournament: EloTournament,
    ranked_list: RankedList,
  }[category.comparison_mode];

  if (!VoteComponent) {
    return (
      <div className="text-center py-20">
        <p className="text-rose-300">Unsupported vote type: {category.comparison_mode}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <Link to="/" className="text-fuchsia-300 hover:underline">
          ← Back to categories
        </Link>
      </div>
      <div className="text-center mb-8">
        <h1 className="text-3xl font-semibold text-white mb-2">{category.name}</h1>
        {category.description && (
          <p className="text-slate-300">{category.description}</p>
        )}
      </div>
      <VoteComponent
        category={category}
        items={category.items}
        onVote={handleVote}
        loading={loading}
      />
    </div>
  );
}

export default VoteContainer;
