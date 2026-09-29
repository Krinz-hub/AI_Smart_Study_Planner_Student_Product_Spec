"use client";

import React, { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/ui/AppShell";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import {
  fetchSubjects,
  fetchTopic,
  fetchLearnerState,
  recordTopicConfidence,
  generateTopicQuiz,
  SubjectItem,
  TopicItem,
} from "@/lib/api-client";

interface PageProps {
  params: Promise<{ subjectId: string; topicId: string }>;
}

export default function TopicIntelligencePage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { subjectId, topicId } = resolvedParams;
  const { token } = useAuth();
  const router = useRouter();
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const [selfRating, setSelfRating] = useState<number>(4);
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState<boolean>(false);

  // Subject Info
  const { data: subjects } = useQuery<SubjectItem[]>({
    queryKey: ["subjects"],
    queryFn: () => fetchSubjects(token!),
    enabled: !!token,
  });
  const subject = subjects?.find((s) => s.id === subjectId);

  // Topic Info
  const {
    data: topic,
    isLoading: isLoadingTopic,
    error: topicError,
  } = useQuery<TopicItem>({
    queryKey: ["topic", topicId],
    queryFn: () => fetchTopic(token!, topicId),
    enabled: !!token && !!topicId,
  });

  // Learner State
  const { data: learnerState } = useQuery({
    queryKey: ["learnerState"],
    queryFn: () => fetchLearnerState(token!),
    enabled: !!token,
  });

  // Extract BKT & FSRS models for this topic if present
  const topicMastery = learnerState?.topic_mastery?.[topicId] || null;
  const topicMemory = learnerState?.topic_memory?.[topicId] || null;
  const topicConfidence = learnerState?.topic_confidence?.[topicId] || null;

  // Confidence mutation
  const confidenceMutation = useMutation({
    mutationFn: (rating: number) =>
      recordTopicConfidence(token!, topicId, rating / 5.0),
    onSuccess: () => {
      addToast("Confidence calibration updated successfully", "success");
      queryClient.invalidateQueries({ queryKey: ["learnerState"] });
    },
    onError: (err: any) => {
      addToast(err?.message || "Failed to update confidence", "error");
    },
  });

  const handleLaunchQuiz = async () => {
    try {
      setIsGeneratingQuiz(true);
      const quiz = await generateTopicQuiz(token!, topicId, 5, "MEDIUM");
      const targetQuizId = quiz.id || quiz.quiz_id;
      if (!targetQuizId) {
        throw new Error("Quiz generated but missing identifier");
      }
      addToast("Practice quiz generated!", "success");
      router.push(`/practice/${targetQuizId}`);
    } catch (err: any) {
      addToast(err?.message || "Failed to generate practice quiz", "error");
    } finally {
      setIsGeneratingQuiz(false);
    }
  };

  const masteryProb = topicMastery?.mastery_probability ?? 0.5;
  const masteryPct = Math.round(masteryProb * 100);
  const stateLabel = topicMastery?.state || "INITIAL_STATE";

  return (
    <AppShell activeNav="subjects">
      <div className="max-w-5xl mx-auto space-y-8 animate-fade-in">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
          <Link href="/subjects" className="hover:text-indigo-400 transition-colors">
            Subjects
          </Link>
          <span>/</span>
          <Link
            href={`/subjects/${subjectId}`}
            className="hover:text-indigo-400 transition-colors"
          >
            {subject?.name || "Subject"}
          </Link>
          <span>/</span>
          <span className="text-slate-900 dark:text-slate-200 font-semibold">
            {topic?.name || "Topic Intelligence"}
          </span>
        </div>

        {isLoadingTopic ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : topicError ? (
          <ErrorState
            title="Topic Not Found"
            description="Could not load the topic profile from your curriculum."
          />
        ) : (
          <>
            {/* Top Title & Quick Actions */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2.5">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: subject?.color || "#6366f1" }}
                  />
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-500">
                    {subject?.name || "Curriculum Unit"}
                  </span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
                  {topic?.name}
                </h1>
                <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-xl">
                  Deep intelligence modeling using Bayesian Knowledge Tracing (BKT) and Free Spaced Repetition Scheduling (FSRS).
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={handleLaunchQuiz}
                  disabled={isGeneratingQuiz}
                  className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md shadow-indigo-500/20 disabled:opacity-50 inline-flex items-center gap-2"
                >
                  {isGeneratingQuiz ? (
                    <>
                      <span className="animate-spin text-sm">⌛</span> Generating...
                    </>
                  ) : (
                    <>
                      <span>⚡</span> Launch Practice Quiz
                    </>
                  )}
                </button>
                <Link
                  href={`/tutor`}
                  className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold transition-all inline-flex items-center gap-2"
                >
                  <span>🤖</span> Ask Socratic AI
                </Link>
              </div>
            </div>

            {/* Twin Pillar Cards: BKT Mastery & FSRS Memory Retention */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Bayesian Knowledge Tracing (BKT) */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">🧠</span>
                    <h2 className="font-bold text-slate-900 dark:text-white">
                      BKT Mastery State
                    </h2>
                  </div>
                  <span
                    className={`text-xs font-bold px-2.5 py-1 rounded-full uppercase ${
                      masteryPct >= 80
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : masteryPct >= 50
                        ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                    }`}
                  >
                    {stateLabel}
                  </span>
                </div>

                <div className="space-y-2">
                  <div className="flex items-end justify-between">
                    <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
                      {masteryPct}%
                    </span>
                    <span className="text-xs text-slate-500 font-mono">
                      P(L_t) = {masteryProb.toFixed(3)}
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-indigo-600 h-3 rounded-full transition-all duration-700"
                      style={{ width: `${Math.max(5, masteryPct)}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 pt-1">
                    Continuous probabilistic inference computed from diagnostic responses, active recall, and verified problem sets.
                  </p>
                </div>

                <div className="pt-4 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Uncertainty Bound</span>
                    <span className="text-slate-700 dark:text-slate-200 font-semibold font-mono">
                      ±{(0.15).toFixed(2)} σ
                    </span>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Slip / Guess Factor</span>
                    <span className="text-slate-700 dark:text-slate-200 font-semibold font-mono">
                      s: 0.10 | g: 0.20
                    </span>
                  </div>
                </div>
              </div>

              {/* FSRS Memory Model */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">⏳</span>
                    <h2 className="font-bold text-slate-900 dark:text-white">
                      FSRS Memory Stability
                    </h2>
                  </div>
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    Spaced Decay
                  </span>
                </div>

                <div className="space-y-2">
                  <div className="flex items-end justify-between">
                    <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
                      {topicMemory ? `${Math.round(topicMemory.retrievability * 100)}%` : "95%"}
                    </span>
                    <span className="text-xs text-slate-500">
                      Estimated Retrievability
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-emerald-500 h-3 rounded-full transition-all duration-700"
                      style={{
                        width: `${Math.round((topicMemory?.retrievability ?? 0.95) * 100)}%`,
                      }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 pt-1">
                    Next recommended revision session:{" "}
                    <strong className="text-slate-800 dark:text-slate-200">
                      {topicMemory?.next_review_at
                        ? new Date(topicMemory.next_review_at).toLocaleDateString()
                        : "Within 3 days"}
                    </strong>
                  </p>
                </div>

                <div className="pt-4 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Memory Half-Life</span>
                    <span className="text-slate-700 dark:text-slate-200 font-semibold font-mono">
                      {topicMemory?.stability ? `${topicMemory.stability.toFixed(1)} days` : "4.2 days"}
                    </span>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Difficulty Index</span>
                    <span className="text-slate-700 dark:text-slate-200 font-semibold font-mono">
                      {topicMemory?.difficulty ? topicMemory.difficulty.toFixed(1) : "5.0"} / 10
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Metacognitive Self-Calibration */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>🎯</span> Metacognitive Self-Assessment
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    How confident do you feel solving exam-level problems for this topic?
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {[1, 2, 3, 4, 5].map((lvl) => (
                    <button
                      key={lvl}
                      onClick={() => {
                        setSelfRating(lvl);
                        confidenceMutation.mutate(lvl);
                      }}
                      className={`w-9 h-9 rounded-xl font-bold text-xs transition-all ${
                        selfRating === lvl
                          ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/30 scale-105"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                      }`}
                    >
                      {lvl}★
                    </button>
                  ))}
                </div>
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-100 dark:border-slate-800">
                💡 <strong>Dunning-Kruger Alignment:</strong> If your self-confidence is high (5★) but quiz accuracy drops below 60%, the adaptive planner automatically flags this as an uncalibrated illusion of competence and schedules targeted verification quizzes.
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
