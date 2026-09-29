"use client";

import React, { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/ui/AppShell";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import {
  fetchSubjects,
  fetchTopics,
  askTutor,
  SubjectItem,
  TopicItem,
  TutorResponse,
} from "@/lib/api-client";

interface ChatMessage {
  id: string;
  sender: "user" | "tutor";
  text: string;
  mode?: string;
  sources?: TutorResponse["sources"];
  evidenceSufficiency?: string;
  pedagogicalIntent?: string;
  suggestedFollowups?: string[];
  timestamp: string;
}

export default function TutorPage() {
  const { token, user } = useAuth();
  const { addToast } = useToast();

  const [selectedSubjectId, setSelectedSubjectId] = useState<string>("");
  const [selectedTopicId, setSelectedTopicId] = useState<string>("");
  const [activeMode, setActiveMode] = useState<string>("socratic");
  const [inputMessage, setInputMessage] = useState<string>("");
  const [isSending, setIsSending] = useState<boolean>(false);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "intro",
      sender: "tutor",
      text: `Hello ${user?.display_name || "Scholar"}! I'm your grounded AI Study Tutor. Select a subject and topic from your curriculum above, choose an instructional mode, and ask me anything about core concepts, tricky proofs, or exam problem-solving!`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  // Auto-select first subject/topic if available
  useEffect(() => {
    if (subjects && subjects.length > 0 && !selectedSubjectId) {
      setSelectedSubjectId(subjects[0].id);
    }
  }, [subjects, selectedSubjectId]);

  useEffect(() => {
    if (topics && topics.length > 0 && !selectedTopicId) {
      setSelectedTopicId(topics[0].id);
    }
  }, [topics, selectedTopicId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  const handleSendMessage = async (textToSend?: string) => {
    const message = (textToSend || inputMessage).trim();
    if (!message) return;
    if (!selectedTopicId) {
      addToast("Please select a topic to provide curriculum context to the tutor", "error");
      return;
    }

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: message,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputMessage("");
    setIsSending(true);

    try {
      const res = await askTutor(token!, selectedTopicId, message, activeMode);
      const tutorMsg: ChatMessage = {
        id: `tutor-${Date.now()}`,
        sender: "tutor",
        text: res.response_text,
        mode: res.mode,
        sources: res.sources,
        evidenceSufficiency: res.evidence_sufficiency,
        pedagogicalIntent: res.pedagogical_intent,
        suggestedFollowups: res.suggested_followups,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, tutorMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: "tutor",
        text: `⚠️ ${
          err?.message ||
          "I couldn't process this request. If the Gemini AI key is not yet configured, I will operate in grounded curriculum mode."
        }`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const modes = [
    { key: "socratic", label: "Socratic Dialog", icon: "🏛️", desc: "Guides through guided questioning" },
    { key: "eli5", label: "ELI5 Analogy", icon: "🌱", desc: "Simple intuitive explanations" },
    { key: "deep_dive", label: "Deep Dive", icon: "🔬", desc: "Rigorous proofs & mechanics" },
    { key: "exam_rubric", label: "Exam Rubric", icon: "📝", desc: "Model answers & marking points" },
    { key: "hint", label: "Step Hint", icon: "💡", desc: "Next step without spoiler" },
  ];

  return (
    <AppShell activeNav="tutor">
      <div className="max-w-5xl mx-auto h-[calc(100vh-140px)] flex flex-col space-y-4 animate-fade-in">
        {/* Top Context & Mode Bar */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-500 font-bold flex items-center justify-center">
                🤖
              </span>
              <div>
                <h1 className="text-base font-bold text-slate-900 dark:text-white">
                  Socratic AI Tutor
                </h1>
                <p className="text-[11px] text-slate-500">
                  Grounded strictly in your syllabus and verified study materials.
                </p>
              </div>
            </div>

            {/* Subject and Topic Pickers */}
            <div className="flex items-center gap-2">
              <select
                value={selectedSubjectId}
                onChange={(e) => {
                  setSelectedSubjectId(e.target.value);
                  setSelectedTopicId("");
                }}
                className="px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                {subjects?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>

              <select
                value={selectedTopicId}
                onChange={(e) => setSelectedTopicId(e.target.value)}
                disabled={!topics || topics.length === 0}
                className="px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 max-w-[200px] truncate"
              >
                {topics?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Mode Pill Badges */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 pt-1 scrollbar-none">
            {modes.map((m) => {
              const isActive = activeMode === m.key;
              return (
                <button
                  key={m.key}
                  type="button"
                  onClick={() => setActiveMode(m.key)}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                    isActive
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                  }`}
                  title={m.desc}
                >
                  <span>{m.icon}</span>
                  <span>{m.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Chat Messages Scrollable Box */}
        <div className="flex-1 bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-3xl p-4 sm:p-6 overflow-y-auto space-y-5 shadow-inner">
          {messages.map((msg) => {
            const isUser = msg.sender === "user";
            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-3xl ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                    isUser
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-200 dark:bg-slate-800 text-indigo-500"
                  }`}
                >
                  {isUser ? "👤" : "🤖"}
                </div>

                <div className="space-y-2 max-w-[85%] sm:max-w-[78%]">
                  <div
                    className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed shadow-sm ${
                      isUser
                        ? "bg-indigo-600 text-white rounded-tr-none"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-tl-none border border-slate-200/50 dark:border-slate-700/40"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                  </div>

                  {/* Grounding Citations if present */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/40 text-[11px] space-y-1">
                      <span className="font-bold text-slate-500 block uppercase tracking-wider text-[9px]">
                        📚 Grounded Sources Used:
                      </span>
                      {msg.sources.map((s, idx) => (
                        <div key={idx} className="text-slate-600 dark:text-slate-300">
                          • <strong>{s.document_title}</strong> {s.page_number ? `(p. ${s.page_number})` : ""}:
                          <span className="italic text-slate-400 block pl-2 font-mono text-[10px]">
                            &ldquo;{s.snippet.slice(0, 140)}...&rdquo;
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Suggested Followups */}
                  {msg.suggestedFollowups && msg.suggestedFollowups.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {msg.suggestedFollowups.map((followup, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleSendMessage(followup)}
                          className="px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 border border-indigo-200 dark:border-indigo-800/40 text-[11px] text-indigo-600 dark:text-indigo-400 text-left transition-colors"
                        >
                          💬 {followup}
                        </button>
                      ))}
                    </div>
                  )}

                  <span className="text-[10px] text-slate-400 block px-1">
                    {msg.timestamp} {msg.mode ? `• ${msg.mode.toUpperCase()}` : ""}
                  </span>
                </div>
              </div>
            );
          })}

          {isSending && (
            <div className="flex gap-3 max-w-md mr-auto">
              <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-800 text-indigo-500 flex items-center justify-center text-xs">
                🤖
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-500 rounded-tl-none text-xs flex items-center gap-2">
                <span className="animate-spin text-sm">⏳</span>
                <span>Thinking through curriculum knowledge graph...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-3 shadow-sm flex items-end gap-3">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask a question in ${activeMode.toUpperCase()} mode (Press Enter to send)...`}
            rows={2}
            className="flex-1 bg-transparent resize-none text-xs sm:text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none"
          />
          <button
            disabled={!inputMessage.trim() || isSending}
            onClick={() => handleSendMessage()}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/20 disabled:opacity-40 inline-flex items-center gap-1.5 self-end"
          >
            <span>Send</span> <span>↑</span>
          </button>
        </div>
      </div>
    </AppShell>
  );
}
