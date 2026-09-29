"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Sparkles, Mail, Lock, Key, ArrowRight, Loader2, CheckCircle2 } from "lucide-react";
import { requestPasswordReset, confirmPasswordReset } from "@/lib/api-client";

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<"REQUEST" | "CONFIRM" | "SUCCESS">("REQUEST");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await requestPasswordReset(email.trim());
      setMessage(res.message);
      if (res.dev_token) {
        setToken(res.dev_token);
      }
      setStep("CONFIRM");
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to request password reset");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);
    try {
      await confirmPasswordReset(token.trim(), newPassword);
      setStep("SUCCESS");
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to reset password. Please check token.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-4">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl p-8 space-y-6">
        <div className="text-center space-y-2">
          <Link href="/" className="inline-flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-linear-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white">
              <Sparkles className="w-5 h-5" />
            </div>
            <span className="font-extrabold text-xl text-white">Luminary</span>
          </Link>
          <h2 className="text-xl font-bold text-white pt-2">Password Recovery</h2>
          <p className="text-xs text-slate-400">Reset your study planner account credentials</p>
        </div>

        {errorMessage && (
          <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60 text-rose-300 text-xs">
            {errorMessage}
          </div>
        )}

        {message && step === "CONFIRM" && (
          <div className="p-3.5 rounded-xl bg-indigo-950/50 border border-indigo-800/60 text-indigo-300 text-xs">
            {message}
          </div>
        )}

        {step === "REQUEST" && (
          <form onSubmit={handleRequest} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Account Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="student@example.com"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Request Reset Token"}
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>
        )}

        {step === "CONFIRM" && (
          <form onSubmit={handleConfirm} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Reset Token</label>
              <div className="relative">
                <Key className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="text"
                  required
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Paste reset token here"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs font-mono placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">New Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all cursor-pointer disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Update Password"}
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>
        )}

        {step === "SUCCESS" && (
          <div className="text-center space-y-4 py-4">
            <div className="w-12 h-12 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 mx-auto flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-white">Password Updated!</h3>
            <p className="text-xs text-slate-400">
              Your password has been securely reset. You can now log in with your new credentials.
            </p>
            <Link
              href="/login"
              className="inline-flex items-center justify-center px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all"
            >
              Back to Sign In
            </Link>
          </div>
        )}

        <div className="text-center text-xs text-slate-400 pt-2 border-t border-slate-800/80">
          Remembered your password?{" "}
          <Link href="/login" className="font-semibold text-indigo-400 hover:text-indigo-300">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
