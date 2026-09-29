"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/ui/AppShell";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/Toast";
import {
  fetchStudentProfile,
  updateStudentProfile,
  StudentProfileData,
} from "@/lib/api-client";

export default function ProfilePage() {
  const { user, token } = useAuth();
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const [institution, setInstitution] = useState<string>("");
  const [degree, setDegree] = useState<string>("");
  const [branch, setBranch] = useState<string>("");
  const [semester, setSemester] = useState<string>("");
  const [timezone, setTimezone] = useState<string>("");

  const { data: profile, isLoading } = useQuery<StudentProfileData>({
    queryKey: ["studentProfile"],
    queryFn: () => fetchStudentProfile(token!),
    enabled: !!token,
  });

  useEffect(() => {
    if (profile) {
      setInstitution(profile.institution || "");
      setDegree(profile.degree || "");
      setBranch(profile.branch || "");
      setSemester(profile.semester || "");
      setTimezone(profile.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
    }
  }, [profile]);

  const updateMutation = useMutation({
    mutationFn: () =>
      updateStudentProfile(token!, {
        institution,
        degree,
        branch,
        semester,
      }),
    onSuccess: () => {
      addToast("Academic profile updated successfully", "success");
      queryClient.invalidateQueries({ queryKey: ["studentProfile"] });
    },
    onError: (err: any) => {
      addToast(err?.message || "Failed to update profile", "error");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate();
  };

  return (
    <AppShell activeNav="profile">
      <div className="max-w-4xl mx-auto space-y-8 animate-fade-in pb-16">
        {/* Header */}
        <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
            Academic Profile
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Manage your university details, academic program, and course enrollment parameters.
          </p>
        </div>

        {isLoading ? (
          <SkeletonCard />
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Account Credentials Card */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>👤</span> Account Credentials
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-500 block mb-1.5">
                    Account Email
                  </label>
                  <input
                    type="text"
                    disabled
                    value={user?.email || ""}
                    className="w-full p-3 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-500 font-mono"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block">
                    Secured by MongoDB identity store & JWT authentication.
                  </span>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 block mb-1.5">
                    Display Name
                  </label>
                  <input
                    type="text"
                    disabled
                    value={user?.display_name || user?.full_name || ""}
                    className="w-full p-3 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium"
                  />
                </div>
              </div>
            </div>

            {/* Academic Information Card */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <span>🎓</span> University & Academic Track
                </h2>
                <Link
                  href="/onboarding"
                  className="text-xs font-bold text-indigo-500 hover:text-indigo-400 transition-colors"
                >
                  Re-run Discovery Wizard →
                </Link>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block mb-1.5">
                    University / College / Institution
                  </label>
                  <input
                    type="text"
                    value={institution}
                    onChange={(e) => setInstitution(e.target.value)}
                    placeholder="e.g. Stanford University, VTU, Mumbai University"
                    className="w-full p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block mb-1.5">
                      Degree / Program
                    </label>
                    <input
                      type="text"
                      value={degree}
                      onChange={(e) => setDegree(e.target.value)}
                      placeholder="e.g. B.Tech, B.S., M.S., High School"
                      className="w-full p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block mb-1.5">
                      Branch / Department
                    </label>
                    <input
                      type="text"
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      placeholder="e.g. Computer Science, Mechanical, Biology"
                      className="w-full p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block mb-1.5">
                      Current Semester / Level
                    </label>
                    <input
                      type="text"
                      value={semester}
                      onChange={(e) => setSemester(e.target.value)}
                      placeholder="e.g. Semester 5, Year 3"
                      className="w-full p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block mb-1.5">
                      Timezone
                    </label>
                    <input
                      type="text"
                      disabled
                      value={timezone}
                      className="w-full p-3 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-500 font-mono"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-end">
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50 inline-flex items-center gap-2"
                >
                  {updateMutation.isPending ? (
                    <>
                      <span className="animate-spin text-sm">⌛</span> Saving...
                    </>
                  ) : (
                    <>
                      <span>✓</span> Save Changes
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </AppShell>
  );
}
