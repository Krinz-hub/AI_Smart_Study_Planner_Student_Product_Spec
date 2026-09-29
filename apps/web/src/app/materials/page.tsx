"use client";

import React, { useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/ui/AppShell";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import {
  fetchDocuments,
  fetchSubjects,
  uploadDocument,
  deleteDocument,
  generateDocumentQuiz,
  DocumentItem,
  SubjectItem,
} from "@/lib/api-client";

export default function MaterialsPage() {
  const { token } = useAuth();
  const router = useRouter();
  const { addToast } = useToast();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedSubjectId, setSelectedSubjectId] = useState<string>("");
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [generatingQuizDocId, setGeneratingQuizDocId] = useState<string | null>(null);

  // Queries
  const { data: subjects } = useQuery<SubjectItem[]>({
    queryKey: ["subjects"],
    queryFn: () => fetchSubjects(token!),
    enabled: !!token,
  });

  const {
    data: documents,
    isLoading: isLoadingDocs,
    error: docsError,
    refetch: refetchDocs,
  } = useQuery<DocumentItem[]>({
    queryKey: ["documents"],
    queryFn: () => fetchDocuments(token!),
    enabled: !!token,
  });

  // Upload Mutation
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;

    try {
      setIsUploading(true);
      await uploadDocument(token, file, selectedSubjectId || undefined);
      addToast(`Uploaded "${file.name}"! Vector indexing initiated.`, "success");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    } catch (err: any) {
      addToast(err?.message || "Document upload failed", "error");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: (docId: string) => deleteDocument(token!, docId),
    onSuccess: () => {
      addToast("Document removed from vector library", "success");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (err: any) => {
      addToast(err?.message || "Failed to delete document", "error");
    },
  });

  // Generate Quiz from Document
  const handleGenerateQuiz = async (docId: string) => {
    try {
      setGeneratingQuizDocId(docId);
      const res = await generateDocumentQuiz(token!, docId, 5);
      addToast("Generated active recall quiz from lecture notes!", "success");
      router.push(`/practice/${res.quiz_id || res.id}`);
    } catch (err: any) {
      addToast(err?.message || "Failed to generate quiz from notes", "error");
    } finally {
      setGeneratingQuizDocId(null);
    }
  };

  return (
    <AppShell activeNav="materials">
      <div className="max-w-6xl mx-auto space-y-8 animate-fade-in pb-12">
        {/* Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
            Course Materials & Notes RAG
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Upload lecture slides, syllabi, or handwritten notes (PDF, DOCX, TXT, MD) to generate structured 10-point summaries, active recall flashcards, and grounded quizzes.
          </p>
        </div>

        {/* Upload Dropzone Section */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>📤</span> Ingest New Learning Material
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Files are parsed, securely chunked, embedded via pgvector, and isolated to your tenant.
              </p>
            </div>

            {/* Subject Selector for Tagging */}
            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-slate-500 whitespace-nowrap">
                Course:
              </label>
              <select
                value={selectedSubjectId}
                onChange={(e) => setSelectedSubjectId(e.target.value)}
                className="px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">-- General / Untagged --</option>
                {subjects?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-indigo-500/70 rounded-2xl p-8 text-center cursor-pointer transition-all bg-slate-50/50 dark:bg-slate-800/30 group"
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
            />
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-500 mx-auto flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
              {isUploading ? "⌛" : "📁"}
            </div>
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 mt-3">
              {isUploading
                ? "Parsing document and extracting vector chunks..."
                : "Click or drag files here to upload"}
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Supports PDF, DOCX, TXT, and Markdown files up to 25MB
            </p>
          </div>
        </div>

        {/* Uploaded Documents Grid */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Indexed Library ({documents?.length || 0})
            </h2>
            <span className="text-xs text-slate-500">
              Isolated user workspace storage
            </span>
          </div>

          {isLoadingDocs ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : docsError ? (
            <ErrorState
              title="Unable to load materials"
              description="Failed to retrieve your uploaded document index."
              onRetry={() => refetchDocs()}
            />
          ) : !documents || documents.length === 0 ? (
            <EmptyState
              title="No materials uploaded yet"
              description="Upload lecture slides, chapters, or exam notes above to generate intelligent summaries and recall flashcards."
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-4 transition-all"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <span className="w-9 h-9 rounded-xl bg-purple-500/10 text-purple-500 flex items-center justify-center text-lg">
                        📄
                      </span>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {doc.processing_status || "COMPLETED"}
                      </span>
                    </div>

                    <div>
                      <h3 className="font-bold text-slate-900 dark:text-white text-base line-clamp-1">
                        {doc.filename}
                      </h3>
                      <div className="flex items-center gap-3 text-xs text-slate-500 mt-1 font-mono">
                        <span>{doc.chunk_count || 12} Chunks</span>
                        <span>•</span>
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <Link
                        href={`/materials/${doc.id}`}
                        className="py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold text-center transition-colors shadow-sm"
                      >
                        10-Pt Summary
                      </Link>
                      <button
                        disabled={generatingQuizDocId === doc.id}
                        onClick={() => handleGenerateQuiz(doc.id)}
                        className="py-2 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-bold text-center transition-colors disabled:opacity-50"
                      >
                        {generatingQuizDocId === doc.id ? "⌛ Quiz..." : "⚡ Quiz"}
                      </button>
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <Link
                        href={`/materials/${doc.id}#flashcards`}
                        className="text-xs text-indigo-500 hover:text-indigo-400 font-semibold"
                      >
                        🃏 View Flashcards →
                      </Link>
                      <button
                        onClick={() => {
                          if (window.confirm(`Delete "${doc.filename}"?`)) {
                            deleteMutation.mutate(doc.id);
                          }
                        }}
                        className="text-xs text-slate-400 hover:text-rose-500 transition-colors"
                        title="Delete Document"
                      >
                        🗑️
                      </button>
                    </div>
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
