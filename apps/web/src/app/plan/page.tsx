"use client";

import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Calendar as CalendarIcon,
  Sparkles,
  Lock,
  Unlock,
  Play,
  CheckCircle2,
  Clock,
  RotateCcw,
  AlertCircle,
  Filter,
  Flame,
  ChevronRight,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  fetchTasks,
  lockTask,
  skipTask,
  startTask,
  rescheduleTask,
  replanStudySchedule,
  generateStudyPlan,
  StudyTask,
} from "@/lib/api-client";
import { AppShell } from "@/components/ui/AppShell";
import { StudySessionModal } from "@/components/ui/StudySessionModal";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useToast } from "@/components/ui/Toast";

export default function StudyPlanPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [activeSessionTask, setActiveSessionTask] = useState<StudyTask | null>(null);
  const [sessionModalOpen, setSessionModalOpen] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [isReplanning, setIsReplanning] = useState(false);

  // Reschedule state
  const [rescheduleTaskId, setRescheduleTaskId] = useState<string | null>(null);
  const [rescheduleDate, setRescheduleDate] = useState<string>("");

  const {
    data: tasks = [],
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["student-tasks"],
    queryFn: () => fetchTasks(token!),
    enabled: !!token,
  });

  const handleLockToggle = async (task: StudyTask) => {
    setActionLoadingId(task.id);
    try {
      await lockTask(token!, task.id, !task.locked);
      showToast(task.locked ? "Task unlocked" : "Task locked. Schedule will preserve it.", "info");
      queryClient.invalidateQueries({ queryKey: ["student-tasks"] });
    } catch (err: any) {
      showToast(err.message || "Failed to update lock state", "error");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleSkip = async (task: StudyTask) => {
    if (!confirm(`Skip "${task.title}"? Your knowledge state will NOT be degraded.`)) return;
    setActionLoadingId(task.id);
    try {
      await skipTask(token!, task.id, "deferred_by_user");
      showToast("Task skipped safely without degrading mastery.", "info");
      queryClient.invalidateQueries({ queryKey: ["student-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["student-home"] });
    } catch (err: any) {
      showToast(err.message || "Failed to skip task", "error");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleStartTask = async (task: StudyTask) => {
    try {
      if (token) {
        await startTask(token, task.id);
      }
      setActiveSessionTask(task);
      setSessionModalOpen(true);
    } catch (err: any) {
      setActiveSessionTask(task);
      setSessionModalOpen(true);
    }
  };

  const handleRescheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rescheduleTaskId || !rescheduleDate) return;
    setActionLoadingId(rescheduleTaskId);
    try {
      const isoStart = new Date(rescheduleDate).toISOString();
      await rescheduleTask(token!, rescheduleTaskId, isoStart);
      showToast("Task successfully rescheduled", "success");
      setRescheduleTaskId(null);
      queryClient.invalidateQueries({ queryKey: ["student-tasks"] });
    } catch (err: any) {
      showToast(err.message || "Failed to reschedule task", "error");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleReplan = async () => {
    setIsReplanning(true);
    try {
      await replanStudySchedule(token!, "active", "MANUAL_REBALANCE", 180);
      showToast("Schedule rebalanced with constraint satisfaction!", "success");
      queryClient.invalidateQueries({ queryKey: ["student-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["student-home"] });
    } catch (err: any) {
      showToast(err.message || "Replanning failed", "error");
    } finally {
      setIsReplanning(false);
    }
  };

  const handleGenerateInitialPlan = async () => {
    setIsReplanning(true);
    try {
      await generateStudyPlan(token!, 7);
      showToast("Generated fresh 7-day adaptive plan!", "success");
      queryClient.invalidateQueries({ queryKey: ["student-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["student-home"] });
    } catch (err: any) {
      showToast(err.message || "Failed to generate plan", "error");
    } finally {
      setIsReplanning(false);
    }
  };

  const filteredTasks = tasks.filter((t) => {
    if (filterStatus === "ALL") return true;
    return t.status === filterStatus;
  });

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white flex items-center gap-2">
              <span>My Adaptive Study Plan</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800">
                OR-Tools CP-SAT
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Constraint-aware scheduling with strict capacity ceilings and deadline compliance
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleReplan}
              disabled={isReplanning}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-850 border border-slate-800 text-xs font-semibold text-slate-300 hover:text-white transition-all cursor-pointer disabled:opacity-50"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isReplanning ? "animate-spin" : ""}`} />
              <span>Rebalance Calendar</span>
            </button>
            <button
              onClick={handleGenerateInitialPlan}
              disabled={isReplanning}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Generate 7 Days</span>
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center justify-between gap-2 overflow-x-auto pb-1">
          <div className="flex items-center gap-1.5 bg-slate-900/60 p-1 rounded-xl border border-slate-800 text-xs">
            {["ALL", "PENDING", "COMPLETED", "SKIPPED"].map((status) => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                  filterStatus === status
                    ? "bg-slate-800 text-white font-semibold shadow-xs"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {status.charAt(0) + status.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          <div className="text-xs text-slate-400 hidden sm:block">
            Showing <span className="font-semibold text-white">{filteredTasks.length}</span> tasks
          </div>
        </div>

        {/* Main Tasks List */}
        {isError ? (
          <ErrorState onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : filteredTasks.length === 0 ? (
          <EmptyState
            icon={CalendarIcon}
            title={filterStatus === "ALL" ? "No study tasks scheduled yet" : `No ${filterStatus.toLowerCase()} tasks`}
            description="Generate a constraint-aware study plan to automatically schedule review and practice sessions."
            actionLabel="Generate 7-Day Plan"
            onAction={handleGenerateInitialPlan}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredTasks.map((task) => {
              const isPending = task.status === "PENDING" || task.status === "IN_PROGRESS";
              const isCompleted = task.status === "COMPLETED";
              const isSkipped = task.status === "SKIPPED";
              const startTime = new Date(task.planned_start).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              });
              const startDate = new Date(task.planned_start).toLocaleDateString([], {
                month: "short",
                day: "numeric",
              });

              return (
                <div
                  key={task.id}
                  className={`p-5 rounded-3xl border transition-all space-y-3.5 ${
                    isCompleted
                      ? "border-emerald-900/40 bg-emerald-950/10 opacity-80"
                      : isSkipped
                      ? "border-slate-800 bg-slate-900/20 opacity-60"
                      : "border-slate-800/80 bg-slate-900/40 hover:border-slate-700"
                  }`}
                >
                  {/* Task Header */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-indigo-950 text-indigo-300 font-bold uppercase tracking-wider border border-indigo-800/40">
                        {task.task_type}
                      </span>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-md ${
                          isCompleted
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-800/40"
                            : isSkipped
                            ? "bg-slate-800 text-slate-400"
                            : "bg-slate-800 text-indigo-300"
                        }`}
                      >
                        {task.status}
                      </span>
                    </div>

                    <button
                      onClick={() => handleLockToggle(task)}
                      disabled={actionLoadingId === task.id}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                      title={task.locked ? "Task is locked (preserved during replanning)" : "Lock task"}
                    >
                      {task.locked ? (
                        <Lock className="w-3.5 h-3.5 text-amber-400" />
                      ) : (
                        <Unlock className="w-3.5 h-3.5 text-slate-500" />
                      )}
                    </button>
                  </div>

                  {/* Title & Objective */}
                  <div className="space-y-1">
                    <h3 className="text-sm font-bold text-white leading-snug">{task.title}</h3>
                    {task.objective && (
                      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                        {task.objective}
                      </p>
                    )}
                  </div>

                  {/* Scheduled Slot & Priority Meta */}
                  <div className="flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-3">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      <span>
                        {startDate} at {startTime} ({task.duration_minutes}m)
                      </span>
                    </div>
                    <span className="font-mono text-indigo-400 font-medium">
                      Pri: {(Number(task.priority) * 100).toFixed(0)}%
                    </span>
                  </div>

                  {/* Actions Bar */}
                  {isPending && (
                    <div className="pt-1 flex items-center gap-2">
                      <button
                        onClick={() => handleStartTask(task)}
                        className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-md shadow-indigo-600/25 transition-all cursor-pointer"
                      >
                        <Play className="w-3.5 h-3.5 fill-white" />
                        <span>Start Session</span>
                      </button>

                      <button
                        onClick={() => {
                          setRescheduleTaskId(task.id);
                          setRescheduleDate(new Date(task.planned_start).toISOString().slice(0, 16));
                        }}
                        className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
                      >
                        Reschedule
                      </button>

                      <button
                        onClick={() => handleSkip(task)}
                        disabled={actionLoadingId === task.id}
                        className="px-3 py-2 rounded-xl bg-slate-800/60 hover:bg-rose-950/40 text-slate-400 hover:text-rose-400 text-xs font-medium transition-colors cursor-pointer"
                        title="Skip task safely without degrading knowledge"
                      >
                        Skip
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Reschedule Modal */}
        {rescheduleTaskId && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-xs p-4">
            <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4 shadow-2xl animate-scale-in">
              <h3 className="text-sm font-bold text-white">Reschedule Study Task</h3>
              <form onSubmit={handleRescheduleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    New Date & Time
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={rescheduleDate}
                    onChange={(e) => setRescheduleDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setRescheduleTaskId(null)}
                    className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all"
                  >
                    Save Changes
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>

      {/* Focus Study Session Modal */}
      <StudySessionModal
        token={token!}
        task={activeSessionTask}
        isOpen={sessionModalOpen}
        onClose={() => setSessionModalOpen(false)}
        onCompleted={() => {
          queryClient.invalidateQueries({ queryKey: ["student-tasks"] });
          queryClient.invalidateQueries({ queryKey: ["student-home"] });
        }}
      />
    </AppShell>
  );
}
