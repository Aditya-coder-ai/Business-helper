import React from "react";

export function EntityTypeBadge({ type, className = "" }: { type: string; className?: string }) {
  const norm = type.toLowerCase();
  let bg = "bg-indigo-950/70 text-indigo-300 border-indigo-700/50";
  if (norm === "customer") bg = "bg-blue-950/70 text-blue-300 border-blue-700/50";
  if (norm === "supplier") bg = "bg-emerald-950/70 text-emerald-300 border-emerald-700/50";
  if (norm === "product") bg = "bg-purple-950/70 text-purple-300 border-purple-700/50";
  if (norm === "order") bg = "bg-amber-950/70 text-amber-300 border-amber-700/50";
  if (norm === "invoice") bg = "bg-rose-950/70 text-rose-300 border-rose-700/50";

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wider ${bg} ${className}`}
    >
      {type}
    </span>
  );
}

export function StatusBadge({ status, className = "" }: { status: string; className?: string }) {
  const norm = status.toUpperCase();
  let bg = "bg-slate-800 text-slate-300 border-slate-700";
  if (norm === "ACTIVE" || norm === "PAID" || norm === "FULFILLED") {
    bg = "bg-emerald-950/60 text-emerald-400 border-emerald-800/60";
  } else if (norm === "OVERDUE" || norm === "CANCELLED") {
    bg = "bg-rose-950/60 text-rose-400 border-rose-800/60";
  } else if (norm === "PENDING" || norm === "OPEN" || norm === "SENT") {
    bg = "bg-amber-950/60 text-amber-400 border-amber-800/60";
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${bg} ${className}`}
    >
      {status}
    </span>
  );
}

export function SourceBadge({ source }: { source: string }) {
  const norm = source.toLowerCase();
  let color = "text-sky-400 bg-sky-950/50 border-sky-800/60";
  if (norm === "gmail") color = "text-red-400 bg-red-950/50 border-red-800/60";
  if (norm === "drive") color = "text-amber-400 bg-amber-950/50 border-amber-800/60";
  if (norm === "quickbooks") color = "text-emerald-400 bg-emerald-950/50 border-emerald-800/60";

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono border ${color}`}>
      {source.toUpperCase()}
    </span>
  );
}
