import React from 'react';

const formatEntry = (entry) => {
  if (!entry) return '';
  if (typeof entry === 'string') return entry;
  if (typeof entry === 'number') return String(entry);
  // Handle nested team structure: { placement: 1, team: { name: "Team Name", ... } }
  const name = entry.name || entry.label || (entry.team && entry.team.name) || '';
  if (entry.placement) {
    return `#${entry.placement} ${name || 'Unknown'}`;
  }
  return name;
};

function TournamentDetails({ tournament, privateResults }) {
  if (!tournament) return null;

  const tierLabel = tournament.tier ? tournament.tier.toUpperCase() : null;
  const topParticipants = Array.isArray(tournament.top_participants)
    ? tournament.top_participants.map(formatEntry).filter(Boolean)
    : [];
  const winners = Array.isArray(tournament.winners)
    ? tournament.winners.map(formatEntry).filter(Boolean)
    : [];

  return (
    <div className="mt-6 rounded-2xl border border-white/5 bg-slate-900/60 p-6 text-left shadow-[0_20px_50px_rgba(2,6,23,0.35)]">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs uppercase tracking-[0.35em] text-slate-400">
          Tournament
        </span>
        {tierLabel && (
          <span className="rounded-full border border-fuchsia-500/30 bg-fuchsia-500/10 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-wide text-fuchsia-200">
            {tierLabel}
          </span>
        )}
        {privateResults && (
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-200">
            Private results
          </span>
        )}
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Name</p>
          <p className="mt-2 text-lg font-semibold text-white">
            {tournament.name || 'Tournament'}
          </p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500">ID</p>
          <p className="mt-2 text-sm font-medium text-slate-200">
            {tournament.id || 'N/A'}
          </p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Link</p>
          {tournament.url && (tournament.url.startsWith('https://') || tournament.url.startsWith('http://')) ? (
            <a
              href={tournament.url}
              className="mt-2 inline-flex items-center text-sm font-semibold text-fuchsia-200 hover:text-fuchsia-100"
              target="_blank"
              rel="noreferrer"
            >
              View full bracket
            </a>
          ) : (
            <p className="mt-2 text-sm text-slate-400">Not available</p>
          )}
        </div>
      </div>
      {(topParticipants.length > 0 || winners.length > 0) && (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-slate-500">
              Top participants
            </p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {topParticipants.length === 0 && (
                <li className="text-sm text-slate-400">Not listed</li>
              )}
              {topParticipants.map((entry) => (
                <li
                  key={entry}
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-200"
                >
                  {entry}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-slate-500">
              Winners
            </p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {winners.length === 0 && (
                <li className="text-sm text-slate-400">Not listed</li>
              )}
              {winners.map((entry) => (
                <li
                  key={entry}
                  className="rounded-full border border-fuchsia-500/30 bg-fuchsia-500/10 px-3 py-1 text-xs font-semibold text-fuchsia-100"
                >
                  {entry}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export default TournamentDetails;
