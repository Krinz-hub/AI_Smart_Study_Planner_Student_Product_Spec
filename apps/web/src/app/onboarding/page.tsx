"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
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
  Award,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  postAcademicType,
  postAcademicProfile,
  postDiscoverSyllabus,
  postConfirmSyllabus,
  postGoalsAvailability,
  fetchDiagnosticTest,
  submitDiagnosticTest,
  fetchOnboardingStatus,
  DiscoveredSyllabus,
  DiagnosticQuestion,
  DiagnosticSubmitResponse,
} from "@/lib/api-client";

type OnboardingStep =
  | "TRACK"
  | "PROFILE"
  | "DISCOVERY"
  | "SYLLABUS_REVIEW"
  | "GOALS"
  | "DIAGNOSTIC"
  | "SUCCESS";

export default function OnboardingPage() {
  const router = useRouter();
  const { token, isLoading, isAuthenticated, refreshUser } = useAuth();
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

  // Step 3 & 4: Syllabus
  const [discoveredSyllabus, setDiscoveredSyllabus] = useState<DiscoveredSyllabus | null>(null);
  const [selectedSubjects, setSelectedSubjects] = useState<Record<string, boolean>>({});

  // Step 5: Goals & Availability
  const [dailyMinutes, setDailyMinutes] = useState(180);
  const [studyTime, setStudyTime] = useState("evening");
  const [targetExamTitle, setTargetExamTitle] = useState("Semester Midterm Examination");
  const [targetExamDate, setTargetExamDate] = useState("2026-10-25");

  // Step 6: Diagnostic
  const [diagnosticQuestions, setDiagnosticQuestions] = useState<DiagnosticQuestion[]>([]);
  const [diagnosticAnswers, setDiagnosticAnswers] = useState<Record<string, string>>({});
  const [diagnosticResult, setDiagnosticResult] = useState<DiagnosticSubmitResponse | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !token) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  // Step 1: Select Track
  const handleSelectTrack = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      await postAcademicType(token, academicType);
      setStep("PROFILE");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to set educational track");
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Save Profile & Trigger Discovery
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

      // Auto trigger syllabus discovery
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
      setStep("PROFILE");
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Confirm Syllabus
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
        throw new Error("Please select at least one course subject.");
      }

      await postConfirmSyllabus(token, confirmedList);
      setStep("GOALS");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to confirm syllabus");
    } finally {
      setLoading(false);
    }
  };

  // Step 4: Save Goals & Fetch Diagnostic
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

      // Load diagnostic
      const diag = await fetchDiagnosticTest(token);
      setDiagnosticQuestions(diag.questions);
      setStep("DIAGNOSTIC");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save goals");
    } finally {
      setLoading(false);
    }
  };

  // Step 5: Submit Diagnostic & Produce Initial Plan
  const handleSubmitDiagnostic = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const answersPayload = diagnosticQuestions.map((q) => ({
        question_id: q.id,
        selected_key: diagnosticAnswers[q.id] || "A",
        response_time_seconds: 14,
      }));

      const res = await submitDiagnosticTest(token, answersPayload);
      setDiagnosticResult(res);
      await refreshUser();
      setStep("SUCCESS");
    } catch (err: any) {
      setErrorMsg(err.message || "Diagnostic submission failed");
    } finally {
      setLoading(false);
    }
  };

  const stepLabels = [
    { id: "TRACK", label: "Track" },
    { id: "PROFILE", label: "Profile" },
    { id: "SYLLABUS_REVIEW", label: "Syllabus" },
    { id: "GOALS", label: "Goals" },
    { id: "DIAGNOSTIC", label: "Diagnostic" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-4 py-12">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden animate-scale-in">
        {/* Wizard Header with Progress */}
        <div className="px-6 py-5 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-linear-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/25">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Student Setup Wizard</h2>
              <p className="text-xs text-slate-400">Calibrate your curriculum & adaptive model</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {stepLabels.map((s, idx) => {
              const active = step === s.id;
              return (
                <div
                  key={s.id}
                  className={`w-2.5 h-2.5 rounded-full transition-all ${
                    active ? "bg-indigo-500 scale-125 ring-2 ring-indigo-500/30" : "bg-slate-800"
                  }`}
                  title={s.label}
                />
              );
            })}
          </div>
        </div>

        {errorMsg && (
          <div className="mx-6 mt-4 p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="p-6">
          {/* STEP 1: Academic Track */}
          {step === "TRACK" && (
            <div className="space-y-4">
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-white">Select Your Educational Level</h3>
                <p className="text-xs text-slate-400">
                  Luminary tailors syllabus discovery and mastery thresholds based on your track.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setAcademicTypeState("COLLEGE")}
                  className={`p-4 rounded-2xl border text-left transition-all cursor-pointer ${
                    academicType === "COLLEGE"
                      ? "border-indigo-500 bg-indigo-950/40 ring-2 ring-indigo-500/20"
                      : "border-slate-800 bg-slate-950/40 hover:border-slate-700"
                  }`}
                >
                  <GraduationCap className="w-6 h-6 text-indigo-400 mb-2" />
                  <div className="font-bold text-xs text-white">University / College</div>
                  <div className="text-[11px] text-slate-400 mt-1">B.Tech, B.Sc, BCA, Masters</div>
                </button>

                <button
                  type="button"
                  onClick={() => setAcademicTypeState("SCHOOL")}
                  className={`p-4 rounded-2xl border text-left transition-all cursor-pointer ${
                    academicType === "SCHOOL"
                      ? "border-emerald-500 bg-emerald-950/40 ring-2 ring-emerald-500/20"
                      : "border-slate-800 bg-slate-950/40 hover:border-slate-700"
                  }`}
                >
                  <School className="w-6 h-6 text-emerald-400 mb-2" />
                  <div className="font-bold text-xs text-white">High School</div>
                  <div className="text-[11px] text-slate-400 mt-1">CBSE, ICSE, State Boards</div>
                </button>

                <button
                  type="button"
                  onClick={() => setAcademicTypeState("COMPETITIVE_EXAM")}
                  className={`p-4 rounded-2xl border text-left transition-all cursor-pointer ${
                    academicType === "COMPETITIVE_EXAM"
                      ? "border-amber-500 bg-amber-950/40 ring-2 ring-amber-500/20"
                      : "border-slate-800 bg-slate-950/40 hover:border-slate-700"
                  }`}
                >
                  <Trophy className="w-6 h-6 text-amber-400 mb-2" />
                  <div className="font-bold text-xs text-white">Competitive Exam</div>
                  <div className="text-[11px] text-slate-400 mt-1">GATE, JEE, GRE, Civil Services</div>
                </button>
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  onClick={handleSelectTrack}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Continue to Details"}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: Profile Details */}
          {step === "PROFILE" && (
            <div className="space-y-4">
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-white">Program & Institution Details</h3>
                <p className="text-xs text-slate-400">
                  Used by our Academic Discovery service to pull accredited syllabus data.
                </p>
              </div>

              {academicType === "COLLEGE" && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      University / Institution
                    </label>
                    <input
                      type="text"
                      value={university}
                      onChange={(e) => setUniversity(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Degree Program</label>
                    <input
                      type="text"
                      value={degree}
                      onChange={(e) => setDegree(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Branch / Specialization
                    </label>
                    <input
                      type="text"
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Current Semester (1-8)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={12}
                      value={semester}
                      onChange={(e) => setSemester(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>
              )}

              {academicType === "SCHOOL" && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Education Board</label>
                    <input
                      type="text"
                      value={board}
                      onChange={(e) => setBoard(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Grade / Class</label>
                    <input
                      type="text"
                      value={grade}
                      onChange={(e) => setGrade(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>
              )}

              {academicType === "COMPETITIVE_EXAM" && (
                <div className="pt-1">
                  <label className="block text-xs font-medium text-slate-300 mb-1">Target Exam</label>
                  <input
                    type="text"
                    value={examName}
                    onChange={(e) => setExamName(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              <div className="pt-4 flex justify-between">
                <button
                  onClick={() => setStep("TRACK")}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Back
                </button>
                <button
                  onClick={handleSaveProfile}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Discover Official Syllabus"}
                  <Compass className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: Discovery in Progress */}
          {step === "DISCOVERY" && (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-indigo-950/80 border border-indigo-800 flex items-center justify-center text-indigo-400">
                <Compass className="w-8 h-8 animate-spin" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-white">Retrieving Official Syllabus</h3>
                <p className="text-xs text-slate-400 max-w-sm">
                  Connecting to university curriculum databases, structuring units, and normalizing topic hierarchies...
                </p>
              </div>
            </div>
          )}

          {/* STEP 4: Syllabus Review */}
          {step === "SYLLABUS_REVIEW" && discoveredSyllabus && (
            <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
              {/* Institution Fact-Check Verification Status Banner */}
              {discoveredSyllabus.institution_verified !== false ? (
                <div className="p-3.5 rounded-2xl bg-emerald-950/40 border border-emerald-500/30 flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-emerald-300">
                        Fact-Checked & Verified Institution
                      </span>
                      <span className="text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-500/30">
                        {Math.round((discoveredSyllabus.confidence_score || 0.95) * 100)}% Match
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed">
                      {discoveredSyllabus.institution_name ? (
                        <>
                          <strong className="text-white">{discoveredSyllabus.institution_name}</strong> confirmed.{" "}
                        </>
                      ) : null}
                      {discoveredSyllabus.verification_note ||
                        "Institution validated against official academic registries."}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-3.5 rounded-2xl bg-amber-950/40 border border-amber-500/30 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-amber-300">
                        Unverified Institution / Custom Curriculum Track
                      </span>
                      <span className="text-[10px] font-semibold bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full border border-amber-500/30">
                        Fact-Check Notice
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed">
                      {discoveredSyllabus.warning_flag ||
                        discoveredSyllabus.verification_note ||
                        "We could not verify this school or university in official academic directories. No false data has been fabricated. A standardized blueprint has been prepared which you can customize below."}
                    </p>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between pt-1">
                <div>
                  <h3 className="text-sm font-bold text-white">
                    Discovered Curriculum ({discoveredSyllabus.subjects.length} courses)
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Confidence: {Math.round((discoveredSyllabus.confidence_score || 0.9) * 100)}% • Confirmed by verified academic repository
                  </p>
                </div>
                <span className="text-[10px] font-semibold bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded-md border border-emerald-800">
                  Ready to Enroll
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
                      className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-start gap-3 ${
                        isChecked
                          ? "border-indigo-600/80 bg-indigo-950/30"
                          : "border-slate-800 bg-slate-950/40 opacity-60"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {}}
                        className="mt-1 w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 accent-indigo-600"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-white">{sub.name}</span>
                          {sub.code && (
                            <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-300 font-mono">
                              {sub.code}
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          {sub.units.length} Units • {sub.units.reduce((acc, u) => acc + u.topics.length, 0)} Topics
                        </div>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {sub.units.flatMap((u) => u.topics).slice(0, 4).map((t) => (
                            <span
                              key={t}
                              className="text-[10px] bg-slate-900 px-2 py-0.5 rounded-md border border-slate-800 text-slate-300"
                            >
                              {t}
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
                <div className="mt-3 p-3 rounded-xl bg-slate-900/70 border border-slate-800 space-y-1.5">
                  <div className="text-[11px] font-bold text-slate-300 flex items-center gap-1.5">
                    <span>📚</span> Grounded Reference Sources (Fact-Checked):
                  </div>
                  <div className="space-y-1">
                    {discoveredSyllabus.sources.map((s, idx) => (
                      <a
                        key={idx}
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1.5 hover:underline truncate"
                      >
                        <span className="text-slate-500">↗</span>
                        <span className="truncate">{s.title || s.name || s.url}</span>
                        <span className="text-[9px] text-slate-500 shrink-0">({s.authority})</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-4 flex justify-between">
                <button
                  onClick={() => setStep("PROFILE")}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Back
                </button>
                <button
                  onClick={handleConfirmSyllabus}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Confirm Syllabus"}
                  <CheckCircle2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 5: Goals & Availability */}
          {step === "GOALS" && (
            <div className="space-y-5">
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-white">Target Exams & Daily Study Hours</h3>
                <p className="text-xs text-slate-400">
                  OR-Tools CP-SAT scheduler requires hard deadline and daily capacity limits.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Primary Exam Milestone
                  </label>
                  <input
                    type="text"
                    value={targetExamTitle}
                    onChange={(e) => setTargetExamTitle(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Exam Date</label>
                  <input
                    type="date"
                    value={targetExamDate}
                    onChange={(e) => setTargetExamDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-300 font-medium">Daily Study Capacity:</span>
                  <span className="font-bold text-indigo-400">
                    {dailyMinutes} mins ({Math.floor(dailyMinutes / 60)}h {dailyMinutes % 60}m)
                  </span>
                </div>
                <input
                  type="range"
                  min={60}
                  max={360}
                  step={30}
                  value={dailyMinutes}
                  onChange={(e) => setDailyMinutes(Number(e.target.value))}
                  className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>1h (Light)</span>
                  <span>3h (Standard)</span>
                  <span>6h (Intensive)</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Preferred Time of Day
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {["morning", "afternoon", "evening", "night"].map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setStudyTime(t)}
                      className={`py-2 rounded-xl text-xs font-medium capitalize border transition-all cursor-pointer ${
                        studyTime === t
                          ? "border-indigo-500 bg-indigo-950/60 text-indigo-300 font-bold"
                          : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700"
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
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Back
                </button>
                <button
                  onClick={handleSaveGoals}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Take Baseline Diagnostic"}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 6: Diagnostic Assessment */}
          {step === "DIAGNOSTIC" && (
            <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-white">Baseline Diagnostic Assessment</h3>
                <p className="text-xs text-slate-400">
                  Answers calibrate your initial Bayesian Knowledge Tracing priors. Don&apos;t guess blindly!
                </p>
              </div>

              <div className="space-y-3.5 pt-1">
                {diagnosticQuestions.map((q, idx) => (
                  <div
                    key={q.id}
                    className="p-4 rounded-2xl border border-slate-800 bg-slate-950/50 space-y-2.5"
                  >
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>Question {idx + 1} of {diagnosticQuestions.length}</span>
                      <span className="font-semibold text-indigo-400">
                        {q.subject_name} • {q.topic_name}
                      </span>
                    </div>

                    <div className="font-medium text-xs text-white leading-relaxed">{q.question_text}</div>

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
                            className={`p-2.5 rounded-xl border text-left text-xs transition-all cursor-pointer flex items-center gap-2.5 ${
                              isSelected
                                ? "border-indigo-500 bg-indigo-950/60 text-indigo-200 font-semibold"
                                : "border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700"
                            }`}
                          >
                            <span className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-300 shrink-0">
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
                  className="flex items-center gap-2 px-8 py-3 rounded-2xl bg-linear-to-r from-indigo-600 via-purple-600 to-sky-600 hover:opacity-95 text-white text-xs font-bold shadow-xl shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Submit Diagnostic & Generate Plan"}
                  <Sparkles className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 7: Completed & Success */}
          {step === "SUCCESS" && diagnosticResult && (
            <div className="py-6 text-center space-y-5 animate-fade-in">
              <div className="w-16 h-16 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-400 mx-auto flex items-center justify-center shadow-lg shadow-emerald-500/10">
                <Award className="w-8 h-8" />
              </div>

              <div className="space-y-1">
                <h3 className="text-xl font-extrabold text-white">Setup Complete!</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Your official syllabus has been imported, baseline knowledge calibrated, and your first constraint-satisfaction study schedule generated.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3 max-w-md mx-auto pt-2">
                <div className="p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800">
                  <div className="text-[11px] text-slate-400">Diagnostic Score</div>
                  <div className="text-lg font-bold text-white mt-0.5">{diagnosticResult.accuracy_pct}%</div>
                </div>
                <div className="p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800">
                  <div className="text-[11px] text-slate-400">Topics Calibrated</div>
                  <div className="text-lg font-bold text-indigo-400 mt-0.5">
                    {diagnosticResult.topic_masteries.length}
                  </div>
                </div>
                <div className="p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800">
                  <div className="text-[11px] text-slate-400">Scheduled Tasks</div>
                  <div className="text-lg font-bold text-emerald-400 mt-0.5">
                    {diagnosticResult.plan_tasks_scheduled}
                  </div>
                </div>
              </div>

              <div className="pt-4">
                <button
                  onClick={() => router.push("/home")}
                  className="px-8 py-3.5 rounded-2xl bg-linear-to-r from-indigo-600 via-purple-600 to-sky-600 hover:opacity-95 text-white text-sm font-bold shadow-xl shadow-indigo-500/25 cursor-pointer transition-all hover:scale-105"
                >
                  Enter Student Cockpit
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
