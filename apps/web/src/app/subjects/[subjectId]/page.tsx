"use client";

import React, { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/ui/AppShell";
import { SkeletonCard, SkeletonRow } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/lib/auth-context";
import {
  fetchSubjects,
  fetchTopics,
  fetchProgressOverview,
  SubjectItem,
  TopicItem,
  ProgressOverview,
} from "@/lib/api-client";

interface PageProps {
  params: Promise<{ subjectId: string }>;
}

export default function SubjectDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const subjectId = resolvedParams.subjectId;
  const { token } = useAuth();

  const { data: subjects } = useQuery<SubjectItem[]>({
    queryKey: ["subjects"],
    queryFn: () => fetchSubjects(token!),
    enabled: !!token,
  });

  const subject = subjects?.find((s) => s.id === subjectId);

  const {
    data: topics,
    isLoading: isLoadingTopics,
    error: topicsError,
    refetch: refetchTopics,
  } = useQuery<TopicItem[]>({
    queryKey: ["topics", subjectId],
    queryFn: () => fetchTopics(token!, subjectId),
    enabled: !!token && !!subjectId,
  });

  const { data: progress } = useQuery<ProgressOverview>({
    queryKey: ["progressOverview"],
    queryFn: () => fetchProgressOverview(token!),
    enabled: !!token,
  });

  // Map topic id to mastery overview if available
  const masteryMap = new Map<string, { state: string; probability: number }>();
  if (progress) {
    [
      ...(progress.strong_topics || []),
      ...(progress.developing_topics || []),
      ...(progress.needs_attention_topics || []),
      ...(progress.review_due_topics || []),
    ].forEach((t) => {
      masteryMap.set(t.id, {
        state: t.state,
        probability: t.mastery_probability,
      });
    });
  }

  const getStatusBadge = (topicId: string) => {
    const m = masteryMap.get(topicId);
    if (!m) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-500">
          Untested
        </span>
      );
    }
    if (m.state === "MASTERED" || m.probability >= 0.85) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          Mastered ({Math.round(m.probability * 100)}%)
        </span>
      );
    }
    if (m.state === "LEARNING" || m.probability >= 0.5) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
          Developing ({Math.round(m.probability * 100)}%)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
        Needs Attention ({Math.round(m.probability * 100)}%)
      </span>
    );
  };

  return (
    <AppShell activeNav="subjects">
      <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
          <Link href="/subjects" className="hover:text-indigo-400 transition-colors">
            Subjects
          </Link>
          <span>/</span>
          <span className="text-slate-900 dark:text-slate-200 font-semibold">
            {subject?.name || "Course Details"}
          </span>
        </div>

        {/* Course Header Banner */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span
                  className="w-4 h-4 rounded-full ring-4 ring-slate-100 dark:ring-slate-800"
                  style={{ backgroundColor: subject?.color || "#6366f1" }}
                />
                {subject?.code && (
                  <span className="text-xs font-mono font-bold uppercase px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                    {subject.code}
                  </span>
                )}
                <span className="text-xs font-medium text-slate-400">
                  {topics?.length || 0} Modules Registered
                </span>
              </div>
              <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
                {subject?.name || "Subject Curriculum"}
              </h1>
              <p className="text-sm text-slate-600 dark:text-slate-400 max-w-2xl">
                Breakdown of units and conceptual milestones. Select any topic to inspect Bayesian Knowledge Tracing mastery and FSRS memory stability.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Link
                href={`/practice`}
                className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md shadow-indigo-500/20"
              >
                ⚡ Practice Quiz
              </Link>
              <Link
                href={`/tutor`}
                className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold transition-all"
              >
                🤖 Socratic Tutor
              </Link>
            </div>
          </div>
        </div>

        {/* Topics List Table / Grid */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Syllabus Topics & Competencies
            </h2>
            <span className="text-xs text-slate-500 font-medium">
              Sorted by curricular progression
            </span>
          </div>

          {isLoadingTopics ? (
            <div className="space-y-3">
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </div>
          ) : topicsError ? (
            <ErrorState
              title="Unable to load topics"
              description="Failed to retrieve topics for this course. Please verify your connection."
              onRetry={() => refetchTopics()}
            />
          ) : !topics || topics.length === 0 ? (
            <EmptyState
              title="No topics listed yet"
              description="This subject does not currently have topics registered. Run syllabus discovery or add topics manually."
              actionLabel="Return to Subjects"
              actionHref="/subjects"
            />
          ) : (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden divide-y divide-slate-100 dark:divide-slate-800">
              {topics.map((t, idx) => (
                <div
                  key={t.id}
                  className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <span className="flex-shrink-0 w-8 h-8 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-xs font-bold flex items-center justify-center">
                      {idx + 1}
                    </span>
                    <div>
                      <div className="flex items-center gap-3">
                        <Link
                          href={`/subjects/${subjectId}/topics/${t.id}`}
                          className="font-bold text-slate-900 dark:text-white hover:text-indigo-500 transition-colors text-base"
                        >
                          {t.name}
                        </Link>
                        {getStatusBadge(t.id)}
                      </div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Syllabus Weight: {t.syllabus_weight ? `${Math.round(t.syllabus_weight * 100)}%` : "Standard"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <Link
                      href={`/subjects/${subjectId}/topics/${t.id}`}
                      className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold transition-colors"
                    >
                      Inspect Intelligence →
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
