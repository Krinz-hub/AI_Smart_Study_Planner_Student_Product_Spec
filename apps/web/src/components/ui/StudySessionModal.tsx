"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Play,
  Pause,
  RotateCcw,
  CheckCircle2,
  BookOpen,
  Sparkles,
  Star,
  Clock,
  Volume2,
  VolumeX,
  Loader2,
} from "lucide-react";
import { StudyTask, submitTaskCompletion } from "@/lib/api-client";
import { useToast } from "./Toast";

interface StudySessionModalProps {
  token: string;
  task: StudyTask | null;
  isOpen: boolean;
  onClose: () => void;
  onCompleted: (taskId: string) => void;
}

export function StudySessionModal({
  token,
  task,
  isOpen,
  onClose,
  onCompleted,
}: StudySessionModalProps) {
  const { showToast } = useToast();
  const [secondsRemaining, setSecondsRemaining] = useState<number>(45 * 60);
  const [totalSeconds, setTotalSeconds] = useState<number>(45 * 60);
  const [isActive, setIsActive] = useState<boolean>(true);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Completion Form State
  const [showCompletionForm, setShowCompletionForm] = useState<boolean>(false);
  const [selfRating, setSelfRating] = useState<number>(4);
  const [notes, setNotes] = useState<string>("");
  const [perceivedSuccess, setPerceivedSuccess] = useState<"STRONG_PASS" | "NEEDS_PRACTICE">("STRONG_PASS");

  useEffect(() => {
    if (task) {
      const initialSeconds = (task.duration_minutes || 45) * 60;
      setSecondsRemaining(initialSeconds);
      setTotalSeconds(initialSeconds);
      setIsActive(true);
      setShowCompletionForm(false);
      setNotes("");
    }
  }, [task]);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (isActive && secondsRemaining > 0) {
      interval = setInterval(() => {
        setSecondsRemaining((prev) => prev - 1);
      }, 1000);
    } else if (secondsRemaining === 0 && isActive) {
      setIsActive(false);
      setShowCompletionForm(true);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isActive, secondsRemaining]);

  if (!isOpen || !task) return null;

  const minutes = Math.floor(secondsRemaining / 60);
  const seconds = secondsRemaining % 60;
  const progressPct = ((totalSeconds - secondsRemaining) / totalSeconds) * 100;
  const elapsedMinutes = Math.max(1, Math.round((totalSeconds - secondsRemaining) / 60));

  const handleFinish = async () => {
    setSubmitting(true);
    try {
      const isCorrect = perceivedSuccess === "STRONG_PASS";
      const score = isCorrect ? 0.85 : 0.45;
      await submitTaskCompletion(token, task.id, {
        actual_minutes: elapsedMinutes,
        score,
        is_correct: isCorrect,
        self_rating: selfRating,
        notes: notes.trim() || undefined,
      });

      showToast(`Completed "${task.title}". Evidence logged & BKT updated!`, "success");
      onCompleted(task.id);
      onClose();
    } catch (err: any) {
      showToast(err.message || "Failed to complete task", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 overflow-y-auto">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden animate-scale-in">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Focus Study Session
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setSoundEnabled(!soundEnabled)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white transition-colors"
              title={soundEnabled ? "Mute chimes" : "Enable chimes"}
            >
              {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Task Info Banner */}
          <div className="p-4 rounded-2xl bg-indigo-950/30 border border-indigo-800/40 space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-indigo-900 text-indigo-300 font-semibold uppercase">
                {task.task_type}
              </span>
              <span className="text-xs text-indigo-300 font-medium">Planned Duration: {task.duration_minutes}m</span>
            </div>
            <h3 className="text-sm font-bold text-white">{task.title}</h3>
            {task.objective && (
              <p className="text-xs text-slate-300/90 leading-relaxed">{task.objective}</p>
            )}
          </div>

          {!showCompletionForm ? (
            /* Timer View */
            <div className="flex flex-col items-center space-y-6">
              {/* Circular Progress Display */}
              <div className="relative w-48 h-48 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="96"
                    cy="96"
                    r="84"
                    stroke="currentColor"
                    strokeWidth="8"
                    className="text-slate-800"
                    fill="transparent"
                  />
                  <circle
                    cx="96"
                    cy="96"
                    r="84"
                    stroke="currentColor"
                    strokeWidth="8"
                    strokeDasharray={2 * Math.PI * 84}
                    strokeDashoffset={2 * Math.PI * 84 * (1 - progressPct / 100)}
                    strokeLinecap="round"
                    className="text-indigo-500 transition-all duration-1000 ease-linear"
                    fill="transparent"
                  />
                </svg>

                <div className="absolute flex flex-col items-center justify-center">
                  <div className="text-4xl font-mono font-bold text-white tracking-tight">
                    {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
                  </div>
                  <div className="text-[11px] font-medium text-slate-400 mt-1">
                    {isActive ? "Focusing..." : "Paused"}
                  </div>
                </div>
              </div>

              {/* Controls */}
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setIsActive(!isActive)}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
                >
                  {isActive ? (
                    <>
                      <Pause className="w-4 h-4" />
                      <span>Pause</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      <span>Resume</span>
                    </>
                  )}
                </button>

                <button
                  onClick={() => setSecondsRemaining(totalSeconds)}
                  className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
                  title="Reset Timer"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>

                <button
                  onClick={() => {
                    setIsActive(false);
                    setShowCompletionForm(true);
                  }}
                  className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-800/80 text-emerald-300 text-xs font-semibold transition-all cursor-pointer"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Finish Early</span>
                </button>
              </div>
            </div>
          ) : (
            /* Reflection & Completion Form */
            <div className="space-y-4 animate-fade-in">
              <div className="text-center space-y-1">
                <div className="w-10 h-10 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 mx-auto flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <h4 className="text-sm font-bold text-white">Record Session Evidence</h4>
                <p className="text-xs text-slate-400">
                  Calibrate your Bayesian Knowledge Tracing model with how this session went.
                </p>
              </div>

              {/* Comprehension Outcome Toggle */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-2">
                  How well did you understand the core objectives?
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setPerceivedSuccess("STRONG_PASS")}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      perceivedSuccess === "STRONG_PASS"
                        ? "border-emerald-500 bg-emerald-950/40 text-emerald-200"
                        : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <div className="text-xs font-semibold">Understood Well</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">Increases topic mastery</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPerceivedSuccess("NEEDS_PRACTICE")}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      perceivedSuccess === "NEEDS_PRACTICE"
                        ? "border-amber-500 bg-amber-950/40 text-amber-200"
                        : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <div className="text-xs font-semibold">Needs Review</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">Schedules early practice</div>
                  </button>
                </div>
              </div>

              {/* Rating */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Self-Rating (1-5)
                </label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setSelfRating(star)}
                      className="p-1.5 transition-transform hover:scale-110"
                    >
                      <Star
                        className={`w-5 h-5 ${
                          star <= selfRating
                            ? "text-amber-400 fill-amber-400"
                            : "text-slate-700"
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              {/* Reflection Notes */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Notes & Key Takeaways (Optional)
                </label>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Formulas remembered, confusing concepts, or ideas to ask AI tutor..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Submit Button */}
              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCompletionForm(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Back to Timer
                </button>
                <button
                  type="button"
                  onClick={handleFinish}
                  disabled={submitting}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/30 transition-all cursor-pointer disabled:opacity-50"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  <span>Save & Complete Task</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
