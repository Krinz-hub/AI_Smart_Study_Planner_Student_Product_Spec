"use client";

import React from "react";
import Link from "next/link";
import {
  Sparkles,
  Calendar,
  BookOpen,
  Brain,
  MessageSquare,
  FileText,
  BarChart3,
  Terminal,
  LogOut,
  Flame,
  User as UserIcon,
} from "lucide-react";

export type StudentTab =
  | "home"
  | "plan"
  | "subjects"
  | "flashcards"
  | "tutor"
  | "materials"
  | "progress";

interface StudentNavbarProps {
  activeTab: StudentTab;
  onTabChange: (tab: StudentTab) => void;
  userName?: string;
  academicSummary?: string;
  streakDays?: number;
  onSignOut?: () => void;
  onOpenOnboarding?: () => void;
}

export function StudentNavbar({
  activeTab,
  onTabChange,
  userName = "Student",
  academicSummary = "Personalized Learning",
  streakDays = 1,
  onSignOut,
  onOpenOnboarding,
}: StudentNavbarProps) {
  const navItems: Array<{ id: StudentTab; label: string; icon: React.ReactNode }> = [
    { id: "home", label: "Home", icon: <Sparkles className="w-4 h-4" /> },
    { id: "plan", label: "My Plan", icon: <Calendar className="w-4 h-4" /> },
    { id: "subjects", label: "Subjects", icon: <BookOpen className="w-4 h-4" /> },
    { id: "flashcards", label: "Flashcards", icon: <Brain className="w-4 h-4" /> },
    { id: "tutor", label: "AI Tutor", icon: <MessageSquare className="w-4 h-4" /> },
    { id: "materials", label: "Materials", icon: <FileText className="w-4 h-4" /> },
    { id: "progress", label: "Progress", icon: <BarChart3 className="w-4 h-4" /> },
  ];

  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-white/85 dark:bg-slate-900/85 border-b border-slate-200/80 dark:border-slate-800/80 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => onTabChange("home")}
              className="flex items-center gap-2.5 group cursor-pointer focus:outline-hidden"
            >
              <div className="w-9 h-9 rounded-xl bg-linear-to-tr from-indigo-600 via-purple-600 to-sky-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-200">
                <Sparkles className="w-5 h-5 animate-pulse" />
              </div>
              <div className="text-left">
                <div className="font-bold text-base bg-linear-to-r from-slate-900 via-indigo-950 to-indigo-700 dark:from-white dark:via-slate-100 dark:to-indigo-300 bg-clip-text text-transparent leading-none">
                  Luminary
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                  Smart Study Planner
                </div>
              </div>
            </button>

            {academicSummary && (
              <span className="hidden md:inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200/60 dark:border-indigo-800/60 max-w-xs truncate">
                {academicSummary}
              </span>
            )}
          </div>

          {/* Primary Navigation Pills */}
          <nav className="hidden lg:flex items-center gap-1 bg-slate-100/70 dark:bg-slate-800/60 p-1 rounded-xl border border-slate-200/60 dark:border-slate-700/60">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 cursor-pointer ${
                    isActive
                      ? "bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs border border-slate-200/60 dark:border-slate-800"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-white/50 dark:hover:bg-slate-800/50"
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Right Action Icons & Badges */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Streak Badge */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200/60 dark:border-amber-800/60 text-amber-700 dark:text-amber-400 text-xs font-semibold">
              <Flame className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
              <span>{streakDays}d Streak</span>
            </div>

            {/* Re-open Onboarding Button */}
            {onOpenOnboarding && (
              <button
                onClick={onOpenOnboarding}
                className="hidden sm:inline-flex items-center text-xs font-medium text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 px-2 py-1 transition-colors"
                title="Syllabus & Setup Wizard"
              >
                Setup Wizard
              </button>
            )}

            {/* Admin Console Link */}
            <Link
              href="/admin"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-medium transition-colors border border-slate-200/80 dark:border-slate-700/80"
              title="Inspect low-level BKT, FSRS, and OR-Tools solvers"
            >
              <Terminal className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
              <span className="hidden sm:inline">Admin Console</span>
            </Link>

            {/* User Profile / Logout */}
            <div className="flex items-center gap-2 pl-1 border-l border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-300">
                <div className="w-7 h-7 rounded-full bg-linear-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[11px] font-bold shadow-xs">
                  {userName.charAt(0).toUpperCase()}
                </div>
                <span className="hidden md:inline max-w-[100px] truncate">{userName}</span>
              </div>

              {onSignOut && (
                <button
                  onClick={onSignOut}
                  className="p-1.5 text-slate-400 hover:text-rose-500 dark:text-slate-500 dark:hover:text-rose-400 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Mobile Navigation Bar */}
        <div className="lg:hidden flex items-center justify-around py-2 border-t border-slate-200/60 dark:border-slate-800/60 overflow-x-auto">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`flex flex-col items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  isActive
                    ? "text-indigo-600 dark:text-indigo-400"
                    : "text-slate-500 dark:text-slate-400 hover:text-slate-800"
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
