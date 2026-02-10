import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useVoteAPI } from '../../hooks/useVoteAPI';
import { useFingerprint } from '../../hooks/useFingerprint';
import Badge from '../shared/Badge';

function getQuestionOrder(category) {
  const settings = category?.settings || {};
  const order = settings.survey_question_order;
  if (typeof order === 'number') {
    return order;
  }
  return Number.MAX_SAFE_INTEGER;
}

function getPageOrder(question) {
  const settings = question?.settings || {};
  const explicitOrder = settings.survey_page_order;
  if (typeof explicitOrder === 'number' && Number.isFinite(explicitOrder)) {
    return explicitOrder;
  }
  const pageValue = settings.survey_page;
  if (pageValue !== undefined && pageValue !== null) {
    const parsed = Number.parseInt(String(pageValue), 10);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return Number.MAX_SAFE_INTEGER;
}

function seedFromString(value) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function deterministicShuffle(items, seedValue) {
  const output = [...items];
  let seed = seedFromString(seedValue);
  for (let i = output.length - 1; i > 0; i -= 1) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const j = seed % (i + 1);
    [output[i], output[j]] = [output[j], output[i]];
  }
  return output;
}

function decodeSurveyKey(rawSurveyKey) {
  if (!rawSurveyKey) {
    return '';
  }
  try {
    return decodeURIComponent(rawSurveyKey);
  } catch {
    return rawSurveyKey;
  }
}

function formatQuestionTitle(surveyLabel, name) {
  if (!name) {
    return '';
  }
  const prefix = `${surveyLabel} `;
  if (name.startsWith(prefix)) {
    return name.slice(prefix.length);
  }
  return name;
}

function getPageMeta(question) {
  const settings = question?.settings || {};
  const rawPage = settings.survey_page;
  const pageKey =
    rawPage === undefined || rawPage === null || String(rawPage).trim() === ''
      ? '1'
      : String(rawPage).trim();

  const rawTitle = settings.survey_page_title;
  const pageTitle =
    typeof rawTitle === 'string' && rawTitle.trim()
      ? rawTitle.trim()
      : `Page ${pageKey}`;

  return { key: pageKey, title: pageTitle };
}

function getQuestionSection(question) {
  const settings = question?.settings || {};
  const rawSection = settings.survey_section || settings.section;
  if (typeof rawSection === 'string' && rawSection.trim()) {
    return rawSection.trim();
  }
  return '';
}

function normalizeChoicesForQuestion(question, localAnswers) {
  const mode = question?.comparison_mode;
  if (mode === 'single_choice') {
    const selected = localAnswers[question.id];
    return selected ? [selected] : [];
  }
  if (mode === 'multi_select') {
    return Array.isArray(localAnswers[question.id]) ? localAnswers[question.id] : [];
  }
  return [];
}

function SurveyContainer() {
  const { surveyKey: rawSurveyKey } = useParams();
  const surveyKey = useMemo(() => decodeSurveyKey(rawSurveyKey), [rawSurveyKey]);

  const [surveyQuestions, setSurveyQuestions] = useState([]);
  const [surveyLabel, setSurveyLabel] = useState(surveyKey || 'Survey');
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [voteStatusByCategory, setVoteStatusByCategory] = useState({});
  const [localAnswers, setLocalAnswers] = useState({});
  const [surveyLoading, setSurveyLoading] = useState(true);
  const [submittingPage, setSubmittingPage] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [discordStatus, setDiscordStatus] = useState(null);
  const [discordLoading, setDiscordLoading] = useState(false);

  const {
    fetchCategories,
    fetchVoteStatuses,
    submitVote,
    fetchDiscordAuthStatus,
    error,
  } = useVoteAPI();
  const { fingerprint, loading: fingerprintLoading } = useFingerprint();

  useEffect(() => {
    let cancelled = false;

    setSurveyLoading(true);
    setSurveyQuestions([]);
    setVoteStatusByCategory({});
    setLocalAnswers({});
    setCurrentPageIndex(0);
    setSubmitError(null);

    fetchCategories({ includeItems: true })
      .then((categories) => {
        if (cancelled) {
          return;
        }

        const matchingQuestions = categories
          .filter((category) => (category.settings || {}).survey_key === surveyKey)
          .sort((a, b) => {
            const orderDelta = getQuestionOrder(a) - getQuestionOrder(b);
            if (orderDelta !== 0) {
              return orderDelta;
            }
            return a.id - b.id;
          });

        setSurveyQuestions(matchingQuestions);
        if (matchingQuestions.length > 0) {
          const firstSettings = matchingQuestions[0].settings || {};
          setSurveyLabel(firstSettings.survey_label || surveyKey || 'Survey');
        } else {
          setSurveyLabel(surveyKey || 'Survey');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setSurveyLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fetchCategories, surveyKey]);

  const pages = useMemo(() => {
    const pagesByKey = new Map();
    surveyQuestions.forEach((question) => {
      const pageMeta = getPageMeta(question);
      if (!pagesByKey.has(pageMeta.key)) {
        pagesByKey.set(pageMeta.key, {
          key: pageMeta.key,
          title: pageMeta.title,
          order: getPageOrder(question),
          questions: [],
        });
      } else {
        const existingPage = pagesByKey.get(pageMeta.key);
        existingPage.order = Math.min(existingPage.order, getPageOrder(question));
        if (existingPage.title.startsWith('Page ') && pageMeta.title) {
          existingPage.title = pageMeta.title;
        }
      }
      pagesByKey.get(pageMeta.key).questions.push(question);
    });
    return Array.from(pagesByKey.values()).sort((a, b) => {
      if (a.order !== b.order) {
        return a.order - b.order;
      }
      return a.key.localeCompare(b.key, undefined, { numeric: true, sensitivity: 'base' });
    });
  }, [surveyQuestions]);

  useEffect(() => {
    if (!fingerprint || surveyQuestions.length === 0) {
      return;
    }

    let cancelled = false;
    fetchVoteStatuses(
      surveyQuestions.map((question) => question.id),
      fingerprint
    ).then((statusMap) => {
      if (cancelled) {
        return;
      }

      const nextStatuses = {};
      Object.entries(statusMap).forEach(([key, status]) => {
        const categoryId = Number(key);
        if (!Number.isNaN(categoryId)) {
          nextStatuses[categoryId] = status;
        }
      });
      setVoteStatusByCategory(nextStatuses);
    });

    return () => {
      cancelled = true;
    };
  }, [fetchVoteStatuses, fingerprint, surveyQuestions]);

  useEffect(() => {
    if (pages.length === 0) {
      setCurrentPageIndex(0);
      return;
    }

    const firstPageWithUnanswered = pages.findIndex((page) =>
      page.questions.some((question) => !voteStatusByCategory[question.id]?.has_voted)
    );

    if (firstPageWithUnanswered >= 0) {
      setCurrentPageIndex(firstPageWithUnanswered);
      return;
    }

    setCurrentPageIndex((existing) => Math.min(existing, pages.length - 1));
  }, [pages, voteStatusByCategory]);

  const currentPage = useMemo(
    () => pages[currentPageIndex] || null,
    [pages, currentPageIndex]
  );
  const currentPageQuestions = useMemo(
    () => currentPage?.questions || [],
    [currentPage]
  );
  const displayItemsByQuestionId = useMemo(() => {
    const itemsByQuestionId = {};

    currentPageQuestions.forEach((question) => {
      const items = question?.items || [];
      const shuffleEnabled = Boolean((question?.settings || {}).shuffle);
      if (!shuffleEnabled || items.length <= 1) {
        itemsByQuestionId[question.id] = items;
        return;
      }
      const seed = `${fingerprint || 'anonymous'}:${question.id}`;
      itemsByQuestionId[question.id] = deterministicShuffle(items, seed);
    });

    return itemsByQuestionId;
  }, [currentPageQuestions, fingerprint]);

  const currentPageRequiresDiscord = useMemo(
    () =>
      currentPageQuestions.some(
        (question) => Boolean((question.settings || {}).discord_required)
      ),
    [currentPageQuestions]
  );

  const currentPageDiscordReason = useMemo(() => {
    const question = currentPageQuestions.find((candidate) =>
      Boolean((candidate.settings || {}).discord_required)
    );
    if (!question) {
      return null;
    }
    const reason = (question.settings || {}).discord_reason;
    if (typeof reason === 'string' && reason.trim()) {
      return reason.trim();
    }
    return null;
  }, [currentPageQuestions]);

  useEffect(() => {
    if (!currentPageRequiresDiscord) {
      setDiscordStatus(null);
      setDiscordLoading(false);
      return;
    }

    let cancelled = false;
    setDiscordLoading(true);

    fetchDiscordAuthStatus()
      .then((status) => {
        if (!cancelled) {
          setDiscordStatus(status);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setDiscordLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [currentPageRequiresDiscord, fetchDiscordAuthStatus, currentPageIndex]);

  const answeredCount = useMemo(
    () =>
      surveyQuestions.reduce(
        (count, question) => count + (voteStatusByCategory[question.id]?.has_voted ? 1 : 0),
        0
      ),
    [surveyQuestions, voteStatusByCategory]
  );
  const totalCount = surveyQuestions.length;
  const allAnswered = totalCount > 0 && answeredCount === totalCount;

  const currentPageSections = useMemo(() => {
    const sectionsByKey = new Map();

    currentPageQuestions.forEach((question) => {
      const sectionTitle = getQuestionSection(question);
      const sectionKey = sectionTitle || '__default__';
      if (!sectionsByKey.has(sectionKey)) {
        sectionsByKey.set(sectionKey, {
          key: sectionKey,
          title: sectionTitle,
          questions: [],
        });
      }
      sectionsByKey.get(sectionKey).questions.push(question);
    });

    return Array.from(sectionsByKey.values());
  }, [currentPageQuestions]);

  const unansweredQuestionIdsOnPage = useMemo(
    () =>
      currentPageQuestions
        .filter((question) => !voteStatusByCategory[question.id]?.has_voted)
        .map((question) => question.id),
    [currentPageQuestions, voteStatusByCategory]
  );

  const toggleSingleChoice = (questionId, itemId) => {
    setLocalAnswers((existing) => ({
      ...existing,
      [questionId]: existing[questionId] === itemId ? null : itemId,
    }));
  };

  const toggleMultiChoice = (questionId, itemId, maxChoices) => {
    setLocalAnswers((existing) => {
      const current = Array.isArray(existing[questionId]) ? existing[questionId] : [];
      if (current.includes(itemId)) {
        return {
          ...existing,
          [questionId]: current.filter((id) => id !== itemId),
        };
      }
      if (typeof maxChoices === 'number' && maxChoices > 0 && current.length >= maxChoices) {
        return existing;
      }
      return {
        ...existing,
        [questionId]: [...current, itemId],
      };
    });
  };

  const handleSubmitCurrentPage = async () => {
    if (!fingerprint || unansweredQuestionIdsOnPage.length === 0) {
      return;
    }

    setSubmitError(null);
    setSubmittingPage(true);

    const nextStatuses = { ...voteStatusByCategory };
    const questionById = Object.fromEntries(
      currentPageQuestions.map((question) => [question.id, question])
    );

    try {
      for (const questionId of unansweredQuestionIdsOnPage) {
        const questionDetail = questionById[questionId];
        if (!questionDetail) {
          throw new Error('Some questions are unavailable. Please refresh and try again.');
        }

        const choices = normalizeChoicesForQuestion(questionDetail, localAnswers);
        if (questionDetail.comparison_mode === 'single_choice') {
          if (choices.length !== 1) {
            throw new Error(`Please answer "${formatQuestionTitle(surveyLabel, questionDetail.name)}".`);
          }
        } else if (questionDetail.comparison_mode === 'multi_select') {
          const maxChoices = questionDetail.settings?.max_choices;
          if (choices.length < 1) {
            throw new Error(`Please answer "${formatQuestionTitle(surveyLabel, questionDetail.name)}".`);
          }
          if (
            typeof maxChoices === 'number' &&
            maxChoices > 0 &&
            choices.length > maxChoices
          ) {
            throw new Error(
              `"${formatQuestionTitle(surveyLabel, questionDetail.name)}" allows up to ${maxChoices} selections.`
            );
          }
        } else {
          throw new Error(
            `"${formatQuestionTitle(surveyLabel, questionDetail.name)}" uses an unsupported question type for row mode.`
          );
        }

        const result = await submitVote(questionId, fingerprint, choices, null);
        if (!result?.success) {
          throw new Error('Failed to save one or more answers.');
        }
        nextStatuses[questionId] = { has_voted: true, vote_id: result.vote_id };
      }

      setVoteStatusByCategory(nextStatuses);

      setLocalAnswers((existing) => {
        const trimmed = { ...existing };
        unansweredQuestionIdsOnPage.forEach((questionId) => {
          delete trimmed[questionId];
        });
        return trimmed;
      });

      const nextPageIndex = pages.findIndex((page, index) =>
        index > currentPageIndex &&
        page.questions.some((question) => !nextStatuses[question.id]?.has_voted)
      );
      if (nextPageIndex >= 0) {
        setCurrentPageIndex(nextPageIndex);
      }
    } catch (err) {
      setSubmitError(err.message || 'Failed to submit this page.');
    } finally {
      setSubmittingPage(false);
    }
  };

  const handlePreviousPage = () => {
    setSubmitError(null);
    setCurrentPageIndex((index) => Math.max(0, index - 1));
  };

  const handleNextPage = () => {
    setSubmitError(null);
    setCurrentPageIndex((index) => Math.min(pages.length - 1, index + 1));
  };

  if (surveyLoading || fingerprintLoading || discordLoading) {
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
        <Link to="/" className="mt-4 inline-block text-fuchsia-300 hover:underline">
          ← Back to categories
        </Link>
      </div>
    );
  }

  if (surveyQuestions.length === 0 || !currentPage) {
    return (
      <div className="text-center py-20">
        <p className="text-rose-300 text-lg">Survey not found.</p>
        <Link to="/" className="mt-4 inline-block text-fuchsia-300 hover:underline">
          ← Back to categories
        </Link>
      </div>
    );
  }

  if (currentPageRequiresDiscord && !discordStatus?.authenticated) {
    return (
      <div className="max-w-md mx-auto text-center py-20">
        <div className="inline-flex items-center">
          <Badge variant="discord" size="lg">
            Discord required
          </Badge>
        </div>
        <h2 className="mt-5 text-2xl font-semibold text-white">Sign in to answer</h2>
        <p className="mt-3 text-slate-300">
          This survey requires Discord login before you can submit responses.
        </p>
        {currentPageDiscordReason && (
          <p className="mt-2 text-sky-200/90">
            Reason: {currentPageDiscordReason}
          </p>
        )}
        <div className="space-x-4">
          <a
            href={discordStatus?.login_url || '/auth/discord/login'}
            className="mt-6 inline-block rounded-full bg-sky-600 px-6 py-3 text-white hover:bg-sky-500"
          >
            Sign in with Discord
          </a>
          <Link
            to="/"
            className="mt-6 inline-block rounded-full bg-white/5 px-6 py-3 text-white hover:bg-white/10"
          >
            Back to categories
          </Link>
        </div>
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

      <div className="mb-8 rounded-2xl border border-white/10 bg-slate-900/60 p-6">
        <h1 className="text-3xl font-semibold text-white">{surveyLabel}</h1>
        <p className="mt-2 text-slate-300">
          {currentPage.title} ({currentPageIndex + 1} / {pages.length})
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {currentPageRequiresDiscord && (
            <Badge variant="discord" size="md">
              Discord required
            </Badge>
          )}
          {discordStatus?.bypass_enabled && (
            <Badge variant="muted" size="md">
              Dev bypass active
            </Badge>
          )}
          {allAnswered && (
            <Badge variant="success" size="md">
              Survey complete
            </Badge>
          )}
        </div>
        <div className="mt-4 h-2 w-full rounded-full bg-slate-800">
          <div
            className="h-2 rounded-full bg-sky-400 transition-all"
            style={{ width: `${totalCount ? (answeredCount / totalCount) * 100 : 0}%` }}
          />
        </div>
        <p className="mt-2 text-sm text-slate-400">
          {answeredCount} of {totalCount} answered
        </p>
      </div>

      {currentPageSections.map((section) => (
        <section key={section.key} className="mb-8">
          {section.title && (
            <h2 className="mb-4 text-lg font-semibold text-slate-100">{section.title}</h2>
          )}
          <div className="space-y-4">
            {section.questions.map((question) => {
              const detail = question;
              const answered = Boolean(voteStatusByCategory[question.id]?.has_voted);
              const mode = detail.comparison_mode;
              const localSingleAnswer = localAnswers[question.id];
              const localMultiAnswer = Array.isArray(localAnswers[question.id])
                ? localAnswers[question.id]
                : [];
              const maxChoices = detail.settings?.max_choices;

              return (
                <article
                  key={question.id}
                  className="rounded-2xl border border-white/10 bg-slate-900/50 p-5"
                >
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-lg font-semibold text-white">
                      {formatQuestionTitle(surveyLabel, question.name)}
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {mode === 'multi_select' && typeof maxChoices === 'number' && maxChoices > 0 && (
                        <Badge size="sm">Up to {maxChoices}</Badge>
                      )}
                      {answered && <Badge variant="success" size="sm">Answered</Badge>}
                    </div>
                  </div>

                  {question.description && (
                    <p className="mb-4 text-sm text-slate-300">{question.description}</p>
                  )}

                  {mode === 'single_choice' && (
                    <div className="flex flex-wrap gap-2">
                      {(displayItemsByQuestionId[question.id] || []).map((item) => {
                        const selected = localSingleAnswer === item.id;
                        return (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => toggleSingleChoice(question.id, item.id)}
                            disabled={answered || submittingPage}
                            className={`rounded-full border px-4 py-2 text-sm transition-all ${
                              selected
                                ? 'border-sky-400/50 bg-sky-500/20 text-sky-100'
                                : 'border-white/10 bg-white/5 text-slate-200 hover:bg-white/10'
                            } ${answered || submittingPage ? 'opacity-60 cursor-not-allowed' : ''}`}
                          >
                            {item.name}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {mode === 'multi_select' && (
                    <div className="flex flex-wrap gap-2">
                      {(displayItemsByQuestionId[question.id] || []).map((item) => {
                        const selected = localMultiAnswer.includes(item.id);
                        const atLimit =
                          typeof maxChoices === 'number' &&
                          maxChoices > 0 &&
                          localMultiAnswer.length >= maxChoices &&
                          !selected;

                        return (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => toggleMultiChoice(question.id, item.id, maxChoices)}
                            disabled={answered || submittingPage || atLimit}
                            className={`rounded-full border px-4 py-2 text-sm transition-all ${
                              selected
                                ? 'border-sky-400/50 bg-sky-500/20 text-sky-100'
                                : 'border-white/10 bg-white/5 text-slate-200 hover:bg-white/10'
                            } ${answered || submittingPage || atLimit ? 'opacity-60 cursor-not-allowed' : ''}`}
                          >
                            {item.name}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {mode !== 'single_choice' && mode !== 'multi_select' && (
                    <p className="text-sm text-rose-300">
                      Unsupported question type for row mode: {mode}
                    </p>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      ))}

      {submitError && (
        <p className="mb-6 text-center text-rose-300">{submitError}</p>
      )}

      <div className="mt-10 flex items-center justify-between">
        <button
          type="button"
          onClick={handlePreviousPage}
          disabled={currentPageIndex === 0 || submittingPage}
          className="px-6 py-2 rounded-full bg-slate-800 text-white font-semibold
                     hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          Previous page
        </button>

        <button
          type="button"
          onClick={handleSubmitCurrentPage}
          disabled={unansweredQuestionIdsOnPage.length === 0 || submittingPage}
          className="px-6 py-2 rounded-full bg-sky-600 text-white font-semibold
                     hover:bg-sky-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {submittingPage ? 'Saving...' : unansweredQuestionIdsOnPage.length > 0 ? 'Submit this page' : 'Page complete'}
        </button>

        <button
          type="button"
          onClick={handleNextPage}
          disabled={currentPageIndex >= pages.length - 1 || submittingPage}
          className="px-6 py-2 rounded-full bg-fuchsia-600 text-white font-semibold
                     hover:bg-fuchsia-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          Next page
        </button>
      </div>
    </div>
  );
}

export default SurveyContainer;
