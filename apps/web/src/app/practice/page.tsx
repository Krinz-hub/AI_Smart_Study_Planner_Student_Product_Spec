"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/ui/AppShell";
import { useToast } from "@/components/ui/Toast";
import { useAuth } from "@/lib/auth-context";
import {
  fetchSubjects,
  fetchTopics,
  fetchProgressOverview,
  fetchDocuments,
  generateTopicQuiz,
  generateDocumentQuiz,
  SubjectItem,
  TopicItem,
  ProgressOverview,
  DocumentItem,
} from "@/lib/api-client";

export default function PracticeHubPage() {
  const { token } = useAuth();
  const router = useRouter();
  const { addToast } = useToast();

  const [selectedSubjectId, setSelectedSubjectId] = useState<string>("");
  const [selectedTopicId, setSelectedTopicId] = useState<string>("");
  const [numQuestions, setNumQuestions] = useState<number>(5);
  const [difficulty, setDifficulty] = useState<string>("MEDIUM");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  // Queries
  const { data: subjects } = useQuery<SubjectItem[]>({
    queryKey: ["subjects"],
    queryFn: () => fetchSubjects(token!),
    enabled: !!token,
  });

  const { data: topics } = useQuery<TopicItem[]>({
    queryKey: ["topics", selectedSubjectId],
    queryFn: () => fetchTopics(token!, selectedSubjectId),
    enabled: !!token && !!selectedSubjectId,
  });

  const { data: progress } = useQuery<ProgressOverview>({
    queryKey: ["progressOverview"],
    queryFn: () => fetchProgressOverview(token!),
    enabled: !!token,
  });

  const { data: documents } = useQuery<DocumentItem[]>({
    queryKey: ["documents"],
    queryFn: () => fetchDocuments(token!),
    enabled: !!token,
  });

  const handleLaunchTopicQuiz = async (topicIdToUse?: string) => {
    const targetTopic = topicIdToUse || selectedTopicId;
    if (!targetTopic) {
      addToast("Please select a topic to practice", "error");
      return;
    }
    try {
      setIsGenerating(true);
      const quiz = await generateTopicQuiz(token!, targetTopic, numQuestions, difficulty);
      const targetQuizId = quiz.id || quiz.quiz_id;
      if (!targetQuizId) {
        throw new Error("Quiz generated but missing identifier");
      }
      addToast("Practice quiz ready!", "success");
      router.push(`/practice/${targetQuizId}`);
    } catch (err: any) {
      addToast(err?.message || "Failed to generate quiz", "error");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleLaunchDocumentQuiz = async (docId: string) => {
    try {
      setIsGenerating(true);
      const res = await generateDocumentQuiz(token!, docId, 5);
      const targetQuizId = res.id || res.quiz_id;
      if (!targetQuizId) {
        throw new Error("Document quiz generated but missing identifier");
      }
      addToast("Document active recall quiz ready!", "success");
      router.push(`/practice/${targetQuizId}`);
    } catch (err: any) {
      addToast(err?.message || "Failed to generate notes quiz", "error");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <AppShell activeNav="practice">
      <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
        {/* Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
            Practice & Active Recall Center
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Grounded diagnostic quizzes, spaced retrieval drills, and targeted mistake remediation.
          </p>
        </div>

        {/* Quick-Launch Preset Tiles */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Weak Topics Rescue Tile */}
          <div className="bg-gradient-to-br from-rose-950/20 via-slate-900 to-slate-900 border border-rose-500/20 rounded-3xl p-6 flex flex-col justify-between space-y-4 hover:border-rose-500/40 transition-all">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-2xl">🎯</span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  Targeted Rescue
                </span>
              </div>
              <h3 className="text-lg font-bold text-white">Weak Topics Drill</h3>
              <p className="text-xs text-slate-400">
                Target areas where your Bayesian Knowledge Tracing probability is currently below 60%.
              </p>
            </div>
            {progress?.needs_attention_topics && progress.needs_attention_topics.length > 0 ? (
              <div className="space-y-2 pt-2">
                <span className="text-[11px] text-slate-400 font-semibold block">
                  Top Priority Topic: {progress.needs_attention_topics[0].name}
                </span>
                <button
                  disabled={isGenerating}
                  onClick={() => handleLaunchTopicQuiz(progress.needs_attention_topics[0].id)}
                  className="w-full py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition-all shadow-md shadow-rose-600/20 disabled:opacity-50"
                >
                  Start Rescue Drill →
                </button>
              </div>
            ) : (
              <div className="pt-2 text-xs text-emerald-400 font-medium flex items-center gap-1.5">
                <span>✓</span> No critical knowledge gaps detected!
              </div>
            )}
          </div>

          {/* Spaced Retrieval Tile */}
          <div className="bg-gradient-to-br from-indigo-950/20 via-slate-900 to-slate-900 border border-indigo-500/20 rounded-3xl p-6 flex flex-col justify-between space-y-4 hover:border-indigo-500/40 transition-all">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-2xl">⏳</span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  FSRS Spaced Repetition
                </span>
              </div>
              <h3 className="text-lg font-bold text-white">Memory Retention Drill</h3>
              <p className="text-xs text-slate-400">
                Reinforce decaying concepts scheduled for review by the spaced repetition engine.
              </p>
            </div>
            {progress?.review_due_topics && progress.review_due_topics.length > 0 ? (
              <div className="space-y-2 pt-2">
                <span className="text-[11px] text-slate-400 font-semibold block">
                  Due: {progress.review_due_topics[0].name}
                </span>
                <button
                  disabled={isGenerating}
                  onClick={() => handleLaunchTopicQuiz(progress.review_due_topics[0].id)}
                  className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                >
                  Review Due Concepts →
                </button>
              </div>
            ) : (
              <div className="pt-2 text-xs text-slate-400">
                All topic memories are currently well-consolidated above 90% retrievability.
              </div>
            )}
          </div>

          {/* Uploaded Notes Quiz Tile */}
          <div className="bg-gradient-to-br from-purple-950/20 via-slate-900 to-slate-900 border border-purple-500/20 rounded-3xl p-6 flex flex-col justify-between space-y-4 hover:border-purple-500/40 transition-all">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-2xl">📄</span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  Document Grounded
                </span>
              </div>
              <h3 className="text-lg font-bold text-white">Lecture Notes Recall</h3>
              <p className="text-xs text-slate-400">
                Generate instant recall questions strictly grounded in your uploaded lecture PDFs or notes.
              </p>
            </div>
            {documents && documents.length > 0 ? (
              <div className="space-y-2 pt-2">
                <span className="text-[11px] text-slate-400 font-semibold block truncate">
                  Latest: {documents[0].filename}
                </span>
                <button
                  disabled={isGenerating}
                  onClick={() => handleLaunchDocumentQuiz(documents[0].id)}
                  className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold transition-all shadow-md shadow-purple-600/20 disabled:opacity-50"
                >
                  Generate Notes Quiz →
                </button>
              </div>
            ) : (
              <button
                onClick={() => router.push("/materials")}
                className="w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
              >
                Upload Course Notes First →
              </button>
            )}
          </div>
        </div>

        {/* Custom Practice Builder Section */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 text-indigo-500 flex items-center justify-center font-bold">
              🛠️
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Custom Topic Practice Builder
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Configure question volume, cognitive taxonomy level, and topic focus.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Subject Selector */}
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Select Course Subject
              </label>
              <select
                value={selectedSubjectId}
                onChange={(e) => {
                  setSelectedSubjectId(e.target.value);
                  setSelectedTopicId("");
                }}
                className="w-full p-3 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">-- Choose Subject --</option>
                {subjects?.map((sub) => (
                  <option key={sub.id} value={sub.id}>
                    {sub.name} {sub.code ? `(${sub.code})` : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Topic Selector */}
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Select Topic / Module
              </label>
              <select
                disabled={!selectedSubjectId || !topics || topics.length === 0}
                value={selectedTopicId}
                onChange={(e) => setSelectedTopicId(e.target.value)}
                className="w-full p-3 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                <option value="">
                  {selectedSubjectId ? "-- Choose Topic --" : "-- Select Subject First --"}
                </option>
                {topics?.map((top) => (
                  <option key={top.id} value={top.id}>
                    {top.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Questions count */}
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Number of Questions
              </label>
              <div className="grid grid-cols-3 gap-3">
                {[3, 5, 10].map((cnt) => (
                  <button
                    key={cnt}
                    type="button"
                    onClick={() => setNumQuestions(cnt)}
                    className={`py-2.5 rounded-xl text-xs font-bold transition-all ${
                      numQuestions === cnt
                        ? "bg-indigo-600 text-white shadow-sm"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                    }`}
                  >
                    {cnt} Questions
                  </button>
                ))}
              </div>
            </div>

            {/* Difficulty */}
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Cognitive Difficulty
              </label>
              <div className="grid grid-cols-3 gap-3">
                {["EASY", "MEDIUM", "HARD"].map((diff) => (
                  <button
                    key={diff}
                    type="button"
                    onClick={() => setDifficulty(diff)}
                    className={`py-2.5 rounded-xl text-xs font-bold transition-all ${
                      difficulty === diff
                        ? "bg-indigo-600 text-white shadow-sm"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                    }`}
                  >
                    {diff}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-end">
            <button
              disabled={!selectedTopicId || isGenerating}
              onClick={() => handleLaunchTopicQuiz()}
              className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold transition-all shadow-md shadow-indigo-600/30 disabled:opacity-50 inline-flex items-center gap-2"
            >
              {isGenerating ? (
                <>
                  <span className="animate-spin text-sm">⌛</span> Generating Verification Quiz...
                </>
              ) : (
                <>
                  <span>🚀</span> Launch Custom Quiz
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
