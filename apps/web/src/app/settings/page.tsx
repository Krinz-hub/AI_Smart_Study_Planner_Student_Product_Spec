"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/ui/AppShell";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import {
  fetchSettings,
  updateSettings,
  fetchAvailability,
  updateAvailability,
  fetchExams,
  createExam,
  deleteExam,
  fetchGoals,
  createGoal,
  deleteGoal,
  fetchSubjects,
  UserSettings,
  AvailabilityWindowItem,
  ExamItem,
  GoalItem,
  SubjectItem,
} from "@/lib/api-client";

const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

export default function SettingsPage() {
  const { token } = useAuth();
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  // Settings State
  const [theme, setTheme] = useState<string>("dark");
  const [studyTimePref, setStudyTimePref] = useState<string>("evening");
  const [dailyCapacity, setDailyCapacity] = useState<number>(180);
  const [aiTutorMode, setAiTutorMode] = useState<string>("socratic");
  const [notifications, setNotifications] = useState<boolean>(true);
  const [reducedMotion, setReducedMotion] = useState<boolean>(false);

  // Availability State
  const [availability, setAvailability] = useState<AvailabilityWindowItem[]>([]);

  // Exam Form State
  const [examName, setExamName] = useState<string>("");
  const [examDate, setExamDate] = useState<string>("");
  const [examSubjectId, setExamSubjectId] = useState<string>("");

  // Goal Form State
  const [goalTitle, setGoalTitle] = useState<string>("");
  const [goalType, setGoalType] = useState<string>("DAILY_MINUTES");
  const [goalValue, setGoalValue] = useState<number>(120);

  // Queries
  const { data: settings, isLoading: isLoadingSettings } = useQuery<UserSettings>({
    queryKey: ["userSettings"],
    queryFn: () => fetchSettings(token!),
    enabled: !!token,
  });

  const { data: availabilityData } = useQuery<AvailabilityWindowItem[]>({
    queryKey: ["availability"],
    queryFn: () => fetchAvailability(token!),
    enabled: !!token,
  });

  const { data: exams } = useQuery<ExamItem[]>({
    queryKey: ["exams"],
    queryFn: () => fetchExams(token!),
    enabled: !!token,
  });

  const { data: goals } = useQuery<GoalItem[]>({
    queryKey: ["goals"],
    queryFn: () => fetchGoals(token!),
    enabled: !!token,
  });

  const { data: subjects } = useQuery<SubjectItem[]>({
    queryKey: ["subjects"],
    queryFn: () => fetchSubjects(token!),
    enabled: !!token,
  });

  // Populate settings
  useEffect(() => {
    if (settings) {
      setTheme(settings.theme || "dark");
      setStudyTimePref(settings.study_time_preference || "evening");
      setDailyCapacity(settings.daily_capacity_minutes || 180);
      setAiTutorMode(settings.ai_tutor_mode || "socratic");
      setNotifications(settings.notifications_enabled ?? true);
      setReducedMotion(settings.reduced_motion ?? false);
    }
  }, [settings]);

  // Populate availability
  useEffect(() => {
    if (availabilityData && availabilityData.length > 0) {
      setAvailability(availabilityData);
    } else {
      // Default 7 days
      const defaults = [0, 1, 2, 3, 4, 5, 6].map((w) => ({
        weekday: w,
        start_time: "09:00",
        end_time: "21:00",
        enabled: true,
      }));
      setAvailability(defaults);
    }
  }, [availabilityData]);

  // Save Settings Mutation
  const settingsMutation = useMutation({
    mutationFn: () =>
      updateSettings(token!, {
        theme,
        study_time_preference: studyTimePref,
        daily_capacity_minutes: Number(dailyCapacity),
        ai_tutor_mode: aiTutorMode,
        notifications_enabled: notifications,
        reduced_motion: reducedMotion,
      }),
    onSuccess: () => {
      addToast("Preferences saved successfully", "success");
      queryClient.invalidateQueries({ queryKey: ["userSettings"] });
    },
    onError: (err: any) => {
      addToast(err?.message || "Failed to save settings", "error");
    },
  });

  // Save Availability Mutation
  const availabilityMutation = useMutation({
    mutationFn: () => updateAvailability(token!, availability),
    onSuccess: () => {
      addToast("Availability schedule updated", "success");
      queryClient.invalidateQueries({ queryKey: ["availability"] });
    },
    onError: (err: any) => {
      addToast(err?.message || "Failed to update availability", "error");
    },
  });

  // Add Exam Mutation
  const addExamMutation = useMutation({
    mutationFn: () =>
      createExam(token!, {
        name: examName,
        exam_at: new Date(examDate).toISOString(),
        subject_id: examSubjectId || subjects?.[0]?.id || "",
      }),
    onSuccess: () => {
      addToast("Target milestone added", "success");
      setExamName("");
      setExamDate("");
      queryClient.invalidateQueries({ queryKey: ["exams"] });
    },
    onError: (err: any) => {
      addToast(err?.message || "Failed to create exam", "error");
    },
  });

  // Delete Exam Mutation
  const deleteExamMutation = useMutation({
    mutationFn: (id: string) => deleteExam(token!, id),
    onSuccess: () => {
      addToast("Exam milestone deleted", "success");
      queryClient.invalidateQueries({ queryKey: ["exams"] });
    },
  });

  // Add Goal Mutation
  const addGoalMutation = useMutation({
    mutationFn: () =>
      createGoal(token!, {
        title: goalTitle,
        target_type: goalType,
        target_value: Number(goalValue),
      }),
    onSuccess: () => {
      addToast("Goal created", "success");
      setGoalTitle("");
      queryClient.invalidateQueries({ queryKey: ["goals"] });
    },
    onError: (err: any) => {
      addToast(err?.message || "Failed to create goal", "error");
    },
  });

  // Delete Goal Mutation
  const deleteGoalMutation = useMutation({
    mutationFn: (id: string) => deleteGoal(token!, id),
    onSuccess: () => {
      addToast("Goal removed", "success");
      queryClient.invalidateQueries({ queryKey: ["goals"] });
    },
  });

  const handleToggleDay = (weekday: number) => {
    setAvailability((prev) =>
      prev.map((w) => (w.weekday === weekday ? { ...w, enabled: !w.enabled } : w))
    );
  };

  const handleTimeChange = (weekday: number, field: "start_time" | "end_time", value: string) => {
    setAvailability((prev) =>
      prev.map((w) => (w.weekday === weekday ? { ...w, [field]: value } : w))
    );
  };

  return (
    <AppShell activeNav="settings">
      <div className="max-w-4xl mx-auto space-y-8 animate-fade-in pb-16">
        {/* Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
            App Settings & Preferences
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Configure adaptive planner capacity, tutor preferences, weekly study windows, and milestones.
          </p>
        </div>

        {isLoadingSettings ? (
          <SkeletonCard />
        ) : (
          <div className="space-y-8">
            {/* 1. General Preferences Card */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>⚙️</span> Study Session & Planner Configuration
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {/* Daily Study Capacity */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                      Daily Study Capacity
                    </label>
                    <span className="font-mono text-xs font-bold text-indigo-500">
                      {dailyCapacity} mins ({(dailyCapacity / 60).toFixed(1)} hrs)
                    </span>
                  </div>
                  <input
                    type="range"
                    min="30"
                    max="480"
                    step="15"
                    value={dailyCapacity}
                    onChange={(e) => setDailyCapacity(Number(e.target.value))}
                    className="w-full accent-indigo-600"
                  />
                  <span className="text-[11px] text-slate-400 block">
                    The OR-Tools constraint solver will never exceed this daily study ceiling.
                  </span>
                </div>

                {/* Preferred Study Time */}
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                    Preferred Study Time
                  </label>
                  <select
                    value={studyTimePref}
                    onChange={(e) => setStudyTimePref(e.target.value)}
                    className="w-full p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="morning">Morning (08:00 - 12:00)</option>
                    <option value="afternoon">Afternoon (13:00 - 17:00)</option>
                    <option value="evening">Evening (18:00 - 22:00)</option>
                    <option value="night">Late Night (22:00 - 02:00)</option>
                  </select>
                </div>

                {/* AI Tutor Default Mode */}
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                    AI Tutor Default Mode
                  </label>
                  <select
                    value={aiTutorMode}
                    onChange={(e) => setAiTutorMode(e.target.value)}
                    className="w-full p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="socratic">Socratic Dialogue (Guided Reflection)</option>
                    <option value="eli5">ELI5 Analogy (Simple intuitive models)</option>
                    <option value="deep_dive">Deep Dive (Mathematical rigor & proofs)</option>
                    <option value="exam_rubric">Exam Rubric (Model high-yield answers)</option>
                    <option value="hint">Step Hint (Next step without spoilers)</option>
                  </select>
                </div>

                {/* Theme & Motion */}
                <div className="space-y-3">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                    Accessibility & Motion
                  </label>
                  <div className="space-y-2">
                    <label className="flex items-center gap-3 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={reducedMotion}
                        onChange={(e) => setReducedMotion(e.target.checked)}
                        className="w-4 h-4 rounded accent-indigo-600"
                      />
                      <span>Enable Reduced Motion (prefers-reduced-motion)</span>
                    </label>
                    <label className="flex items-center gap-3 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={notifications}
                        onChange={(e) => setNotifications(e.target.checked)}
                        className="w-4 h-4 rounded accent-indigo-600"
                      />
                      <span>In-App Study & Spaced Review Notifications</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-end">
                <button
                  type="button"
                  onClick={() => settingsMutation.mutate()}
                  disabled={settingsMutation.isPending}
                  className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                >
                  {settingsMutation.isPending ? "Saving..." : "Save Preferences"}
                </button>
              </div>
            </div>

            {/* 2. Weekly Availability Schedule */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>🗓️</span> Weekly Study Availability Windows
                  </h2>
                  <p className="text-xs text-slate-500">
                    Define when you are available for automated study block allocations.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => availabilityMutation.mutate()}
                  disabled={availabilityMutation.isPending}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-sm disabled:opacity-50"
                >
                  {availabilityMutation.isPending ? "Updating..." : "Update Schedule"}
                </button>
              </div>

              <div className="space-y-3">
                {availability.map((win) => (
                  <div
                    key={win.weekday}
                    className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                  >
                    <label className="flex items-center gap-3 font-semibold text-slate-800 dark:text-slate-200 cursor-pointer min-w-[120px]">
                      <input
                        type="checkbox"
                        checked={win.enabled}
                        onChange={() => handleToggleDay(win.weekday)}
                        className="w-4 h-4 rounded accent-indigo-600"
                      />
                      <span>{DAYS[win.weekday]}</span>
                    </label>

                    <div className="flex items-center gap-3">
                      <span className="text-slate-400">From:</span>
                      <input
                        type="time"
                        disabled={!win.enabled}
                        value={win.start_time}
                        onChange={(e) =>
                          handleTimeChange(win.weekday, "start_time", e.target.value)
                        }
                        className="px-2.5 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-white font-mono disabled:opacity-40"
                      />
                      <span className="text-slate-400">To:</span>
                      <input
                        type="time"
                        disabled={!win.enabled}
                        value={win.end_time}
                        onChange={(e) =>
                          handleTimeChange(win.weekday, "end_time", e.target.value)
                        }
                        className="px-2.5 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-white font-mono disabled:opacity-40"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 3. Manage Target Exams & Milestones */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>🎯</span> Manage Target Exams
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <input
                  type="text"
                  placeholder="Exam Name (e.g. Midterm)"
                  value={examName}
                  onChange={(e) => setExamName(e.target.value)}
                  className="p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <input
                  type="date"
                  value={examDate}
                  onChange={(e) => setExamDate(e.target.value)}
                  className="p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <button
                  type="button"
                  disabled={!examName || !examDate || addExamMutation.isPending}
                  onClick={() => addExamMutation.mutate()}
                  className="px-4 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all disabled:opacity-40"
                >
                  + Add Milestone
                </button>
              </div>

              {exams && exams.length > 0 && (
                <div className="space-y-2 pt-2">
                  {exams.map((ex) => (
                    <div
                      key={ex.id}
                      className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs"
                    >
                      <div>
                        <span className="font-bold text-slate-900 dark:text-white block">
                          {ex.name}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          {new Date(ex.exam_at).toLocaleDateString()}
                        </span>
                      </div>
                      <button
                        onClick={() => deleteExamMutation.mutate(ex.id)}
                        className="text-slate-400 hover:text-rose-500 transition-colors"
                        title="Delete Milestone"
                      >
                        🗑️
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 4. Study Goals */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>🏆</span> Study Goals
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <input
                  type="text"
                  placeholder="Goal (e.g. Master Calculus)"
                  value={goalTitle}
                  onChange={(e) => setGoalTitle(e.target.value)}
                  className="p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <input
                  type="number"
                  placeholder="Target Minutes"
                  value={goalValue}
                  onChange={(e) => setGoalValue(Number(e.target.value))}
                  className="p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <button
                  type="button"
                  disabled={!goalTitle || addGoalMutation.isPending}
                  onClick={() => addGoalMutation.mutate()}
                  className="px-4 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all disabled:opacity-40"
                >
                  + Add Goal
                </button>
              </div>

              {goals && goals.length > 0 && (
                <div className="space-y-2 pt-2">
                  {goals.map((g) => (
                    <div
                      key={g.id}
                      className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs"
                    >
                      <span className="font-bold text-slate-900 dark:text-white">
                        {g.title} {g.target_value ? `(${g.target_value}m)` : ""}
                      </span>
                      <button
                        onClick={() => deleteGoalMutation.mutate(g.id)}
                        className="text-slate-400 hover:text-rose-500 transition-colors"
                        title="Delete Goal"
                      >
                        🗑️
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
