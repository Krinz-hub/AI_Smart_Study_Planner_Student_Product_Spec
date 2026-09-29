"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  Lock,
  Mail,
  ArrowRight,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import { apiLogin, fetchOnboardingStatus } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMessage("Please enter both email and password.");
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      const resp = await apiLogin(email.trim(), password);
      login(resp.access_token, resp.user);

      // Check onboarding state to route accurately
      try {
        const onboarding = await fetchOnboardingStatus(resp.access_token);
        if (onboarding.is_completed) {
          router.push("/home");
        } else {
          router.push("/onboarding");
        }
      } catch {
        router.push("/home");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Invalid email or password. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleDemoFill = () => {
    setEmail("student_demo@example.com");
    setPassword("Password123!");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-4">
      {/* Background Glow */}
      <div className="absolute w-[500px] h-[300px] bg-linear-to-tr from-indigo-600/15 to-purple-600/10 blur-3xl pointer-events-none rounded-full" />

      <div className="relative w-full max-w-md bg-slate-900/90 backdrop-blur-xl border border-slate-800 rounded-3xl shadow-2xl p-8 space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <Link href="/" className="inline-flex items-center gap-2 group">
            <div className="w-10 h-10 rounded-xl bg-linear-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5" />
            </div>
            <span className="font-extrabold text-xl text-white">Luminary</span>
          </Link>
          <h2 className="text-xl font-bold text-white pt-2">Welcome Back</h2>
          <p className="text-xs text-slate-400">Sign in to your adaptive study cockpit</p>
        </div>

        {/* Demo Fast-Fill Helper */}
        <div className="p-3 rounded-xl bg-indigo-950/40 border border-indigo-800/40 flex items-center justify-between">
          <div className="text-[11px] text-indigo-300 font-medium">Testing & Evaluation helper:</div>
          <button
            type="button"
            onClick={handleDemoFill}
            className="text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 bg-indigo-900/60 px-2.5 py-1 rounded-lg border border-indigo-700/50 transition-colors cursor-pointer"
          >
            Fill Demo Student
          </button>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60 text-rose-300 text-xs">
            {errorMessage}
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@university.edu"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-300">Password</label>
              <Link
                href="/forgot-password"
                className="text-[11px] font-medium text-indigo-400 hover:text-indigo-300"
              >
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-3 text-slate-500 hover:text-slate-300"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Sign In to Cockpit"}
            {!loading && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        {/* Footer Link */}
        <div className="text-center text-xs text-slate-400 pt-2 border-t border-slate-800/80">
          Don&apos;t have an account yet?{" "}
          <Link href="/signup" className="font-semibold text-indigo-400 hover:text-indigo-300">
            Sign up now
          </Link>
        </div>
      </div>
    </div>
  );
}
