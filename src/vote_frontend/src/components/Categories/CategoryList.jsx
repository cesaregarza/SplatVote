import React, { useEffect, useMemo, useState } from 'react';
import { useVoteAPI } from '../../hooks/useVoteAPI';
import CategoryCard from './CategoryCard';
import SurveyCard from './SurveyCard';

function CategoryList() {
  const [categories, setCategories] = useState([]);
  const { fetchCategories, loading, error } = useVoteAPI();

  useEffect(() => {
    fetchCategories().then(setCategories);
  }, [fetchCategories]);

  const surveyEntries = useMemo(() => {
    const surveysByKey = new Map();

    categories.forEach((category) => {
      const settings = category.settings || {};
      const surveyKey = settings.survey_key;
      if (!surveyKey) {
        return;
      }

      if (!surveysByKey.has(surveyKey)) {
        surveysByKey.set(surveyKey, {
          key: surveyKey,
          label: settings.survey_label || surveyKey,
          questionCount: 0,
          discordRequired: false,
          discordReason: null,
        });
      }

      const survey = surveysByKey.get(surveyKey);
      survey.questionCount += 1;
      survey.discordRequired = survey.discordRequired || Boolean(settings.discord_required);
      if (!survey.discordReason && settings.discord_reason) {
        survey.discordReason = settings.discord_reason;
      }
      if (settings.survey_label) {
        survey.label = settings.survey_label;
      }
      if (typeof settings.survey_total_questions === 'number' && settings.survey_total_questions > 0) {
        survey.questionCount = settings.survey_total_questions;
      }
    });

    return Array.from(surveysByKey.values()).sort((a, b) => {
      if (a.label < b.label) return -1;
      if (a.label > b.label) return 1;
      return 0;
    });
  }, [categories]);

  const regularCategories = useMemo(
    () => categories.filter((category) => !(category.settings || {}).survey_key),
    [categories]
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-fuchsia-400"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-rose-300 text-lg">{error}</p>
        <button
          onClick={() => fetchCategories().then(setCategories)}
          className="mt-4 rounded-full bg-fuchsia-600 px-6 py-2 text-white hover:bg-fuchsia-500"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-10 rounded-2xl border border-white/5 bg-slate-900/60 px-6 py-8 shadow-[0_24px_60px_rgba(2,6,23,0.45)]">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          Splatoon 3
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">
          Community Polls
        </h1>
        <p className="mt-2 max-w-2xl text-slate-300">
          Pick a category, cast your vote, and watch the rankings update as the
          community weighs in.
        </p>
      </div>
      {surveyEntries.length > 0 && (
        <div className="mb-10">
          <h2 className="mb-4 text-sm uppercase tracking-[0.3em] text-sky-200">
            Surveys
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {surveyEntries.map((survey) => (
              <SurveyCard key={survey.key} survey={survey} />
            ))}
          </div>
        </div>
      )}
      {regularCategories.length > 0 && (
        <div>
          <h2 className="mb-4 text-sm uppercase tracking-[0.3em] text-slate-400">
            Polls
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {regularCategories.map((category) => (
              <CategoryCard key={category.id} category={category} />
            ))}
          </div>
        </div>
      )}
      {surveyEntries.length === 0 && regularCategories.length === 0 && (
        <p className="text-center text-slate-400 py-10">
          No categories available yet.
        </p>
      )}
    </div>
  );
}

export default CategoryList;
