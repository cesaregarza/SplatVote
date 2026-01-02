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
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-splat-orange"></div>
      </div>
    );
  }

  if (error || !category) {
    return (
      <div className="text-center py-20">
        <p className="text-red-500 text-lg">{error || 'Category not found'}</p>
        <Link to="/" className="mt-4 inline-block text-splat-orange hover:underline">
          ← Back to categories
        </Link>
      </div>
    );
  }

  if (voteResult) {
    return (
      <div className="max-w-md mx-auto text-center py-20">
        <div className="text-6xl mb-4">🎉</div>
        <h2 className="text-2xl font-bold text-white mb-4">Vote Recorded!</h2>
        <p className="text-gray-400 mb-8">{voteResult.message}</p>
        <div className="space-x-4">
          <Link
            to={`/results/${categoryId}`}
            className="inline-block px-6 py-3 bg-splat-orange text-white rounded-lg hover:bg-orange-600"
          >
            View Results
          </Link>
          <Link
            to="/"
            className="inline-block px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
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
        <div className="text-6xl mb-4">✅</div>
        <h2 className="text-2xl font-bold text-white mb-4">Already Voted</h2>
        <p className="text-gray-400 mb-8">
          You've already cast your vote in this category.
        </p>
        <div className="space-x-4">
          <Link
            to={`/results/${categoryId}`}
            className="inline-block px-6 py-3 bg-splat-orange text-white rounded-lg hover:bg-orange-600"
          >
            View Results
          </Link>
          <Link
            to="/"
            className="inline-block px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
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
        <p className="text-red-500">Unsupported vote type: {category.comparison_mode}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <Link to="/" className="text-splat-orange hover:underline">
          ← Back to categories
        </Link>
      </div>
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">{category.name}</h1>
        {category.description && (
          <p className="text-gray-400">{category.description}</p>
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
