import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useVoteAPI } from '../../hooks/useVoteAPI';
import PercentageChart from './PercentageChart';
import EloRankings from './EloRankings';
import WilsonConfidence from './WilsonConfidence';

function ResultsContainer() {
  const { categoryId } = useParams();
  const [results, setResults] = useState(null);
  const { fetchResults, loading, error } = useVoteAPI();

  useEffect(() => {
    fetchResults(categoryId).then(setResults);
  }, [categoryId, fetchResults]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-fuchsia-400"></div>
      </div>
    );
  }

  if (error || !results) {
    return (
      <div className="text-center py-20">
        <p className="text-rose-300 text-lg">{error || 'Results not found'}</p>
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
  }[results.comparison_mode] || PercentageChart;

  return (
    <div>
      <div className="mb-8">
        <Link to="/" className="text-fuchsia-300 hover:underline">
          ← Back to categories
        </Link>
      </div>
      <div className="text-center mb-8">
        <h1 className="text-3xl font-semibold text-white mb-2">{results.category_name}</h1>
        <p className="text-slate-300">
          {results.total_votes} total vote{results.total_votes !== 1 ? 's' : ''}
        </p>
      </div>
      <ResultsComponent results={results.results} totalVotes={results.total_votes} />
      <div className="text-center mt-8">
        <Link
          to={`/vote/${categoryId}`}
          className="inline-block rounded-full bg-fuchsia-600 px-6 py-3 text-white hover:bg-fuchsia-500"
        >
          Cast Your Vote
        </Link>
      </div>
    </div>
  );
}

export default ResultsContainer;
