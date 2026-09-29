import React from "react";

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`skeleton-shimmer rounded-xl bg-slate-800/60 ${className}`}
      aria-hidden="true"
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 space-y-3">
      <div className="flex justify-between items-center">
        <Skeleton className="h-4 w-24 rounded-md" />
        <Skeleton className="h-4 w-12 rounded-md" />
      </div>
      <Skeleton className="h-6 w-3/4 rounded-lg" />
      <Skeleton className="h-3 w-1/2 rounded-md" />
      <div className="pt-2 flex gap-2">
        <Skeleton className="h-8 flex-1 rounded-lg" />
        <Skeleton className="h-8 w-20 rounded-lg" />
      </div>
    </div>
  );
}

export function TableRowSkeleton() {
  return (
    <div className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/30 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3 flex-1">
        <Skeleton className="h-9 w-9 rounded-xl shrink-0" />
        <div className="space-y-1.5 flex-1">
          <Skeleton className="h-4 w-1/3 rounded-md" />
          <Skeleton className="h-3 w-1/4 rounded-md" />
        </div>
      </div>
      <Skeleton className="h-7 w-24 rounded-lg" />
    </div>
  );
}

export const SkeletonCard = CardSkeleton;
export const SkeletonRow = TableRowSkeleton;

