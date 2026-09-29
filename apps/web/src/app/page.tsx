"use client";

import React from "react";
import Link from "next/link";
import {
  Sparkles,
  ArrowRight,
  Brain,
  Calendar,
  BookOpen,
  MessageSquare,
  FileText,
  ShieldCheck,
  Cpu,
  CheckCircle2,
  Lock,
  Layers,
  Flame,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white flex flex-col">
      {/* Top Navbar */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-slate-950/80 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-linear-to-tr from-indigo-600 via-purple-600 to-sky-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </div>
            <span className="font-bold text-lg bg-linear-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent">
              Luminary
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/admin"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-900 transition-colors"
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>Admin Console</span>
            </Link>
            <Link
              href="/login"
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-900 transition-colors"
            >
              Log In
            </Link>
            <Link
              href="/signup"
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all cursor-pointer"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1">
        <section className="relative pt-20 pb-16 overflow-hidden">
          {/* Subtle Ambient Background Gradients */}
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-linear-to-tr from-indigo-600/15 via-purple-600/10 to-sky-500/15 blur-3xl pointer-events-none rounded-full" />

          <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-950/80 border border-indigo-800/60 text-indigo-300 text-xs font-medium">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Evidence-Driven Adaptive Learning Intelligence</span>
            </div>

            <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
              Study Smarter with{" "}
              <span className="bg-linear-to-r from-indigo-400 via-purple-300 to-sky-400 bg-clip-text text-transparent">
                Mathematical Certainty
              </span>
            </h1>

            <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-400 leading-relaxed">
              Not a chatbot wrapper. Luminary combines Bayesian Knowledge Tracing (BKT), FSRS memory decay, and Google OR-Tools constraint scheduling to engineer your optimal study journey.
            </p>

            <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                href="/signup"
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-3.5 rounded-2xl bg-linear-to-r from-indigo-600 via-purple-600 to-sky-600 hover:opacity-95 text-white font-bold text-sm shadow-xl shadow-indigo-500/25 transition-all hover:scale-105"
              >
                <span>Start Your Personalized Plan</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/login"
                className="w-full sm:w-auto px-6 py-3.5 rounded-2xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white font-semibold text-sm transition-all"
              >
                Sign In to Existing Cockpit
              </Link>
            </div>

            {/* Platform Highlights */}
            <div className="pt-12 grid grid-cols-2 sm:grid-cols-4 gap-4 text-left">
              <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/80">
                <Brain className="w-5 h-5 text-indigo-400 mb-2" />
                <div className="text-xs font-bold text-white">BKT Mastery Model</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Posterior probability updates per question</div>
              </div>
              <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/80">
                <Calendar className="w-5 h-5 text-sky-400 mb-2" />
                <div className="text-xs font-bold text-white">OR-Tools CP-SAT</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Conflict-free scheduling with hard capacity ceilings</div>
              </div>
              <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/80">
                <MessageSquare className="w-5 h-5 text-purple-400 mb-2" />
                <div className="text-xs font-bold text-white">Socratic AI Tutor</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Strictly grounded in your course materials</div>
              </div>
              <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/80">
                <FileText className="w-5 h-5 text-emerald-400 mb-2" />
                <div className="text-xs font-bold text-white">Notes to Quizzes</div>
                <div className="text-[11px] text-slate-400 mt-0.5">10-point summaries, flashcards, vector RAG</div>
              </div>
            </div>
          </div>
        </section>

        {/* The Closed-Loop Adaptive Engine Breakdown */}
        <section className="py-16 border-t border-slate-900 bg-slate-950/50">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
            <div className="text-center space-y-3">
              <h2 className="text-2xl sm:text-3xl font-bold text-white">
                How Luminary Continuously Adapts
              </h2>
              <p className="text-sm text-slate-400 max-w-xl mx-auto">
                Every study task and quiz submission generates empirical evidence that recalibrates your schedule in real-time.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-950 text-indigo-400 flex items-center justify-center font-bold font-mono">
                  1
                </div>
                <h3 className="text-base font-bold text-white">Official Syllabus Discovery</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Enter your university, branch, and semester. Luminary automatically discovers, normalizes, and structures your complete syllabus before generating your baseline diagnostic.
                </p>
              </div>

              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-3">
                <div className="w-10 h-10 rounded-xl bg-purple-950 text-purple-400 flex items-center justify-center font-bold font-mono">
                  2
                </div>
                <h3 className="text-base font-bold text-white">Deterministic Task Selection</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  The Decision Engine prioritizes topics based on upcoming exam deadlines, forgetting risks, prerequisite relationships, and current BKT mastery—avoiding random schedules.
                </p>
              </div>

              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-3">
                <div className="w-10 h-10 rounded-xl bg-sky-950 text-sky-400 flex items-center justify-center font-bold font-mono">
                  3
                </div>
                <h3 className="text-base font-bold text-white">Smart Rescue & Replanning</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Fell behind or missed a session? The Anti-Feedback Engine preserves locked commitments, trims low-value work, and rebalances your calendar without overloading tomorrow.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-8 bg-slate-950 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-400">Luminary Study Planner</span>
            <span>• Evidence-Based Education Architecture</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="hover:text-slate-300">Login</Link>
            <Link href="/signup" className="hover:text-slate-300">Register</Link>
            <Link href="/admin" className="hover:text-slate-300">Admin Observability</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
