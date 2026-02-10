import React from 'react';
import { Link } from 'react-router-dom';
import Badge from '../shared/Badge';

function SurveyCard({ survey }) {
  const questionLabel = survey.questionCount === 1
    ? '1 question'
    : `${survey.questionCount} questions`;

  return (
    <div className="group rounded-2xl border border-sky-500/20 bg-slate-900/60 shadow-[0_18px_40px_rgba(2,6,23,0.45)] transition hover:border-sky-400/50">
      <div className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <Badge variant="discord" size="md">
            Survey
          </Badge>
          <div className="flex flex-wrap items-center gap-2">
            <Badge>
              {questionLabel}
            </Badge>
            {survey.discordRequired && (
              <Badge variant="discord">
                Discord required
              </Badge>
            )}
          </div>
        </div>
        <h2 className="mb-2 text-xl font-semibold text-white">
          {survey.label}
        </h2>
        <p className="mb-4 text-slate-300 text-sm">
          Answer each question in sequence.
        </p>
        {survey.discordRequired && survey.discordReason && (
          <p className="text-sky-200/90 text-sm mb-4">
            Why Discord: {survey.discordReason}
          </p>
        )}
        <Link
          to={`/survey/${encodeURIComponent(survey.key)}`}
          className="block w-full text-center py-2 rounded-full bg-sky-600 text-white transition hover:bg-sky-500 font-medium"
        >
          Start Survey
        </Link>
      </div>
    </div>
  );
}

export default SurveyCard;
