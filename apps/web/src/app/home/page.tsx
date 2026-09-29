"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles,
  Play,
  CheckCircle2,
  Calendar,
  Flame,
  ArrowRight,
  Clock,
  BookOpen,
  Brain,
  MessageSquare,
  FileText,
  AlertTriangle,
  RotateCcw,
  Zap,
  Target,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  fetchStudentHome,
  fetchSuggestions,
  fetchTasks,
  StudyTask,
  startTask,
} from "@/lib/api-client";
import { AppShell } from "@/components/ui/AppShell";
import { StudySessionModal } from "@/components/ui/StudySessionModal";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useToast } from "@/components/ui/Toast";

export default function StudentHomePage() {
  const { token, user } = useAuth();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [activeSessionTask, setActiveSessionTask] = useState<StudyTask | null>(null);
  const [sessionModalOpen, setSessionModalOpen] = useState(false);

  // Queries
  const {
    data: homeData,
    isLoading: homeLoading,
    isError: homeError,
    refetch: refetchHome,
  } = useQuery({
    queryKey: ["student-home"],
    queryFn: () => fetchStudentHome(token!),
    enabled: !!token,
  });

  const { data: suggestionsData, isLoading: suggLoading } = useQuery({
    queryKey: ["student-suggestions"],
    queryFn: () => fetchSuggestions(token!),
    enabled: !!token,
  });

  const { data: tasksData, isLoading: tasksLoading, refetch: refetchTasks } = useQuery({
    queryKey: ["student-tasks"],
    queryFn: () => fetchTasks(token!),
    enabled: !!token,
  });

  const handleStartTask = async (task: StudyTask) => {
    try {
      if (token) {
        await startTask(token, task.id);
      }
      setActiveSessionTask(task);
      setSessionModalOpen(true);
    } catch (err: any) {
      showToast(err.message || "Failed to start task session", "error");
      setActiveSessionTask(task);
      setSessionModalOpen(true);
    }
  };

  const handleSessionFinished = () => {
    queryClient.invalidateQueries({ queryKey: ["student-home"] });
    queryClient.invalidateQueries({ queryKey: ["student-tasks"] });
    queryClient.invalidateQueries({ queryKey: ["student-progress"] });
    queryClient.invalidateQueries({ queryKey: ["student-suggestions"] });
  };

  const pendingTasks = (tasksData || []).filter((t) => t.status === "PENDING" || t.status === "IN_PROGRESS");
  const topTask = homeData?.top_task;
  const currentTaskObject = topTask
    ? (tasksData || []).find((t) => t.id === topTask.id) || {
        id: topTask.id,
        title: topTask.title,
        subject_id: "",
        topic_id: "",
        objective: "Focus on primary learning outcomes for this session.",
        task_type: topTask.task_type,
        planned_start: topTask.scheduled_start || new Date().toISOString(),
        planned_end: topTask.scheduled_end || new Date().toISOString(),
        duration_minutes: topTask.duration_minutes,
        priority: 0.9,
        status: topTask.status,
        locked: false,
      }
    : null;

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Top Greeting & Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white">
              Hello, {homeData?.student_name || user?.display_name || "Student"} 👋
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              {homeData?.academic_summary || "Curriculum synchronized with official syllabus"}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/plan"
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-850 border border-slate-800 text-xs font-semibold text-slate-300 hover:text-white transition-all"
            >
              <Calendar className="w-3.5 h-3.5" />
              <span>Full Schedule</span>
            </Link>
            <Link
              href="/tutor"
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 text-xs font-semibold text-indigo-300 transition-all"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Ask AI Tutor</span>
            </Link>
          </div>
        </div>

        {homeError ? (
          <ErrorState onRetry={() => refetchHome()} />
        ) : homeLoading ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <CardSkeleton />
            </div>
            <div>
              <CardSkeleton />
            </div>
          </div>
        ) : (
          <>
            {/* "What Should I Study Now?" Hero Recommendation */}
            <div className="p-6 rounded-3xl bg-linear-to-r from-indigo-950/60 via-purple-950/40 to-slate-900 border border-indigo-800/50 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

              <div className="relative flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 uppercase tracking-wide">
                      Top Priority Task
                    </span>
                    {topTask?.task_type && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-800 text-slate-300">
                        {topTask.task_type}
                      </span>
                    )}
                  </div>

                  <h2 className="text-lg sm:text-2xl font-bold text-white leading-tight">
                    {topTask ? topTask.title : "All scheduled tasks for today completed!"}
                  </h2>

                  <p className="text-xs text-slate-300 max-w-xl leading-relaxed">
                    {homeData?.top_task_reason ||
                      "Optimal selection derived from your upcoming exam deadline, forgetting curve risk, and knowledge mastery."}
                  </p>

                  <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
                    <span className="flex items-center gap-1.5 text-slate-300 font-medium">
                      <Clock className="w-3.5 h-3.5 text-indigo-400" />
                      {topTask?.duration_minutes || 45} minutes
                    </span>
                    {topTask?.subject_name && (
                      <span className="flex items-center gap-1.5 text-slate-300 font-medium">
                        <BookOpen className="w-3.5 h-3.5 text-purple-400" />
                        {topTask.subject_name}
                      </span>
                    )}
                  </div>
                </div>

                <div className="shrink-0 flex flex-col sm:flex-row md:flex-col gap-2.5">
                  {currentTaskObject ? (
                    <button
                      onClick={() => handleStartTask(currentTaskObject as StudyTask)}
                      className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl bg-linear-to-r from-indigo-600 to-purple-600 hover:opacity-95 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 cursor-pointer transition-all hover:scale-105"
                    >
                      <Play className="w-4 h-4 fill-white" />
                      <span>Start Study Session</span>
                    </button>
                  ) : (
                    <Link
                      href="/practice"
                      className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl bg-indigo-600 text-white font-bold text-xs"
                    >
                      <Brain className="w-4 h-4" />
                      <span>Practice Quiz</span>
                    </Link>
                  )}
                  <Link
                    href="/plan"
                    className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl text-slate-300 hover:text-white text-xs font-medium hover:bg-slate-800/60 transition-colors"
                  >
                    <span>View upcoming tasks</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </div>

            {/* Quick Metrics Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-1">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Today&apos;s Study</span>
                  <Clock className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="text-xl font-bold text-white">
                  {homeData?.today_completed_minutes || 0} / {homeData?.today_target_minutes || 180}m
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden mt-2">
                  <div
                    className="h-full bg-indigo-500 rounded-full transition-all"
                    style={{
                      width: `${Math.min(
                        100,
                        ((homeData?.today_completed_minutes || 0) /
                          Math.max(1, homeData?.today_target_minutes || 180)) *
                          100
                      )}%`,
                    }}
                  />
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-1">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Tasks Completed</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-xl font-bold text-emerald-400">
                  {homeData?.tasks_completed_today || 0}
                  <span className="text-xs text-slate-400 font-normal">
                    {" "}
                    / {homeData?.tasks_total_today || 0} today
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Constraint scheduler active</div>
              </div>

              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-1">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Curriculum Mastery</span>
                  <Brain className="w-4 h-4 text-purple-400" />
                </div>
                <div className="text-xl font-bold text-white">
                  {homeData?.overall_mastery_pct || 0}%
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Across {homeData?.subjects_count || 0} enrolled courses
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-1">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Current Streak</span>
                  <Flame className="w-4 h-4 text-amber-500 fill-amber-500" />
                </div>
                <div className="text-xl font-bold text-amber-400">
                  {homeData?.streak_days || 1} Days
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Consistent daily progress</div>
              </div>
            </div>

            {/* Split Section: Today's Tasks & Explainable Suggestions */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left 2 Cols: Today's Tasks Agenda */}
              <div className="lg:col-span-2 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white">Today&apos;s Study Agenda</h3>
                  <Link href="/plan" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium">
                    View Week
                  </Link>
                </div>

                {tasksLoading ? (
                  <div className="space-y-2">
                    <CardSkeleton />
                    <CardSkeleton />
                  </div>
                ) : pendingTasks.length === 0 ? (
                  <EmptyState
                    icon={CheckCircle2}
                    title="No pending tasks for today"
                    description="You are completely caught up! Take a diagnostic quiz or explore new topics."
                    actionLabel="Take Practice Quiz"
                    onAction={() => (window.location.href = "/practice")}
                  />
                ) : (
                  <div className="space-y-2.5">
                    {pendingTasks.slice(0, 4).map((task) => (
                      <div
                        key={task.id}
                        className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/80 hover:border-slate-700 transition-all flex items-center justify-between gap-4"
                      >
                        <div className="space-y-1 flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-indigo-950 text-indigo-300 border border-indigo-800/40 uppercase">
                              {task.task_type}
                            </span>
                            <span className="text-xs font-semibold text-white truncate">{task.title}</span>
                          </div>
                          <div className="flex items-center gap-3 text-[11px] text-slate-400">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3 text-slate-500" />
                              {task.duration_minutes}m
                            </span>
                            <span className="font-mono text-indigo-400">
                              Priority: {(Number(task.priority) * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>

                        <button
                          onClick={() => handleStartTask(task)}
                          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition-all cursor-pointer shrink-0"
                        >
                          <Play className="w-3.5 h-3.5 fill-indigo-300" />
                          <span>Start</span>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right Col: Explainable Next Suggestions */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white">Why This Next?</h3>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/40">
                    Decision Engine
                  </span>
                </div>

                {suggLoading ? (
                  <CardSkeleton />
                ) : (suggestionsData?.suggestions || []).length === 0 ? (
                  <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800 text-xs text-slate-400 text-center">
                    No active gap alerts. Knowledge model is stable.
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {(suggestionsData?.suggestions || []).slice(0, 3).map((sugg) => (
                      <div
                        key={sugg.id}
                        className="p-3.5 rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-white truncate">{sugg.title}</span>
                          <span className="text-[10px] font-mono text-amber-400 bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-800/40">
                            {sugg.action_type}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-snug">{sugg.reason}</p>
                        <div className="pt-1 flex justify-end">
                          <Link
                            href="/practice"
                            className="text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1"
                          >
                            <span>Act Now</span>
                            <ArrowRight className="w-3 h-3" />
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Quick Shortcut Launchers */}
                <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
                  <div className="text-xs font-bold text-slate-300">Quick Tools</div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <Link
                      href="/tutor"
                      className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 flex items-center gap-2 text-slate-300 hover:text-white transition-colors"
                    >
                      <MessageSquare className="w-4 h-4 text-purple-400" />
                      <span>AI Tutor</span>
                    </Link>
                    <Link
                      href="/materials"
                      className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 flex items-center gap-2 text-slate-300 hover:text-white transition-colors"
                    >
                      <FileText className="w-4 h-4 text-emerald-400" />
                      <span>Upload Notes</span>
                    </Link>
                    <Link
                      href="/practice"
                      className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 flex items-center gap-2 text-slate-300 hover:text-white transition-colors"
                    >
                      <Brain className="w-4 h-4 text-indigo-400" />
                      <span>Quiz Center</span>
                    </Link>
                    <Link
                      href="/progress"
                      className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 flex items-center gap-2 text-slate-300 hover:text-white transition-colors"
                    >
                      <Target className="w-4 h-4 text-sky-400" />
                      <span>Analytics</span>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Focus Study Session Modal */}
      <StudySessionModal
        token={token!}
        task={activeSessionTask}
        isOpen={sessionModalOpen}
        onClose={() => setSessionModalOpen(false)}
        onCompleted={handleSessionFinished}
      />
    </AppShell>
  );
}
