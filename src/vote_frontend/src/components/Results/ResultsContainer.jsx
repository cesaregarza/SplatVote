import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useVoteAPI } from '../../hooks/useVoteAPI';
import { useFingerprint } from '../../hooks/useFingerprint';
import PercentageChart from './PercentageChart';
import EloRankings from './EloRankings';
import WilsonConfidence from './WilsonConfidence';
import TournamentDetails from '../shared/TournamentDetails';

function ResultsContainer() {
  const { categoryId } = useParams();
  const [results, setResults] = useState(null);
  const [category, setCategory] = useState(null);
  const { fingerprint, loading: fpLoading } = useFingerprint();
  const {
    fetchResults,
    loading: resultsLoading,
    error: resultsError,
  } = useVoteAPI();
  const {
    fetchCategory,
    loading: categoryLoading,
    error: categoryError,
  } = useVoteAPI();

  useEffect(() => {
    fetchCategory(categoryId).then(setCategory);
  }, [categoryId, fetchCategory]);

  useEffect(() => {
    if (!categoryId || fpLoading) return;
    fetchResults(categoryId, fingerprint).then(setResults);
  }, [categoryId, fingerprint, fpLoading, fetchResults]);

  const isLoading =
    (resultsLoading || categoryLoading || fpLoading) && !results && !category;
  const isPrivate =
    resultsError &&
    resultsError.toLowerCase().includes('private');

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-fuchsia-400"></div>
      </div>
    );
  }

  if (categoryError && !category) {
    return (
      <div className="text-center py-20">
        <p className="text-rose-300 text-lg">{categoryError}</p>
        <Link to="/" className="mt-4 inline-block text-fuchsia-300 hover:underline">
          ← Back to categories
        </Link>
      </div>
    );
  }

  const ResultsComponent = {
    single_choice: WilsonConfidence,
    elo_tournament: EloRankings,
    ranked_list: PercentageChart,
  }[results?.comparison_mode] || PercentageChart;

  const heading = category?.name || results?.category_name || 'Results';
  const description = category?.description || null;

  return (
    <div>
      <div className="mb-8">
        <Link to="/" className="text-fuchsia-300 hover:underline">
          ← Back to categories
        </Link>
      </div>
      <div className="text-center mb-8">
        <h1 className="text-3xl font-semibold text-white mb-2">{heading}</h1>
        {description && (
          <p className="text-slate-300">{description}</p>
        )}
        {results && (
          <p className="text-slate-300">
            {results.total_votes} total vote{results.total_votes !== 1 ? 's' : ''}
          </p>
        )}
      </div>
      {category && (
        <TournamentDetails
          tournament={category.settings?.tournament}
          privateResults={category.settings?.private_results}
        />
      )}
      {isPrivate && (
        <div className="mt-10 text-center">
          <div className="inline-flex items-center rounded-full border border-fuchsia-500/30 bg-fuchsia-500/10 px-4 py-1 text-xs uppercase tracking-[0.3em] text-fuchsia-200">
            Results locked
          </div>
          {category?.comparison_mode === 'tournament_tiers' ? (
            <>
              <h2 className="mt-4 text-2xl font-semibold text-white">
                Thanks for your input!
              </h2>
              <p className="mt-3 text-slate-300">
                Your votes help us calibrate tournament tiers for the community.
              </p>
              <Link
                to={`/vote/${categoryId}`}
                className="mt-6 inline-block rounded-full bg-fuchsia-600 px-6 py-3 text-white hover:bg-fuchsia-500"
              >
                Back to voting
              </Link>
            </>
          ) : (
            <>
              <h2 className="mt-4 text-2xl font-semibold text-white">
                Results are private for this vote
              </h2>
              <p className="mt-3 text-slate-300">
                Cast your vote to unlock the current standings.
              </p>
              <Link
                to={`/vote/${categoryId}`}
                className="mt-6 inline-block rounded-full bg-fuchsia-600 px-6 py-3 text-white hover:bg-fuchsia-500"
              >
                Vote to unlock
              </Link>
            </>
          )}
        </div>
      )}
      {!isPrivate && results && (
        <>
          <ResultsComponent results={results.results} totalVotes={results.total_votes} />
          <div className="text-center mt-8">
            <Link
              to={`/vote/${categoryId}`}
              className="inline-block rounded-full bg-fuchsia-600 px-6 py-3 text-white hover:bg-fuchsia-500"
            >
              Cast Your Vote
            </Link>
          </div>
        </>
      )}
      {!isPrivate && !results && resultsError && (
        <div className="text-center py-20">
          <p className="text-rose-300 text-lg">{resultsError}</p>
          <Link to="/" className="mt-4 inline-block text-fuchsia-300 hover:underline">
            ← Back to categories
          </Link>
        </div>
      )}
    </div>
  );
}

export default ResultsContainer;
