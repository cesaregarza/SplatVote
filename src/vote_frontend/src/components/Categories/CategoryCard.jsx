import React from 'react';
import { Link } from 'react-router-dom';
import Badge from '../shared/Badge';

const MODE_LABELS = {
  single_choice: 'Single Choice',
  multi_select: 'Multi Select',
  elo_tournament: 'Head-to-Head',
  ranked_list: 'Ranked List',
  tournament_tiers: 'Tier Vote',
};

function CategoryCard({ category }) {
  const tournament = category?.settings?.tournament;
  const tierLabel = tournament?.tier ? tournament.tier.toUpperCase() : null;
  const privateResults = category?.settings?.private_results;
  const discordRequired = category?.settings?.discord_required;
  const discordReason = category?.settings?.discord_reason;

  return (
    <div className="group rounded-2xl border border-white/5 bg-slate-900/60 shadow-[0_18px_40px_rgba(2,6,23,0.45)] transition hover:border-fuchsia-500/40">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs uppercase tracking-[0.25em] text-slate-400">
            Mode
          </span>
          <div className="flex flex-wrap items-center gap-2">
            {tierLabel && (
              <Badge variant="mode">
                {tierLabel}
              </Badge>
            )}
            {discordRequired && (
              <Badge variant="discord">
                Discord required
              </Badge>
            )}
            {privateResults && (
              <Badge>
                Private results
              </Badge>
            )}
            <Badge variant="mode" size="md">
              {MODE_LABELS[category.comparison_mode]}
            </Badge>
          </div>
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">
          {category.name}
        </h2>
        {category.description && (
          <p className="text-slate-300 text-sm mb-4 line-clamp-2">
            {category.description}
          </p>
        )}
        {discordRequired && discordReason && (
          <p className="text-sky-200/90 text-sm mb-4">
            Why Discord: {discordReason}
          </p>
        )}
        <div className="flex gap-3">
          <Link
            to={`/vote/${category.id}`}
            className="flex-1 text-center py-2 rounded-full bg-fuchsia-600 text-white transition hover:bg-fuchsia-500 font-medium"
          >
            Vote
          </Link>
          <Link
            to={`/results/${category.id}`}
            className="flex-1 text-center py-2 rounded-full bg-white/5 text-white transition hover:bg-white/10 font-medium"
          >
            Results
          </Link>
        </div>
      </div>
    </div>
  );
}

export default CategoryCard;
