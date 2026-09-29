"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/ui/AppShell";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/lib/auth-context";
import { fetchSubjects, fetchProgressOverview, SubjectItem, ProgressOverview } from "@/lib/api-client";

export default function SubjectsPage() {
  const { token } = useAuth();
  const [searchFilter, setSearchFilter] = useState("");

  const {
    data: subjects,
    isLoading: isLoadingSubjects,
    error: subjectsError,
    refetch: refetchSubjects,
  } = useQuery<SubjectItem[]>({
    queryKey: ["subjects"],
    queryFn: () => fetchSubjects(token!),
    enabled: !!token,
  });

  const { data: progress } = useQuery<ProgressOverview>({
    queryKey: ["progressOverview"],
    queryFn: () => fetchProgressOverview(token!),
    enabled: !!token,
  });

  const filteredSubjects = (subjects || []).filter((s) =>
    s.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
    (s.code && s.code.toLowerCase().includes(searchFilter.toLowerCase()))
  );

  return (
    <AppShell activeNav="subjects">
      <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              Course Subjects
            </h1>
            <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
              Your registered curriculum and personalized mastery tracking per domain.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/onboarding"
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors shadow-sm"
            >
              <span>⚙️</span> Discover New Syllabus
            </Link>
          </div>
        </div>

        {/* Global Progress Bar Barometer */}
        {progress && (
          <div className="bg-gradient-to-r from-indigo-900/40 via-purple-900/30 to-slate-900/40 border border-indigo-500/20 rounded-2xl p-5 backdrop-blur-md">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">Curriculum Health</span>
                <h3 className="text-lg font-bold text-white">Overall Mastery: {Math.round(progress.overall_mastery_pct)}%</h3>
              </div>
              <div className="flex items-center gap-4 text-xs font-medium text-slate-300">
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> {progress.mastered_topics_count} Mastered</span>
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> {progress.developing_topics?.length || 0} In Progress</span>
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> {progress.needs_attention_topics?.length || 0} Needs Review</span>
              </div>
            </div>
            <div className="w-full bg-slate-800/80 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400 h-2.5 rounded-full transition-all duration-700"
                style={{ width: `${Math.min(100, Math.max(5, progress.overall_mastery_pct))}%` }}
              />
            </div>
          </div>
        )}

        {/* Search & Filter Toolbar */}
        <div className="flex items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              🔍
            </span>
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Filter by subject name or code..."
              className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
          </div>
          <span className="text-xs text-slate-500 font-medium">
            Showing {filteredSubjects.length} of {subjects?.length || 0} subjects
          </span>
        </div>

        {/* Subjects List State */}
        {isLoadingSubjects ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : subjectsError ? (
          <ErrorState
            title="Failed to Load Subjects"
            description="We encountered an issue fetching your curriculum. Please check your connection."
            onRetry={() => refetchSubjects()}
          />
        ) : filteredSubjects.length === 0 ? (
          <EmptyState
            title="No Subjects Found"
            description={
              searchFilter
                ? `No courses match your filter query "${searchFilter}".`
                : "You haven't added or confirmed any subjects yet. Complete syllabus discovery to populate your courses."
            }
            actionLabel="Discover Syllabus"
            actionHref="/onboarding"
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredSubjects.map((sub) => {
              const accentColor = sub.color || "#6366f1";
              return (
                <div
                  key={sub.id}
                  className="group relative bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 rounded-2xl p-6 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between"
                >
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-3.5 h-3.5 rounded-full ring-4 ring-slate-100 dark:ring-slate-800"
                          style={{ backgroundColor: accentColor }}
                        />
                        {sub.code && (
                          <span className="text-xs font-mono font-semibold uppercase px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                            {sub.code}
                          </span>
                        )}
                      </div>
                      <span className="text-xs font-semibold text-slate-400 group-hover:text-indigo-400 transition-colors">
                        Active Curriculum
                      </span>
                    </div>

                    <div>
                      <h3 className="text-xl font-bold text-slate-900 dark:text-white group-hover:text-indigo-400 transition-colors line-clamp-1">
                        {sub.name}
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Full course modules and knowledge graph breakdown.
                      </p>
                    </div>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between gap-2">
                    <Link
                      href={`/subjects/${sub.id}`}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-3.5 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white transition-all shadow-sm shadow-indigo-500/20"
                    >
                      <span>Explore Topics</span> <span>→</span>
                    </Link>
                    <Link
                      href={`/tutor`}
                      className="inline-flex items-center justify-center p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors"
                      title="Ask Tutor about this subject"
                    >
                      🤖
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
