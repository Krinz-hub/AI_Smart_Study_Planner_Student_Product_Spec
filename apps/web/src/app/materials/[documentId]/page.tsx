"use client";

import React, { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/ui/AppShell";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import {
  fetchDocumentSummary,
  fetchDocumentFlashcards,
  generateDocumentQuiz,
  Document10PointSummary,
  DocumentFlashcardsResponse,
} from "@/lib/api-client";

interface PageProps {
  params: Promise<{ documentId: string }>;
}

export default function DocumentAnalysisPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { documentId } = resolvedParams;
  const { token } = useAuth();
  const router = useRouter();
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState<"summary" | "flashcards">("summary");
  const [currentCardIdx, setCurrentCardIdx] = useState<number>(0);
  const [isFlipped, setIsFlipped] = useState<boolean>(false);
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState<boolean>(false);

  // Queries
  const {
    data: summary,
    isLoading: isLoadingSummary,
    error: summaryError,
    refetch: refetchSummary,
  } = useQuery<Document10PointSummary>({
    queryKey: ["documentSummary", documentId],
    queryFn: () => fetchDocumentSummary(token!, documentId),
    enabled: !!token && !!documentId,
  });

  const { data: flashcardData, isLoading: isLoadingFlashcards } =
    useQuery<DocumentFlashcardsResponse>({
      queryKey: ["documentFlashcards", documentId],
      queryFn: () => fetchDocumentFlashcards(token!, documentId),
      enabled: !!token && !!documentId,
    });

  const flashcards = flashcardData?.flashcards || [];
  const currentCard = flashcards[currentCardIdx] || null;

  const handleGenerateQuiz = async () => {
    try {
      setIsGeneratingQuiz(true);
      const res = await generateDocumentQuiz(token!, documentId, 5);
      addToast("Generated active recall quiz!", "success");
      router.push(`/practice/${res.quiz_id || res.id}`);
    } catch (err: any) {
      addToast(err?.message || "Failed to generate quiz", "error");
    } finally {
      setIsGeneratingQuiz(false);
    }
  };

  return (
    <AppShell activeNav="materials">
      <div className="max-w-5xl mx-auto space-y-8 animate-fade-in pb-16">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
          <Link href="/materials" className="hover:text-indigo-400 transition-colors">
            Materials
          </Link>
          <span>/</span>
          <span className="text-slate-900 dark:text-slate-200 font-semibold truncate max-w-sm">
            {summary?.filename || "Document Intelligence"}
          </span>
        </div>

        {/* Top Header Card */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-indigo-500">
              10-Point Pedagogical Synthesis
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
              {summary?.filename || "Course Document Analysis"}
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
              Extracted formulas, high-yield exam points, core definitions, and active recall cues.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              disabled={isGeneratingQuiz}
              onClick={handleGenerateQuiz}
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md shadow-indigo-500/20 disabled:opacity-50 inline-flex items-center gap-2"
            >
              {isGeneratingQuiz ? (
                <>
                  <span className="animate-spin text-sm">⌛</span> Generating...
                </>
              ) : (
                <>
                  <span>⚡</span> Generate Document Quiz
                </>
              )}
            </button>
            <Link
              href="/tutor"
              className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold transition-all"
            >
              🤖 Ask Tutor
            </Link>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
          <button
            onClick={() => setActiveTab("summary")}
            className={`px-4 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === "summary"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            📋 10-Point Synthesis
          </button>
          <button
            onClick={() => setActiveTab("flashcards")}
            className={`px-4 py-2 text-xs font-bold rounded-xl transition-all ${
              activeTab === "flashcards"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            🃏 Active Recall Flashcards ({flashcards.length})
          </button>
        </div>

        {/* TAB 1: 10-POINT SUMMARY */}
        {activeTab === "summary" && (
          <div className="space-y-6">
            {isLoadingSummary ? (
              <div className="space-y-4">
                <SkeletonCard />
                <SkeletonCard />
              </div>
            ) : summaryError ? (
              <ErrorState
                title="Summary Unavailable"
                description="Could not extract 10-point summary for this document."
                onRetry={() => refetchSummary()}
              />
            ) : !summary ? null : (
              <div className="space-y-6">
                {/* 1. Executive Summary */}
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-3">
                  <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>1️⃣</span> Executive Summary
                  </h2>
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    {summary.executive_summary}
                  </p>
                </div>

                {/* 2. Key Definitions */}
                {summary.key_definitions && summary.key_definitions.length > 0 && (
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
                    <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <span>2️⃣</span> Key Definitions & Terminology
                    </h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {summary.key_definitions.map((def, idx) => (
                        <div
                          key={idx}
                          className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 space-y-1"
                        >
                          <span className="text-xs font-bold text-indigo-500 block">
                            {def.term}
                          </span>
                          <p className="text-xs text-slate-600 dark:text-slate-300">
                            {def.definition}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 3. Formulas and Equations */}
                {summary.formulas_and_equations && summary.formulas_and_equations.length > 0 && (
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
                    <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <span>3️⃣</span> Formulas & Equations
                    </h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {summary.formulas_and_equations.map((f, idx) => (
                        <div
                          key={idx}
                          className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 space-y-2"
                        >
                          <span className="text-xs font-bold text-slate-900 dark:text-white block">
                            {f.name}
                          </span>
                          <div className="p-2.5 rounded-xl bg-slate-900 text-emerald-400 font-mono text-xs text-center">
                            {f.formula}
                          </div>
                          <p className="text-[11px] text-slate-500">{f.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 4 & 5. Core Mechanisms & Procedures */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Core Mechanisms */}
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-3">
                    <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <span>4️⃣</span> Core Mechanisms
                    </h2>
                    <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
                      {summary.core_mechanisms?.map((m, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-indigo-500 font-bold">•</span>
                          <span>{m}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Step by Step Procedures */}
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-3">
                    <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <span>5️⃣</span> Step-by-Step Procedures
                    </h2>
                    <ol className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
                      {summary.step_by_step_procedures?.map((p, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-indigo-500 font-bold font-mono">
                            {idx + 1}.
                          </span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>

                {/* 6 & 7. Pitfalls & Practical Examples */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Common Pitfalls */}
                  <div className="bg-white dark:bg-slate-900 border border-rose-500/20 rounded-3xl p-6 shadow-sm space-y-3 bg-rose-500/5">
                    <h2 className="text-base font-bold text-rose-500 flex items-center gap-2">
                      <span>⚠️</span> Common Pitfalls & Mistakes
                    </h2>
                    <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
                      {summary.common_pitfalls?.map((p, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-rose-500 font-bold">✗</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* High Yield Exam Points */}
                  <div className="bg-white dark:bg-slate-900 border border-amber-500/20 rounded-3xl p-6 shadow-sm space-y-3 bg-amber-500/5">
                    <h2 className="text-base font-bold text-amber-500 flex items-center gap-2">
                      <span>🎯</span> High-Yield Exam Points
                    </h2>
                    <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
                      {summary.high_yield_exam_points?.map((p, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-amber-500 font-bold">★</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* 10. Active Recall Questions */}
                {summary.active_recall_questions && summary.active_recall_questions.length > 0 && (
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
                    <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <span>🔟</span> Self-Testing Active Recall Prompts
                    </h2>
                    <div className="space-y-3">
                      {summary.active_recall_questions.map((q, idx) => (
                        <details
                          key={idx}
                          className="group p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 cursor-pointer"
                        >
                          <summary className="font-semibold text-xs sm:text-sm text-slate-900 dark:text-white list-none flex items-center justify-between">
                            <span>Q{idx + 1}: {q.question}</span>
                            <span className="text-slate-400 group-open:rotate-180 transition-transform">▼</span>
                          </summary>
                          <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300">
                            <strong className="text-emerald-500 block mb-1">Answer / Model Solution:</strong>
                            {q.answer}
                          </div>
                        </details>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: FLASHCARDS DECK */}
        {activeTab === "flashcards" && (
          <div className="space-y-6">
            {isLoadingFlashcards ? (
              <SkeletonCard />
            ) : flashcards.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-sm">
                No flashcards generated for this document yet.
              </div>
            ) : (
              <div className="max-w-xl mx-auto space-y-6">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
                  <span>
                    Card {currentCardIdx + 1} of {flashcards.length}
                  </span>
                  <span className="font-mono uppercase text-indigo-500">
                    {currentCard?.tag || "Conceptual"} • {currentCard?.difficulty || "Medium"}
                  </span>
                </div>

                {/* Flip Card Container */}
                <div
                  onClick={() => setIsFlipped(!isFlipped)}
                  className="cursor-pointer perspective h-80 relative select-none"
                >
                  <div
                    className={`w-full h-full rounded-3xl p-8 border shadow-lg transition-transform duration-500 flex flex-col justify-between items-center text-center ${
                      isFlipped
                        ? "bg-slate-900 border-indigo-500/50 text-white"
                        : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white"
                    }`}
                  >
                    <span className="text-xs uppercase font-bold tracking-widest text-slate-400">
                      {isFlipped ? "💡 Conceptual Solution" : "❓ Question / Prompt"}
                    </span>

                    <p className="text-lg sm:text-xl font-bold leading-relaxed px-4">
                      {isFlipped ? currentCard?.back : currentCard?.front}
                    </p>

                    <span className="text-[11px] text-slate-400">
                      (Click to flip card)
                    </span>
                  </div>
                </div>

                {/* Navigation Controls */}
                <div className="flex items-center justify-between gap-4">
                  <button
                    disabled={currentCardIdx === 0}
                    onClick={() => {
                      setIsFlipped(false);
                      setCurrentCardIdx((i) => Math.max(0, i - 1));
                    }}
                    className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-bold transition-all disabled:opacity-40"
                  >
                    ← Previous Card
                  </button>
                  <button
                    onClick={() => setIsFlipped(!isFlipped)}
                    className="px-4 py-2.5 rounded-xl bg-indigo-600/10 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-600/20 text-xs font-bold transition-all"
                  >
                    Flip Card ↺
                  </button>
                  <button
                    disabled={currentCardIdx === flashcards.length - 1}
                    onClick={() => {
                      setIsFlipped(false);
                      setCurrentCardIdx((i) => Math.min(flashcards.length - 1, i + 1));
                    }}
                    className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-bold transition-all disabled:opacity-40"
                  >
                    Next Card →
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
