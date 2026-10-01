"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchEntities,
  fetchOpenCommitments,
  fetchOverdueInvoices,
  fetchRecentEvents,
} from "@/lib/api";
import type { CommitmentItem, EntitySummary, InvoiceEntity, RecentEvent } from "@/lib/types";
import { StatusBadge } from "@/components/Badge";
import {
  BrainCircuit,
  Users,
  Building2,
  Clock,
  ArrowRight,
  AlertTriangle,
  Search,
  Activity,
} from "lucide-react";
import { useRouter } from "next/navigation";

export default function DashboardPage() {
  const router = useRouter();
  const [entities, setEntities] = useState<EntitySummary[]>([]);
  const [commitments, setCommitments] = useState<CommitmentItem[]>([]);
  const [invoices, setInvoices] = useState<InvoiceEntity[]>([]);
  const [events, setEvents] = useState<RecentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchVal, setSearchVal] = useState("");

  useEffect(() => {
    Promise.all([
      fetchEntities(undefined, undefined, 10).catch(() => ({ entities: [] })),
      fetchOpenCommitments().catch(() => ({ commitments: [] })),
      fetchOverdueInvoices().catch(() => ({ invoices: [] })),
      fetchRecentEvents(10).catch(() => ({ events: [] })),
    ])
      .then(([entData, commData, invData, evData]) => {
        setEntities(entData.entities || []);
        setCommitments(commData.commitments || []);
        setInvoices(invData.invoices || []);
        setEvents(evData.events || []);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchVal.trim()) {
      router.push(`/entity?q=${encodeURIComponent(searchVal.trim())}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-950/70 via-slate-900 to-slate-950 border border-slate-800 p-8 shadow-2xl">
        <div className="relative z-10 max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-900/50 border border-indigo-700/60 text-indigo-300 text-xs font-semibold">
            <BrainCircuit className="w-3.5 h-3.5" />
            <span>Layer 2 Business Memory Engine</span>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
            Entity-Centric Business Memory
          </h1>
          <p className="text-slate-300 text-sm leading-relaxed">
            Consolidated canonical entities, verified relationships, chronological audit timelines,
            and complete Layer 1 provenance extracted across Gmail, Drive, and QuickBooks.
          </p>

          {/* Quick Search */}
          <form onSubmit={handleSearch} className="pt-2 flex items-center gap-2 max-w-lg">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                id="hero-search-input"
                type="text"
                placeholder="Search customers, suppliers, invoices..."
                value={searchVal}
                onChange={(e) => setSearchVal(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900/90 border border-slate-700/80 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 shadow-inner"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition shadow-lg shadow-indigo-600/30"
            >
              Explore
            </button>
          </form>
        </div>

        {/* Ambient glow */}
        <div className="absolute -right-20 -bottom-20 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          href="/entity"
          className="glass-card rounded-2xl p-5 border border-slate-800 space-y-2 group"
        >
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Entities</span>
            <Users className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition" />
          </div>
          <div className="text-3xl font-extrabold text-white font-mono">
            {loading ? "..." : entities.length}
          </div>
          <span className="text-[11px] text-slate-500 flex items-center gap-1">
            Canonical Directory <ArrowRight className="w-3 h-3 text-indigo-400" />
          </span>
        </Link>

        <Link
          href="/entity?entity_type=customer"
          className="glass-card rounded-2xl p-5 border border-slate-800 space-y-2 group"
        >
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Customers</span>
            <Users className="w-4 h-4 text-blue-400 group-hover:scale-110 transition" />
          </div>
          <div className="text-3xl font-extrabold text-blue-400 font-mono">
            {loading ? "..." : entities.filter((e) => e.entity_type === "customer").length}
          </div>
          <span className="text-[11px] text-slate-500 flex items-center gap-1">
            Accounts & Contacts <ArrowRight className="w-3 h-3 text-blue-400" />
          </span>
        </Link>

        <Link
          href="/entity?entity_type=supplier"
          className="glass-card rounded-2xl p-5 border border-slate-800 space-y-2 group"
        >
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Suppliers</span>
            <Building2 className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 font-mono">
            {loading ? "..." : entities.filter((e) => e.entity_type === "supplier").length}
          </div>
          <span className="text-[11px] text-slate-500 flex items-center gap-1">
            Vendors & Logistics <ArrowRight className="w-3 h-3 text-emerald-400" />
          </span>
        </Link>

        <div className="glass-card rounded-2xl p-5 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Open Promises</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-extrabold text-amber-400 font-mono">
            {loading ? "..." : commitments.length}
          </div>
          <span className="text-[11px] text-slate-500">Tracked Commitments</span>
        </div>
      </div>

      {/* Main Panels: Overdue Invoices & Open Commitments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Open Commitments Panel */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
                <Clock className="w-4 h-4" />
              </div>
              <h3 className="text-base font-bold text-white">Active Commitments</h3>
            </div>
            <span className="text-xs font-mono text-slate-400">{commitments.length} Pending</span>
          </div>

          {commitments.length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">No outstanding commitments.</p>
          ) : (
            <div className="space-y-3">
              {commitments.map((comm) => (
                <div
                  key={comm.id}
                  className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <StatusBadge status={comm.status} />
                    <span className="font-mono text-indigo-400 text-[11px]">
                      Confidence: {Math.round(comm.confidence * 100)}%
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-200">{comm.description}</p>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono pt-1">
                    <span>Due: {comm.due_date ? new Date(comm.due_date).toLocaleDateString() : "TBD"}</span>
                    {comm.related_entity_id && (
                      <Link
                        href={`/entity/${encodeURIComponent(comm.related_entity_id)}`}
                        className="text-indigo-400 hover:underline"
                      >
                        View Entity &rarr;
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Overdue Invoices Panel */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <h3 className="text-base font-bold text-white">Overdue Invoices</h3>
            </div>
            <span className="text-xs font-mono text-rose-400">{invoices.length} Overdue</span>
          </div>

          {invoices.length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">No overdue invoices.</p>
          ) : (
            <div className="space-y-3">
              {invoices.map((inv) => (
                <div
                  key={inv.id}
                  className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-900/40 flex items-center justify-between gap-4"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-100">
                        {inv.invoice_number ? `Invoice #${inv.invoice_number}` : inv.id}
                      </span>
                      <StatusBadge status={inv.status} />
                    </div>
                    <p className="text-[11px] text-rose-400/80 font-mono mt-0.5">
                      Due: {inv.due_date ? new Date(inv.due_date).toLocaleDateString() : "Immediate"}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-base font-bold font-mono text-slate-100 block">
                      ${(inv.amount || 0).toLocaleString()} {inv.currency || "USD"}
                    </span>
                    {(inv.customer_id || inv.supplier_id) && (
                      <Link
                        href={`/entity/${encodeURIComponent(inv.customer_id || inv.supplier_id || "")}`}
                        className="text-[11px] text-indigo-400 hover:underline"
                      >
                        View Entity &rarr;
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Events Audit Feed */}
      {events.length > 0 && (
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <Activity className="w-4 h-4" />
              </div>
              <h3 className="text-base font-bold text-white">Recent Business Events</h3>
            </div>
            <span className="text-xs font-mono text-slate-400">{events.length} Events</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {events.slice(0, 6).map((ev) => (
              <div
                key={ev.id}
                className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-indigo-400 text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-indigo-950/80 border border-indigo-800/50">
                    {ev.type}
                  </span>
                  <span className="text-slate-500 font-mono text-[10px]">
                    {new Date(ev.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-slate-300 font-mono truncate">Entity: {ev.entity_id}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
