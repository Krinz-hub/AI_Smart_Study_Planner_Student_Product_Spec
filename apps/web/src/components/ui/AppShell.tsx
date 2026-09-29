"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Sparkles,
  Calendar,
  BookOpen,
  Brain,
  MessageSquare,
  FileText,
  BarChart3,
  Flame,
  LogOut,
  Settings,
  User as UserIcon,
  Layers,
  ChevronDown,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { ToastProvider } from "./Toast";
import { Skeleton } from "./Skeleton";

interface AppShellProps {
  children: React.ReactNode;
  activeNav?: string;
}

export function AppShell({ children, activeNav }: AppShellProps) {
  const { user, token, isLoading, isAuthenticated, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);

  // Protected route check
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-linear-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-xl shadow-indigo-500/25 animate-pulse">
          <Sparkles className="w-6 h-6" />
        </div>
        <div className="text-xs text-slate-400 font-medium">Loading your student cockpit...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  const navItems = [
    { href: "/home", label: "Home", icon: Sparkles },
    { href: "/plan", label: "My Plan", icon: Calendar },
    { href: "/subjects", label: "Subjects", icon: BookOpen },
    { href: "/practice", label: "Practice", icon: Brain },
    { href: "/tutor", label: "AI Tutor", icon: MessageSquare },
    { href: "/materials", label: "Materials", icon: FileText },
    { href: "/progress", label: "Progress", icon: BarChart3 },
  ];

  return (
    <ToastProvider>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col pb-20 lg:pb-0">
        {/* Sticky Desktop & Tablet Header */}
        <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-slate-950/85 border-b border-slate-800/80 shadow-xs">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              {/* Brand Logo */}
              <div className="flex items-center gap-3">
                <Link href="/home" className="flex items-center gap-2.5 group focus:outline-hidden">
                  <div className="w-9 h-9 rounded-xl bg-linear-to-tr from-indigo-600 via-purple-600 to-sky-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-200">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div className="text-left">
                    <div className="font-bold text-base bg-linear-to-r from-white via-slate-100 to-indigo-300 bg-clip-text text-transparent leading-none">
                      Luminary
                    </div>
                    <div className="text-[11px] text-slate-400 font-medium">Smart Study Planner</div>
                  </div>
                </Link>
              </div>

              {/* Desktop Navigation Links */}
              <nav className="hidden lg:flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                        isActive
                          ? "bg-slate-800 text-indigo-400 shadow-xs border border-slate-700/80 font-semibold"
                          : "text-slate-400 hover:text-white hover:bg-slate-850"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </nav>

              {/* Right Side Badges & Profile Dropdown */}
              <div className="flex items-center gap-2 sm:gap-3">
                {/* Streak Badge */}
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-400 text-xs font-semibold">
                  <Flame className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                  <span>3d Streak</span>
                </div>

                {/* Profile / Account Dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
                    className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-slate-900 border border-transparent hover:border-slate-800 transition-all cursor-pointer"
                  >
                    <div className="w-7 h-7 rounded-full bg-linear-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[11px] font-bold shadow-xs">
                      {user?.display_name ? user.display_name.charAt(0).toUpperCase() : "S"}
                    </div>
                    <span className="hidden md:inline text-xs font-medium text-slate-300 max-w-[110px] truncate">
                      {user?.display_name || "Student"}
                    </span>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:inline" />
                  </button>

                  {profileDropdownOpen && (
                    <div
                      className="absolute right-0 mt-2 w-52 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl py-1.5 z-50 animate-scale-in"
                      onClick={() => setProfileDropdownOpen(false)}
                    >
                      <div className="px-3.5 py-2 border-b border-slate-800">
                        <div className="text-xs font-semibold text-white truncate">
                          {user?.display_name || "Student"}
                        </div>
                        <div className="text-[11px] text-slate-400 truncate">{user?.email}</div>
                      </div>

                      <div className="py-1">
                        <Link
                          href="/profile"
                          className="flex items-center gap-2 px-3.5 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                        >
                          <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                          <span>Academic Profile</span>
                        </Link>
                        <Link
                          href="/settings"
                          className="flex items-center gap-2 px-3.5 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                        >
                          <Settings className="w-3.5 h-3.5 text-slate-400" />
                          <span>Settings & Goals</span>
                        </Link>
                        <Link
                          href="/admin"
                          className="flex items-center gap-2 px-3.5 py-2 text-xs text-slate-400 hover:text-cyan-300 hover:bg-slate-800 transition-colors"
                        >
                          <Layers className="w-3.5 h-3.5" />
                          <span>Admin Observability</span>
                        </Link>
                      </div>

                      <div className="border-t border-slate-800 pt-1">
                        <button
                          onClick={logout}
                          className="w-full flex items-center gap-2 px-3.5 py-2 text-xs text-rose-400 hover:bg-rose-950/40 transition-colors text-left cursor-pointer"
                        >
                          <LogOut className="w-3.5 h-3.5" />
                          <span>Sign Out</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content Workspace */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">{children}</main>

        {/* Mobile Sticky Bottom Navigation */}
        <div className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-slate-950/95 backdrop-blur-lg border-t border-slate-800/80 px-2 py-1.5 flex items-center justify-around shadow-2xl">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-col items-center gap-0.5 py-1 px-2 rounded-xl text-[10px] font-medium transition-colors ${
                  isActive ? "text-indigo-400 font-bold" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-indigo-400 scale-110" : ""}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </ToastProvider>
  );
}
