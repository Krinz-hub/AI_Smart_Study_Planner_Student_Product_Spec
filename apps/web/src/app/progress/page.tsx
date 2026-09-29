"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/ui/AppShell";
import { SkeletonCard, SkeletonRow } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/lib/auth-context";
import {
  fetchProgressOverview,
  fetchExams,
  fetchLearnerEvents,
  fetchStudySessions,
  ProgressOverview,
  ExamItem,
  StudySessionRecord,
} from "@/lib/api-client";

export default function ProgressDashboardPage() {
  const { token } = useAuth();

  const {
    data: progress,
    isLoading: isLoadingProgress,
    error: progressError,
    refetch: refetchProgress,
  } = useQuery<ProgressOverview>({
    queryKey: ["progressOverview"],
    queryFn: () => fetchProgressOverview(token!),
    enabled: !!token,
  });

  const { data: exams } = useQuery<ExamItem[]>({
    queryKey: ["exams"],
    queryFn: () => fetchExams(token!),
    enabled: !!token,
  });

  const { data: sessions } = useQuery<StudySessionRecord[]>({
    queryKey: ["studySessions"],
    queryFn: () => fetchStudySessions(token!),
    enabled: !!token,
  });

  const { data: events } = useQuery<any[]>({
    queryKey: ["learnerEvents"],
    queryFn: () => fetchLearnerEvents(token!, 10),
    enabled: !!token,
  });

  const overallMastery = Math.round(progress?.overall_mastery_pct || 0);
  const totalStudyHours = ((progress?.total_study_minutes_completed || 0) / 60).toFixed(1);

  return (
    <AppShell activeNav="progress">
      <div className="max-w-6xl mx-auto space-y-8 animate-fade-in pb-16">
        {/* Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
              Cognitive Mastery & Progress
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Authoritative Bayesian Knowledge Tracing metrics, spaced repetition decay schedules, and verified learning velocity.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/practice"
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md shadow-indigo-500/20"
            >
              ⚡ Take Diagnostic Quiz
            </Link>
          </div>
        </div>

        {isLoadingProgress ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : progressError ? (
          <ErrorState
            title="Failed to Load Progress"
            description="We were unable to retrieve your learning evidence. Please retry."
            onRetry={() => refetchProgress()}
          />
        ) : (
          <>
            {/* Top Stat Metrics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Overall Mastery */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 text-indigo-500 flex items-center justify-center font-extrabold text-xl shadow-inner border border-indigo-500/20">
                  {overallMastery}%
                </div>
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    BKT Mastery Index
                  </span>
                  <div className="text-xl font-extrabold text-slate-900 dark:text-white">
                    {overallMastery >= 75 ? "Proficient" : overallMastery >= 50 ? "Developing" : "Foundational"}
                  </div>
                </div>
              </div>

              {/* Mastered Topics */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-extrabold text-xl shadow-inner border border-emerald-500/20">
                  {progress?.mastered_topics_count || 0}
                </div>
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Mastered Topics
                  </span>
                  <div className="text-xl font-extrabold text-slate-900 dark:text-white">
                    of {progress?.total_topics || 0} Total
                  </div>
                </div>
              </div>

              {/* Study Time */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-purple-500/10 text-purple-500 flex items-center justify-center font-extrabold text-xl shadow-inner border border-purple-500/20">
                  ⏱️
                </div>
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Time Invested
                  </span>
                  <div className="text-xl font-extrabold text-slate-900 dark:text-white">
                    {totalStudyHours} hrs
                  </div>
                </div>
              </div>

              {/* Study Streak */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-amber-500/10 text-amber-500 flex items-center justify-center font-extrabold text-xl shadow-inner border border-amber-500/20">
                  🔥
                </div>
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Study Streak
                  </span>
                  <div className="text-xl font-extrabold text-slate-900 dark:text-white">
                    {progress?.streak_days || 1} Days
                  </div>
                </div>
              </div>
            </div>

            {/* Knowledge Distribution Spectrum */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Developing / In-Progress Topics */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                    <span>In Progress ({progress?.developing_topics?.length || 0})</span>
                  </h3>
                  <span className="text-[10px] text-slate-400 uppercase font-bold">50-80% BKT</span>
                </div>
                <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                  {progress?.developing_topics && progress.developing_topics.length > 0 ? (
                    progress.developing_topics.map((t) => (
                      <Link
                        key={t.id}
                        href={`/subjects/${t.subject_id}/topics/${t.id}`}
                        className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs transition-colors group block"
                      >
                        <span className="font-medium text-slate-800 dark:text-slate-200 group-hover:text-indigo-400 truncate">
                          {t.name}
                        </span>
                        <span className="font-mono font-bold text-amber-500 flex-shrink-0 ml-2">
                          {Math.round(t.mastery_probability * 100)}%
                        </span>
                      </Link>
                    ))
                  ) : (
                    <p className="text-xs text-slate-400 py-4 text-center">
                      No topics currently in intermediate state.
                    </p>
                  )}
                </div>
              </div>

              {/* Needs Review / Attention Topics */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                    <span>Needs Attention ({progress?.needs_attention_topics?.length || 0})</span>
                  </h3>
                  <span className="text-[10px] text-slate-400 uppercase font-bold">&lt; 50% BKT</span>
                </div>
                <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                  {progress?.needs_attention_topics && progress.needs_attention_topics.length > 0 ? (
                    progress.needs_attention_topics.map((t) => (
                      <Link
                        key={t.id}
                        href={`/subjects/${t.subject_id}/topics/${t.id}`}
                        className="p-3 rounded-xl bg-rose-500/5 hover:bg-rose-500/10 border border-rose-500/15 flex items-center justify-between text-xs transition-colors group block"
                      >
                        <span className="font-medium text-slate-800 dark:text-slate-200 group-hover:text-rose-400 truncate">
                          {t.name}
                        </span>
                        <span className="font-mono font-bold text-rose-500 flex-shrink-0 ml-2">
                          {Math.round(t.mastery_probability * 100)}%
                        </span>
                      </Link>
                    ))
                  ) : (
                    <p className="text-xs text-emerald-500 py-4 text-center font-medium">
                      ✓ Zero critical knowledge gaps detected!
                    </p>
                  )}
                </div>
              </div>

              {/* Memory Review Due (FSRS) */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                    <span>FSRS Review Due ({progress?.review_due_topics?.length || 0})</span>
                  </h3>
                  <span className="text-[10px] text-slate-400 uppercase font-bold">Decaying Memory</span>
                </div>
                <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                  {progress?.review_due_topics && progress.review_due_topics.length > 0 ? (
                    progress.review_due_topics.map((t) => (
                      <Link
                        key={t.id}
                        href={`/subjects/${t.subject_id}/topics/${t.id}`}
                        className="p-3 rounded-xl bg-indigo-500/5 hover:bg-indigo-500/10 border border-indigo-500/15 flex items-center justify-between text-xs transition-colors group block"
                      >
                        <span className="font-medium text-slate-800 dark:text-slate-200 group-hover:text-indigo-400 truncate">
                          {t.name}
                        </span>
                        <span className="text-[11px] text-indigo-400 font-semibold flex-shrink-0 ml-2">
                          Review Now →
                        </span>
                      </Link>
                    ))
                  ) : (
                    <p className="text-xs text-slate-400 py-4 text-center">
                      Memory retrievability is optimal across all topics.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Target Exams & Milestones */}
            {exams && exams.length > 0 && (
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
                <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <span>📅</span> Target Exams & Milestones
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {exams.map((ex) => {
                    const daysRemaining = Math.ceil(
                      (new Date(ex.exam_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
                    );
                    return (
                      <div
                        key={ex.id}
                        className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-slate-900 dark:text-white text-sm">
                            {ex.name}
                          </h4>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
                            {daysRemaining > 0 ? `${daysRemaining} days left` : "Today"}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500">
                          Date: {new Date(ex.exam_at).toLocaleDateString()}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Recent Study Activity History */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
              <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>⚡</span> Recent Study Evidence Stream
              </h3>
              {sessions && sessions.length > 0 ? (
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  {sessions.slice(0, 5).map((s) => (
                    <div key={s.id} className="py-3 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-bold text-slate-900 dark:text-white">
                          Study Session Completed
                        </span>
                        <span className="text-slate-500 block text-[11px]">
                          {new Date(s.started_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-slate-600 dark:text-slate-300">
                          {s.actual_minutes} mins
                        </span>
                        <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-500 font-bold text-[10px]">
                          {s.completion_status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 py-3">
                  No completed study sessions recorded yet. Launch your first study session from the Home page!
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
