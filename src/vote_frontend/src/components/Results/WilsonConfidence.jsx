import React from 'react';

function WilsonConfidence({ results, totalVotes }) {
  if (!results || results.length === 0) {
    return (
      <div className="text-center py-10 text-slate-400">
        No votes yet. Be the first to vote!
      </div>
    );
  }

  // Sort by Wilson lower bound (more confident ranking)
  const sorted = [...results].sort((a, b) => (b.wilson_lower || 0) - (a.wilson_lower || 0));

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <p className="text-center text-slate-400 text-sm mb-6">
        Results ranked by 95% confidence interval (Wilson score)
      </p>
      {sorted.map((result, index) => {
        const hasConfidence = result.wilson_lower !== null && result.wilson_upper !== null;

        return (
          <div key={result.item_id} className="bg-slate-900/60 border border-white/5 rounded-xl p-4">
            <div className="flex items-center gap-4 mb-3">
              <div className={`
                flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full font-semibold
                ${index === 0 ? 'bg-fuchsia-400 text-slate-950' : ''}
                ${index === 1 ? 'bg-fuchsia-300 text-slate-950' : ''}
                ${index === 2 ? 'bg-fuchsia-500 text-slate-950' : ''}
                ${index > 2 ? 'bg-fuchsia-500/20 text-fuchsia-100' : ''}
              `}>
                {index + 1}
              </div>
              {result.image_url && (
                <img
                  src={result.image_url}
                  alt={result.item_name}
                  className="w-12 h-12 object-contain"
                />
              )}
              <div className="flex-1">
                <h3 className="font-semibold text-white">{result.item_name}</h3>
                <p className="text-slate-400 text-sm">
                  {result.vote_count} vote{result.vote_count !== 1 ? 's' : ''}
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-semibold text-fuchsia-300">
                  {result.percentage.toFixed(1)}%
                </div>
                {hasConfidence && (
                  <div className="text-xs text-slate-400">
                    {result.wilson_lower.toFixed(1)}% - {result.wilson_upper.toFixed(1)}%
                  </div>
                )}
              </div>
            </div>

            {/* Confidence interval visualization */}
            <div className="relative h-4 bg-slate-800/70 rounded-full overflow-hidden">
              {hasConfidence && (
                <>
                  {/* Full range background */}
                  <div
                    className="absolute h-full bg-fuchsia-500/30"
                    style={{
                      left: `${result.wilson_lower}%`,
                      width: `${result.wilson_upper - result.wilson_lower}%`,
                    }}
                  />
                  {/* Actual percentage point */}
                  <div
                    className="absolute h-full w-1 bg-fuchsia-300"
                    style={{ left: `${result.percentage}%` }}
                  />
                </>
              )}
              {/* Bar fill */}
              <div
                className="h-full bg-gradient-to-r from-fuchsia-500 via-fuchsia-400 to-fuchsia-600 rounded-full"
                style={{ width: `${result.percentage}%` }}
              />
            </div>
          </div>
        );
      })}
      <p className="text-center text-slate-500 text-xs mt-4">
        The shaded area shows the 95% confidence interval. More votes = narrower interval.
      </p>
    </div>
  );
}

export default WilsonConfidence;
