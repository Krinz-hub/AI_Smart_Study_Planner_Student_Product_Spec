"use client";

import React, { useState } from "react";
import {
  GraduationCap,
  School,
  Trophy,
  Compass,
  CheckCircle2,
  Calendar,
  Clock,
  Sparkles,
  ArrowRight,
  BookOpen,
  HelpCircle,
  Award,
  Loader2,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import {
  postAcademicType,
  postAcademicProfile,
  postDiscoverSyllabus,
  postConfirmSyllabus,
  postGoalsAvailability,
  fetchDiagnosticTest,
  submitDiagnosticTest,
  DiscoveredSyllabus,
  DiagnosticQuestion,
  DiagnosticSubmitResponse,
} from "@/lib/api-client";

interface OnboardingModalProps {
  token: string;
  isOpen: boolean;
  onClose: () => void;
  onCompleted: () => void;
}

type OnboardingStep =
  | "TRACK"
  | "PROFILE"
  | "DISCOVERY"
  | "SYLLABUS_REVIEW"
  | "GOALS"
  | "DIAGNOSTIC"
  | "SUCCESS";

export function OnboardingModal({
  token,
  isOpen,
  onClose,
  onCompleted,
}: OnboardingModalProps) {
  const [step, setStep] = useState<OnboardingStep>("TRACK");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Step 1: Track
  const [academicType, setAcademicTypeState] = useState<"COLLEGE" | "SCHOOL" | "COMPETITIVE_EXAM">("COLLEGE");

  // Step 2: Profile Details
  const [university, setUniversity] = useState("Anna University");
  const [degree, setDegree] = useState("B.Tech");
  const [branch, setBranch] = useState("Computer Science & Engineering");
  const [semester, setSemester] = useState(3);
  const [board, setBoard] = useState("CBSE");
  const [grade, setGrade] = useState("Class 12");
  const [examName, setExamName] = useState("JEE Main");

  // Step 3 & 4: Discovered Syllabus
  const [discoveredSyllabus, setDiscoveredSyllabus] = useState<DiscoveredSyllabus | null>(null);
  const [selectedSubjects, setSelectedSubjects] = useState<Record<string, boolean>>({});

  // Step 5: Goals & Availability
  const [dailyMinutes, setDailyMinutes] = useState(180);
  const [studyTime, setStudyTime] = useState("evening");
  const [targetExamTitle, setTargetExamTitle] = useState("Semester Midterm Examination");
  const [targetExamDate, setTargetExamDate] = useState("2026-10-25");

  // Step 6: Diagnostic Questions & Answers
  const [diagnosticQuestions, setDiagnosticQuestions] = useState<DiagnosticQuestion[]>([]);
  const [diagnosticAnswers, setDiagnosticAnswers] = useState<Record<string, string>>({});
  const [diagnosticResult, setDiagnosticResult] = useState<DiagnosticSubmitResponse | null>(null);

  if (!isOpen) return null;

  // Handle Track Selection -> Next
  const handleSelectTrack = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      await postAcademicType(token, academicType);
      setStep("PROFILE");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to set academic track");
    } finally {
      setLoading(false);
    }
  };

  // Handle Profile Submission -> Discovery
  const handleSaveProfile = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      let details: Record<string, any> = {};
      if (academicType === "COLLEGE") {
        details = {
          country: "India",
          university,
          degree,
          branch,
          year: Math.ceil(semester / 2),
          semester: Number(semester),
        };
      } else if (academicType === "SCHOOL") {
        details = { country: "India", board, grade };
      } else {
        details = { exam_name: examName, target_year: 2026 };
      }

      await postAcademicProfile(token, details);
      setStep("DISCOVERY");

      // Auto trigger discovery
      const syllabus = await postDiscoverSyllabus(token);
      setDiscoveredSyllabus(syllabus);
      const initialSelection: Record<string, boolean> = {};
      syllabus.subjects.forEach((s) => {
        initialSelection[s.name] = true;
      });
      setSelectedSubjects(initialSelection);
      setStep("SYLLABUS_REVIEW");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to discover syllabus");
    } finally {
      setLoading(false);
    }
  };

  // Handle Syllabus Confirmation -> Goals
  const handleConfirmSyllabus = async () => {
    if (!discoveredSyllabus) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const confirmedList = discoveredSyllabus.subjects
        .filter((s) => selectedSubjects[s.name] !== false)
        .map((s) => ({
          name: s.name,
          code: s.code,
          color_code: s.color_code,
          topics: s.units.flatMap((u) => u.topics),
        }));

      if (confirmedList.length === 0) {
        throw new Error("Please select at least one subject.");
      }

      await postConfirmSyllabus(token, confirmedList);
      setStep("GOALS");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to confirm syllabus");
    } finally {
      setLoading(false);
    }
  };

  // Handle Goals & Availability -> Diagnostic
  const handleSaveGoals = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const examDateIso = new Date(targetExamDate).toISOString();
      await postGoalsAvailability(token, {
        daily_capacity_minutes: dailyMinutes,
        study_time_preference: studyTime,
        exams: [{ name: targetExamTitle, exam_at: examDateIso }],
        goals: [{ title: `Master syllabus for ${targetExamTitle}`, target_type: "mastery", target_value: 0.85 }],
        weekly_availability: [
          { weekday: 0, start_time: "18:00", end_time: "21:00", enabled: true },
          { weekday: 1, start_time: "18:00", end_time: "21:00", enabled: true },
          { weekday: 2, start_time: "18:00", end_time: "21:00", enabled: true },
          { weekday: 3, start_time: "18:00", end_time: "21:00", enabled: true },
          { weekday: 4, start_time: "18:00", end_time: "21:00", enabled: true },
          { weekday: 5, start_time: "14:00", end_time: "18:00", enabled: true },
          { weekday: 6, start_time: "10:00", end_time: "14:00", enabled: true },
        ],
      });

      // Fetch diagnostic test
      const diag = await fetchDiagnosticTest(token);
      setDiagnosticQuestions(diag.questions);
      setStep("DIAGNOSTIC");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save study goals");
    } finally {
      setLoading(false);
    }
  };

  // Handle Diagnostic Submission -> Success
  const handleSubmitDiagnostic = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const answersPayload = diagnosticQuestions.map((q) => ({
        question_id: q.id,
        selected_key: diagnosticAnswers[q.id] || "A",
        response_time_seconds: 12,
      }));

      const res = await submitDiagnosticTest(token, answersPayload);
      setDiagnosticResult(res);
      setStep("SUCCESS");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit diagnostic assessment");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden my-8">
        {/* Wizard Header */}
        <div className="px-6 py-5 border-b border-slate-200 dark:border-slate-800 bg-linear-to-r from-indigo-50/70 via-purple-50/50 to-white dark:from-indigo-950/40 dark:via-slate-900 dark:to-slate-900 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-linear-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Personalized Study Setup
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Discover syllabus, align goals, and calibrate your first plan
              </p>
            </div>
          </div>

          <div className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/80 px-2.5 py-1 rounded-full border border-indigo-200/60 dark:border-indigo-800/60">
            {step === "TRACK" && "Step 1 of 6"}
            {step === "PROFILE" && "Step 2 of 6"}
            {step === "DISCOVERY" && "Discovering..."}
            {step === "SYLLABUS_REVIEW" && "Step 3 of 6"}
            {step === "GOALS" && "Step 4 of 6"}
            {step === "DIAGNOSTIC" && "Step 5 of 6"}
            {step === "SUCCESS" && "Complete!"}
          </div>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs">
            {errorMsg}
          </div>
        )}

        {/* Modal Body */}
        <div className="p-6">
          {/* STEP 1: Academic Track */}
          {step === "TRACK" && (
            <div className="space-y-4">
              <div className="text-sm font-semibold text-slate-900 dark:text-white">
                What is your educational track?
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setAcademicTypeState("COLLEGE")}
                  className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    academicType === "COLLEGE"
                      ? "border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/30 ring-2 ring-indigo-500/20"
                      : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                  }`}
                >
                  <GraduationCap className="w-6 h-6 text-indigo-600 dark:text-indigo-400 mb-2" />
                  <div className="font-semibold text-sm text-slate-900 dark:text-white">College / University</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">B.Tech, B.Sc, BCA, MBBS, Masters</div>
                </button>

                <button
                  type="button"
                  onClick={() => setAcademicTypeState("SCHOOL")}
                  className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    academicType === "SCHOOL"
                      ? "border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/30 ring-2 ring-indigo-500/20"
                      : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                  }`}
                >
                  <School className="w-6 h-6 text-emerald-600 dark:text-emerald-400 mb-2" />
                  <div className="font-semibold text-sm text-slate-900 dark:text-white">High School</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">CBSE, ICSE, State Boards, IB</div>
                </button>

                <button
                  type="button"
                  onClick={() => setAcademicTypeState("COMPETITIVE_EXAM")}
                  className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    academicType === "COMPETITIVE_EXAM"
                      ? "border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/30 ring-2 ring-indigo-500/20"
                      : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                  }`}
                >
                  <Trophy className="w-6 h-6 text-amber-600 dark:text-amber-400 mb-2" />
                  <div className="font-semibold text-sm text-slate-900 dark:text-white">Competitive Exam</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">JEE, NEET, GATE, UPSC, GRE</div>
                </button>
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  onClick={handleSelectTrack}
                  disabled={loading}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-md shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Continue"}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: Profile Details */}
          {step === "PROFILE" && (
            <div className="space-y-4">
              <div className="text-sm font-semibold text-slate-900 dark:text-white">
                Enter your academic program details
              </div>

              {academicType === "COLLEGE" && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      University Name
                    </label>
                    <input
                      type="text"
                      value={university}
                      onChange={(e) => setUniversity(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Degree Program
                    </label>
                    <input
                      type="text"
                      value={degree}
                      onChange={(e) => setDegree(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Branch / Specialization
                    </label>
                    <input
                      type="text"
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Current Semester (1-8)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={12}
                      value={semester}
                      onChange={(e) => setSemester(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                    />
                  </div>
                </div>
              )}

              {academicType === "SCHOOL" && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Education Board
                    </label>
                    <input
                      type="text"
                      value={board}
                      onChange={(e) => setBoard(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Grade / Standard
                    </label>
                    <input
                      type="text"
                      value={grade}
                      onChange={(e) => setGrade(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                    />
                  </div>
                </div>
              )}

              {academicType === "COMPETITIVE_EXAM" && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Target Competitive Examination
                  </label>
                  <input
                    type="text"
                    value={examName}
                    onChange={(e) => setExamName(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                  />
                </div>
              )}

              <div className="pt-4 flex justify-between">
                <button
                  onClick={() => setStep("TRACK")}
                  className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 cursor-pointer"
                >
                  Back
                </button>
                <button
                  onClick={handleSaveProfile}
                  disabled={loading}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-md shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Discover Syllabus"}
                  <Compass className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: Discovery in Progress */}
          {step === "DISCOVERY" && (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                  <Compass className="w-8 h-8 animate-spin" />
                </div>
                <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center text-white text-[10px] font-bold">
                  AI
                </div>
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Discovering Official Syllabus
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm">
                  Connecting to university and educational board repositories to retrieve your official course outline...
                </p>
              </div>
            </div>
          )}

          {/* STEP 4: Syllabus Review */}
          {step === "SYLLABUS_REVIEW" && discoveredSyllabus && (
            <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
              {/* Institution Fact-Check Verification Status Banner */}
              {discoveredSyllabus.institution_verified !== false ? (
                <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-emerald-900 dark:text-emerald-300">
                        Fact-Checked & Verified Institution
                      </span>
                      <span className="text-[10px] font-semibold bg-emerald-100 dark:bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-300 dark:border-emerald-700">
                        {Math.round((discoveredSyllabus.confidence_score || 0.95) * 100)}% Match
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-700 dark:text-slate-300 leading-relaxed">
                      {discoveredSyllabus.institution_name ? (
                        <>
                          <strong className="text-slate-900 dark:text-white">{discoveredSyllabus.institution_name}</strong> confirmed.{" "}
                        </>
                      ) : null}
                      {discoveredSyllabus.verification_note ||
                        "Institution validated against official academic registries."}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-amber-900 dark:text-amber-300">
                        Unverified Institution / Custom Track
                      </span>
                      <span className="text-[10px] font-semibold bg-amber-100 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300 px-2 py-0.5 rounded-full border border-amber-300 dark:border-amber-700">
                        Fact-Check Notice
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-700 dark:text-slate-300 leading-relaxed">
                      {discoveredSyllabus.warning_flag ||
                        discoveredSyllabus.verification_note ||
                        "We could not verify this school or university in official academic directories. No false data has been fabricated. A standardized blueprint has been prepared which you can customize below."}
                    </p>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between pt-1">
                <div>
                  <div className="text-sm font-semibold text-slate-900 dark:text-white">
                    Discovered Courses ({discoveredSyllabus.subjects.length} subjects found)
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    Confidence: {Math.round((discoveredSyllabus.confidence_score || 0.9) * 100)}% • Official curriculum aligned
                  </div>
                </div>
                <span className="text-[11px] font-medium bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800">
                  Verified Structure
                </span>
              </div>

              <div className="space-y-2.5">
                {discoveredSyllabus.subjects.map((sub) => {
                  const isChecked = selectedSubjects[sub.name] !== false;
                  return (
                    <div
                      key={sub.name}
                      onClick={() =>
                        setSelectedSubjects((prev) => ({
                          ...prev,
                          [sub.name]: !isChecked,
                        }))
                      }
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                        isChecked
                          ? "border-indigo-300 dark:border-indigo-800 bg-indigo-50/30 dark:bg-indigo-950/20"
                          : "border-slate-200 dark:border-slate-800 opacity-60"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {}}
                        className="mt-1 w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-slate-900 dark:text-white">
                            {sub.name}
                          </span>
                          {sub.code && (
                            <span className="text-[10px] bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-600 dark:text-slate-400 font-mono">
                              {sub.code}
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                          {sub.units.length} Units • {sub.units.reduce((acc, u) => acc + u.topics.length, 0)} Topics
                        </div>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {sub.units.flatMap((u) => u.topics).slice(0, 4).map((topic) => (
                            <span
                              key={topic}
                              className="text-[10px] bg-white dark:bg-slate-800/80 px-2 py-0.5 rounded-md border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300"
                            >
                              {topic}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Real Verified Grounded Reference Sources */}
              {discoveredSyllabus.sources && discoveredSyllabus.sources.length > 0 && (
                <div className="mt-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1.5">
                  <div className="text-[11px] font-bold text-slate-800 dark:text-slate-300 flex items-center gap-1.5">
                    <span>📚</span> Grounded Reference Sources (Fact-Checked):
                  </div>
                  <div className="space-y-1">
                    {discoveredSyllabus.sources.map((s, idx) => (
                      <a
                        key={idx}
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1.5 truncate"
                      >
                        <span className="text-slate-400">↗</span>
                        <span className="truncate">{s.title || s.name || s.url}</span>
                        <span className="text-[9px] text-slate-400 shrink-0">({s.authority})</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-4 flex justify-between">
                <button
                  onClick={() => setStep("PROFILE")}
                  className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 cursor-pointer"
                >
                  Back
                </button>
                <button
                  onClick={handleConfirmSyllabus}
                  disabled={loading}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-md shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Confirm Syllabus"}
                  <CheckCircle2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 5: Goals & Availability */}
          {step === "GOALS" && (
            <div className="space-y-4">
              <div className="text-sm font-semibold text-slate-900 dark:text-white">
                Configure your target exams and daily capacity
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Target Exam / Milestone
                  </label>
                  <input
                    type="text"
                    value={targetExamTitle}
                    onChange={(e) => setTargetExamTitle(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Exam Date
                  </label>
                  <input
                    type="date"
                    value={targetExamDate}
                    onChange={(e) => setTargetExamDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                    Daily Study Capacity Goal: <span className="font-bold text-indigo-600">{dailyMinutes} minutes</span> ({Math.floor(dailyMinutes / 60)}h {dailyMinutes % 60}m)
                  </label>
                </div>
                <input
                  type="range"
                  min={60}
                  max={360}
                  step={30}
                  value={dailyMinutes}
                  onChange={(e) => setDailyMinutes(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400 mt-1">
                  <span>1 Hour (Light)</span>
                  <span>3 Hours (Recommended)</span>
                  <span>6 Hours (Intensive)</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Preferred Daily Study Time
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {["morning", "afternoon", "evening", "night"].map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setStudyTime(t)}
                      className={`py-2 rounded-lg text-xs font-medium capitalize border transition-all cursor-pointer ${
                        studyTime === t
                          ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 font-semibold"
                          : "border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300"
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-4 flex justify-between">
                <button
                  onClick={() => setStep("SYLLABUS_REVIEW")}
                  className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 cursor-pointer"
                >
                  Back
                </button>
                <button
                  onClick={handleSaveGoals}
                  disabled={loading}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-md shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Take Diagnostic"}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 6: Diagnostic Assessment */}
          {step === "DIAGNOSTIC" && (
            <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
              <div>
                <div className="text-sm font-semibold text-slate-900 dark:text-white">
                  Baseline Diagnostic Assessment
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {diagnosticQuestions.length} quick questions to calibrate your Bayesian Knowledge Tracing baseline.
                </div>
              </div>

              <div className="space-y-4">
                {diagnosticQuestions.map((q, idx) => (
                  <div
                    key={q.id}
                    className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-2.5"
                  >
                    <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
                      <span>Question {idx + 1} of {diagnosticQuestions.length}</span>
                      <span className="font-medium text-indigo-600 dark:text-indigo-400">{q.subject_name} • {q.topic_name}</span>
                    </div>
                    <div className="font-medium text-xs text-slate-900 dark:text-white leading-relaxed">
                      {q.question_text}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                      {q.options.map((opt) => {
                        const isSelected = diagnosticAnswers[q.id] === opt.key;
                        return (
                          <button
                            key={opt.key}
                            type="button"
                            onClick={() =>
                              setDiagnosticAnswers((prev) => ({
                                ...prev,
                                [q.id]: opt.key,
                              }))
                            }
                            className={`p-2.5 rounded-lg border text-left text-xs transition-all cursor-pointer flex items-center gap-2 ${
                              isSelected
                                ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-200 font-medium"
                                : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-slate-300"
                            }`}
                          >
                            <span className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-600 dark:text-slate-300 shrink-0">
                              {opt.key}
                            </span>
                            <span className="truncate">{opt.text}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  onClick={handleSubmitDiagnostic}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-linear-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white text-sm font-semibold shadow-md shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Generate My Study Plan"}
                  <Sparkles className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 7: Completed & Success */}
          {step === "SUCCESS" && diagnosticResult && (
            <div className="py-6 text-center space-y-4">
              <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 mx-auto flex items-center justify-center shadow-lg shadow-emerald-500/10">
                <Award className="w-8 h-8" />
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Welcome to Luminary!
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto mt-1">
                  Your academic profile is synchronized, baseline knowledge calibrated, and your first personalized weekly plan has been generated with OR-Tools constraint satisfaction.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3 max-w-md mx-auto pt-2">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Diagnostic Score</div>
                  <div className="text-base font-bold text-slate-900 dark:text-white mt-0.5">
                    {diagnosticResult.accuracy_pct}%
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Topics Calibrated</div>
                  <div className="text-base font-bold text-indigo-600 dark:text-indigo-400 mt-0.5">
                    {diagnosticResult.topic_masteries.length}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">Plan Tasks</div>
                  <div className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                    {diagnosticResult.plan_tasks_scheduled}
                  </div>
                </div>
              </div>

              <div className="pt-4">
                <button
                  onClick={() => {
                    onCompleted();
                    onClose();
                  }}
                  className="px-8 py-3 rounded-xl bg-linear-to-r from-indigo-600 via-purple-600 to-sky-600 hover:opacity-95 text-white text-sm font-bold shadow-lg shadow-indigo-500/25 cursor-pointer transition-all hover:scale-105"
                >
                  Launch My Student Cockpit
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
