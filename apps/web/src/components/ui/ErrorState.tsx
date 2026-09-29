import React from "react";
import { AlertCircle, RotateCcw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  message,
  description,
  onRetry,
  className = "",
}: ErrorStateProps) {
  const displayMessage = description || message || "Failed to load learning data. Please check your network connection.";
  return (
    <div
      className={`p-6 rounded-2xl border border-rose-900/40 bg-rose-950/20 text-center flex flex-col items-center justify-center space-y-3 ${className}`}
    >
      <div className="w-10 h-10 rounded-xl bg-rose-900/40 border border-rose-700/50 text-rose-400 flex items-center justify-center">
        <AlertCircle className="w-5 h-5" />
      </div>
      <div className="space-y-1">
        <h4 className="text-sm font-semibold text-rose-200">{title}</h4>
        <p className="text-xs text-rose-300/80 max-w-sm">{displayMessage}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-rose-800/40 hover:bg-rose-800/60 border border-rose-700/60 text-rose-200 text-xs font-medium transition-all cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Try Again</span>
        </button>
      )}
    </div>
  );
}
