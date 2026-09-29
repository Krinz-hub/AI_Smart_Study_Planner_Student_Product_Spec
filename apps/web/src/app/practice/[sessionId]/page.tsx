"use client";

import React, { use, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/ui/AppShell";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import {
  startQuizSession,
  submitQuizAnswers,
  fetchQuizResults,
  QuizDetail,
  QuizResultDetail,
} from "@/lib/api-client";

interface PageProps {
  params: Promise<{ sessionId: string }>;
}

export default function QuizRunnerPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const quizId = resolvedParams.sessionId;
  const { token } = useAuth();
  const router = useRouter();
  const { addToast } = useToast();

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [quizData, setQuizData] = useState<QuizDetail | null>(null);
  const [results, setResults] = useState<QuizResultDetail | null>(null);
  const [currentIdx, setCurrentIdx] = useState<number>(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;

    if (!quizId || quizId === "undefined" || quizId === "null") {
      setErrorMsg("Invalid quiz session ID. Please launch a quiz from the Practice Hub.");
      setIsLoading(false);
      return;
    }

    let mounted = true;
    const initQuiz = async () => {
      try {
        setIsLoading(true);
        // First check if quiz is already completed
        try {
          const res = await fetchQuizResults(token, quizId);
          if (mounted && res && res.answers && res.answers.length > 0) {
            setResults(res);
            setIsLoading(false);
            return;
          }
        } catch {
          // If not completed or 404, start/load session
        }

        const session = await startQuizSession(token, quizId);
        if (mounted) {
          setQuizData(session);
        }
      } catch (err: any) {
        if (mounted) setErrorMsg(err?.message || "Failed to load quiz session");
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    initQuiz();
    return () => {
      mounted = false;
    };
  }, [token, quizId]);

  const questions = quizData?.questions || [];
  const currentQuestion = questions[currentIdx] || null;

  const handleSelectOption = (key: string) => {
    if (!currentQuestion) return;
    setSelectedAnswers((prev) => ({
      ...prev,
      [currentQuestion.id]: key,
    }));
  };

  const handleSubmitQuiz = async () => {
    if (!quizData || !token) return;

    // Check if all questions have answers
    const unansweredCount = questions.length - Object.keys(selectedAnswers).length;
    if (unansweredCount > 0) {
      const confirmSubmit = window.confirm(
        `You have ${unansweredCount} unanswered questions. Submit anyway?`
      );
      if (!confirmSubmit) return;
    }

    try {
      setIsSubmitting(true);
      const answersPayload = questions.map((q) => ({
        question_id: q.id,
        selected_key: selectedAnswers[q.id] || "UNANSWERED",
        response_time_seconds: 15,
      }));

      const res = await submitQuizAnswers(token, quizId, answersPayload);
      setResults(res);
      addToast("Quiz evaluated! BKT & FSRS models updated.", "success");
    } catch (err: any) {
      addToast(err?.message || "Failed to submit quiz", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <AppShell activeNav="practice">
        <div className="max-w-3xl mx-auto py-12 space-y-6">
          <SkeletonCard />
        </div>
      </AppShell>
    );
  }

  if (errorMsg) {
    const isInvalidId = !quizId || quizId === "undefined" || quizId === "null";
    return (
      <AppShell activeNav="practice">
        <div className="max-w-2xl mx-auto py-12 space-y-6">
          <ErrorState
            title="Quiz Session Error"
            description={errorMsg}
            onRetry={() => {
              if (isInvalidId) {
                router.push("/practice");
              } else {
                window.location.reload();
              }
            }}
          />
          <div className="flex justify-center">
            <Link
              href="/practice"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm transition-colors shadow-sm"
            >
              ← Back to Practice Hub
            </Link>
          </div>
        </div>
      </AppShell>
    );
  }

  // --- RESULTS VIEW ---
  if (results) {
    const accuracy = Math.round(results.accuracy_pct || 0);
    const isPassing = accuracy >= 70;

    return (
      <AppShell activeNav="practice">
        <div className="max-w-4xl mx-auto space-y-8 animate-fade-in pb-12">
          {/* Header Score Banner */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-500">
                  Assessment Complete
                </span>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
                  Diagnostic Performance Report
                </h1>
                <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                  Your answers have been ingested into the student knowledge model to adapt your upcoming study schedule.
                </p>
              </div>

              <div className="flex items-center gap-4 bg-slate-50 dark:bg-slate-800/80 p-4 rounded-2xl border border-slate-100 dark:border-slate-700/60">
                <div
                  className={`w-16 h-16 rounded-2xl flex flex-col items-center justify-center font-extrabold text-xl shadow-inner ${
                    isPassing
                      ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                      : "bg-rose-500/10 text-rose-500 border border-rose-500/20"
                  }`}
                >
                  <span>{accuracy}%</span>
                  <span className="text-[9px] uppercase tracking-wider font-bold">Accuracy</span>
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-900 dark:text-white">
                    {results.correct_count} of {results.total_questions} Correct
                  </div>
                  <div className="text-xs text-slate-500">
                    {isPassing ? "Mastery Reinforced" : "Review Recommended"}
                  </div>
                </div>
              </div>
            </div>

            {/* Weak Concepts Warning if any */}
            {results.weak_concepts && results.weak_concepts.length > 0 && (
              <div className="mt-6 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 space-y-1">
                <span className="text-xs font-bold text-amber-500 flex items-center gap-1.5">
                  <span>⚠️</span> Identified Knowledge Gaps:
                </span>
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  The planner detected confusion in:{" "}
                  <strong>{results.weak_concepts.join(", ")}</strong>. Recovery study tasks have been scheduled.
                </p>
              </div>
            )}
          </div>

          {/* Itemized Questions Review */}
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Question-by-Question Pedagogical Review
            </h2>

            <div className="space-y-4">
              {results.answers?.map((ans, idx) => {
                const questionObj = questions.find((q) => q.id === ans.question_id);
                return (
                  <div
                    key={ans.question_id || idx}
                    className={`bg-white dark:bg-slate-900 border rounded-2xl p-6 shadow-sm space-y-4 ${
                      ans.is_correct
                        ? "border-emerald-500/30"
                        : "border-rose-500/30"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <span className="text-xs font-bold text-slate-400">
                        Question {idx + 1}
                      </span>
                      <span
                        className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                          ans.is_correct
                            ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                            : "bg-rose-500/10 text-rose-500 border border-rose-500/20"
                        }`}
                      >
                        {ans.is_correct ? "✓ Correct" : "✗ Incorrect"}
                      </span>
                    </div>

                    <p className="text-sm font-semibold text-slate-900 dark:text-white">
                      {questionObj?.question_text || `Question item`}
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                        <span className="text-slate-400 block text-[10px] uppercase font-bold">Your Response</span>
                        <span className={`font-semibold ${ans.is_correct ? "text-emerald-500" : "text-rose-500"}`}>
                          Key: {ans.selected_key}
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                        <span className="text-slate-400 block text-[10px] uppercase font-bold">Correct Solution</span>
                        <span className="font-semibold text-emerald-500">
                          Key: {ans.correct_key}
                        </span>
                      </div>
                    </div>

                    {ans.explanation && (
                      <div className="p-3.5 rounded-xl bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/30 text-xs text-slate-700 dark:text-slate-300">
                        <strong className="text-indigo-600 dark:text-indigo-400 block mb-1">
                          Pedagogical Explanation:
                        </strong>
                        {ans.explanation}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-slate-200 dark:border-slate-800">
            <Link
              href="/practice"
              className="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold transition-all"
            >
              ← Back to Practice Hub
            </Link>
            <div className="flex items-center gap-3">
              <Link
                href="/tutor"
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md shadow-indigo-500/20"
              >
                Ask AI Tutor About Mistakes →
              </Link>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  // --- ACTIVE RUNNER VIEW ---
  if (!currentQuestion) {
    return (
      <AppShell activeNav="practice">
        <div className="max-w-2xl mx-auto py-12 text-center space-y-4">
          <p className="text-slate-500">No questions available in this session.</p>
          <Link
            href="/practice"
            className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-bold"
          >
            Return to Practice
          </Link>
        </div>
      </AppShell>
    );
  }

  const selectedKey = selectedAnswers[currentQuestion.id] || "";
  const progressPct = Math.round(((currentIdx + 1) / questions.length) * 100);

  return (
    <AppShell activeNav="practice">
      <div className="max-w-3xl mx-auto space-y-6 animate-fade-in pb-12">
        {/* Progress & Top Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-slate-500">
            <span>
              Question <strong className="text-slate-900 dark:text-white">{currentIdx + 1}</strong> of{" "}
              {questions.length}
            </span>
            <span className="font-mono">{progressPct}% Complete</span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Question Card */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold uppercase px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
              {currentQuestion.difficulty || "MEDIUM"}
            </span>
            <span className="text-xs text-slate-400 font-medium">
              Single Choice
            </span>
          </div>

          <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white leading-relaxed">
            {currentQuestion.question_text}
          </h2>

          {/* Options */}
          <div className="space-y-3 pt-2">
            {currentQuestion.options?.map((opt) => {
              const isSelected = selectedKey === opt.key;
              return (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => handleSelectOption(opt.key)}
                  className={`w-full p-4 rounded-2xl text-left border transition-all flex items-center gap-4 ${
                    isSelected
                      ? "bg-indigo-50/80 dark:bg-indigo-950/40 border-indigo-500 text-slate-900 dark:text-white shadow-sm ring-1 ring-indigo-500"
                      : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                  }`}
                >
                  <span
                    className={`w-8 h-8 rounded-xl font-bold text-xs flex items-center justify-center flex-shrink-0 transition-colors ${
                      isSelected
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
                    }`}
                  >
                    {opt.key}
                  </span>
                  <span className="text-sm font-medium flex-1">{opt.text}</span>
                </button>
              );
            })}
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center justify-between pt-6 border-t border-slate-100 dark:border-slate-800">
            <button
              disabled={currentIdx === 0}
              onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
              className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-bold transition-all disabled:opacity-40"
            >
              ← Previous
            </button>

            {currentIdx < questions.length - 1 ? (
              <button
                onClick={() => setCurrentIdx((i) => Math.min(questions.length - 1, i + 1))}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md shadow-indigo-500/20"
              >
                Next Question →
              </button>
            ) : (
              <button
                disabled={isSubmitting}
                onClick={handleSubmitQuiz}
                className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50 inline-flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <span className="animate-spin text-sm">⌛</span> Evaluating...
                  </>
                ) : (
                  <>
                    <span>✓</span> Submit Assessment
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
