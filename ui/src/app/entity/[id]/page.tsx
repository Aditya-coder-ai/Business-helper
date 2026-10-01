"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  fetchEntity,
  fetchTimeline,
  fetchRelationships,
  fetchCommunications,
  fetchEntityCommitments,
} from "@/lib/api";
import type {
  CommitmentItem,
  CommunicationItem,
  RelationshipItem,
  TimelineItem,
} from "@/lib/types";
import { EntityTypeBadge, StatusBadge } from "@/components/Badge";
import { WhyModal } from "@/components/WhyModal";
import { RelationshipGraph } from "@/components/RelationshipGraph";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Mail,
  Network,
  Phone,
  Receipt,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Users,
} from "lucide-react";

type TabId =
  | "overview"
  | "timeline"
  | "orders"
  | "invoices"
  | "communications"
  | "commitments"
  | "relationships"
  | "sources";

export default function EntityDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const unwrappedParams = use(params);
  const entityId = unwrappedParams.id;

  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [entity, setEntity] = useState<any | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [relationships, setRelationships] = useState<RelationshipItem[]>([]);
  const [communications, setCommunications] = useState<CommunicationItem[]>([]);
  const [commitments, setCommitments] = useState<CommitmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Why modal state
  const [whyFactId, setWhyFactId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      fetchEntity(entityId).catch(() => null),
      fetchTimeline(entityId).catch(() => ({ timeline: [] })),
      fetchRelationships(entityId).catch(() => ({ relationships: [] })),
      fetchCommunications(entityId).catch(() => ({ communications: [] })),
      fetchEntityCommitments(entityId).catch(() => ({ commitments: [] })),
    ])
      .then(([entData, timeData, relData, commData, commsData]) => {
        if (!isMounted) return;
        if (!entData) {
          setError("Entity not found");
        } else {
          setEntity(entData);
          setTimeline(timeData.timeline || []);
          setRelationships(relData.relationships || []);
          setCommunications(commData.communications || []);
          setCommitments(commsData.commitments || []);
        }
      })
      .catch((err) => {
        if (isMounted) setError(err.message || "Failed to load entity details");
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [entityId]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 flex flex-col items-center justify-center text-slate-400">
        <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-sm font-medium">Resolving entity memory record...</p>
      </div>
    );
  }

  if (error || !entity) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="p-4 bg-rose-950/40 border border-rose-800/60 rounded-2xl text-rose-300 text-sm">
          {error || "Entity not found"}
        </div>
        <Link
          href="/entity"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Entity Directory
        </Link>
      </div>
    );
  }

  const entityType = (entity.entity_type || (entity.emails ? "customer" : "entity")).toLowerCase();
  const canonicalName = entity.canonical_name || entity.name || entity.order_number || entity.invoice_number || "Entity";

  // Filter orders and invoices from timeline
  const orders = timeline.filter((t) => t.kind === "order");
  const invoices = timeline.filter((t) => t.kind === "invoice");

  // Derive sources from timeline + communications
  const sourceRawIds = Array.from(
    new Set(
      [
        ...timeline.map((t) => t.raw_item_id),
        ...communications.map((c) => c.raw_item_id),
      ].filter(Boolean) as string[]
    )
  );

  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: "overview", label: "Overview" },
    { id: "timeline", label: "Timeline", count: timeline.length },
    { id: "orders", label: "Orders", count: orders.length },
    { id: "invoices", label: "Invoices", count: invoices.length },
    { id: "communications", label: "Communications", count: communications.length },
    { id: "commitments", label: "Commitments", count: commitments.length },
    { id: "relationships", label: "Relationships", count: relationships.length },
    { id: "sources", label: "Sources", count: sourceRawIds.length },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Breadcrumb & Actions */}
      <div className="flex items-center justify-between">
        <Link
          href="/entity"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Entities
        </Link>

        {/* Why Button for Entity itself */}
        <button
          id="btn-why-entity"
          onClick={() => setWhyFactId(entity.id)}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-950/80 hover:bg-indigo-900/80 border border-indigo-800 text-indigo-300 text-xs font-medium transition shadow-sm"
        >
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Why this entity?</span>
        </button>
      </div>

      {/* Hero Header Card */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5">
              <EntityTypeBadge type={entityType} />
              <StatusBadge status={entity.status || "ACTIVE"} />
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              {canonicalName}
            </h1>
            <p className="text-xs text-slate-400 font-mono">Entity ID: {entity.id}</p>
          </div>

          {/* Quick Metrics Pills */}
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center min-w-[90px]">
              <span className="block text-xl font-bold text-slate-100">{timeline.length}</span>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider font-mono">
                Events
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center min-w-[90px]">
              <span className="block text-xl font-bold text-indigo-400">{relationships.length}</span>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider font-mono">
                Links
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center min-w-[90px]">
              <span className="block text-xl font-bold text-amber-400">{commitments.length}</span>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider font-mono">
                Promises
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="border-b border-slate-800 flex items-center gap-1 overflow-x-auto pb-px">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 rounded-t-xl text-xs font-semibold whitespace-nowrap transition flex items-center gap-2 border-b-2 ${
                isActive
                  ? "border-indigo-500 text-indigo-400 bg-slate-900/70"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/30"
              }`}
            >
              <span>{tab.label}</span>
              {typeof tab.count === "number" && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    isActive ? "bg-indigo-950 text-indigo-300" : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT: Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-6">
            <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                Entity Profile & Attributes
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                {entity.emails && entity.emails.length > 0 && (
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
                    <span className="text-slate-500 block mb-1 flex items-center gap-1.5">
                      <Mail className="w-3.5 h-3.5 text-indigo-400" /> Resolved Emails
                    </span>
                    <div className="space-y-1 font-mono text-slate-200">
                      {entity.emails.map((m: string) => (
                        <div key={m}>{m}</div>
                      ))}
                    </div>
                  </div>
                )}

                {entity.phones && entity.phones.length > 0 && (
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
                    <span className="text-slate-500 block mb-1 flex items-center gap-1.5">
                      <Phone className="w-3.5 h-3.5 text-emerald-400" /> Phone Numbers
                    </span>
                    <div className="space-y-1 font-mono text-slate-200">
                      {entity.phones.map((p: string) => (
                        <div key={p}>{p}</div>
                      ))}
                    </div>
                  </div>
                )}

                {entity.contact_names && entity.contact_names.length > 0 && (
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
                    <span className="text-slate-500 block mb-1 flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5 text-blue-400" /> Associated Contacts
                    </span>
                    <div className="space-y-1 font-medium text-slate-200">
                      {entity.contact_names.map((c: string) => (
                        <div key={c}>{c}</div>
                      ))}
                    </div>
                  </div>
                )}

                {entity.payment_terms && (
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
                    <span className="text-slate-500 block mb-1 flex items-center gap-1.5">
                      <Receipt className="w-3.5 h-3.5 text-amber-400" /> Payment Terms
                    </span>
                    <span className="font-semibold text-slate-200">{entity.payment_terms}</span>
                  </div>
                )}
              </div>

              {entity.aliases && entity.aliases.length > 0 && (
                <div className="pt-2">
                  <span className="text-slate-500 text-xs block mb-1.5">
                    Recognized Name Aliases:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {entity.aliases.map((a: string) => (
                      <span
                        key={a}
                        className="text-xs px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 font-mono"
                      >
                        {a}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Quick Relationship Preview */}
            <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Network className="w-4 h-4 text-indigo-400" /> Connected Entities
                </h3>
                <button
                  onClick={() => setActiveTab("relationships")}
                  className="text-xs text-indigo-400 hover:text-indigo-300 transition"
                >
                  View Interactive Graph &rarr;
                </button>
              </div>
              <RelationshipGraph
                currentEntityId={entity.id}
                currentEntityName={canonicalName}
                currentEntityType={entityType}
                relationships={relationships.slice(0, 4)}
              />
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                Ground Truth Audit
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                All facts regarding this entity are non-destructively extracted and linked to
                underlying Layer 1 raw items (Gmail, Drive, QuickBooks).
              </p>
              <button
                id="btn-audit-provenance"
                onClick={() => setWhyFactId(entity.id)}
                className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition flex items-center justify-center gap-2"
              >
                <ShieldCheck className="w-4 h-4" /> Inspect Provenance Chain
              </button>
            </div>

            <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                System Timestamps
              </h3>
              <div className="text-xs space-y-2 text-slate-400 font-mono">
                <div>Created: {entity.created_at || "Initial sync"}</div>
                <div>Updated: {entity.updated_at || "Initial sync"}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: Timeline */}
      {activeTab === "timeline" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Unified Chronological Feed
            </h3>
            <span className="text-xs text-slate-500 font-mono">{timeline.length} timeline events</span>
          </div>

          {timeline.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400 text-sm">
              No timeline items recorded yet.
            </div>
          ) : (
            <div className="space-y-3">
              {timeline.map((item, idx) => (
                <div
                  key={`${item.id}-${idx}`}
                  className="glass-card rounded-xl p-4 border border-slate-800 flex items-start justify-between gap-4"
                >
                  <div className="flex items-start gap-3.5">
                    <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/80 text-slate-300 mt-0.5">
                      {item.kind === "communication" && <Mail className="w-4 h-4 text-blue-400" />}
                      {item.kind === "invoice" && <Receipt className="w-4 h-4 text-rose-400" />}
                      {item.kind === "order" && <ShoppingCart className="w-4 h-4 text-emerald-400" />}
                      {item.kind === "commitment" && <Clock className="w-4 h-4 text-amber-400" />}
                      {item.kind === "event" && <Calendar className="w-4 h-4 text-indigo-400" />}
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {item.kind}
                        </span>
                        {item.status && <StatusBadge status={item.status} />}
                        <span className="text-xs text-slate-400 font-mono">
                          {new Date(item.timestamp).toLocaleString()}
                        </span>
                      </div>

                      <h4 className="text-sm font-semibold text-slate-100">
                        {item.subject ||
                          item.description ||
                          item.type ||
                          (item.invoice_number ? `Invoice #${item.invoice_number}` : "Event")}
                      </h4>

                      {item.sender && (
                        <p className="text-xs text-slate-400">
                          Sender: <span className="font-mono text-slate-300">{item.sender}</span>
                        </p>
                      )}

                      {(item.amount || item.total_amount) && (
                        <p className="text-xs font-mono font-semibold text-emerald-400">
                          Amount: ${(item.amount || item.total_amount)?.toLocaleString()} {item.currency || "USD"}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Why Button */}
                  <button
                    id={`btn-why-timeline-${item.id}`}
                    onClick={() => setWhyFactId(item.id)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-950/70 hover:bg-indigo-900 border border-indigo-800/80 text-indigo-300 text-xs font-medium transition self-start"
                  >
                    <Sparkles className="w-3 h-3 text-indigo-400" />
                    <span>Why?</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Orders */}
      {activeTab === "orders" && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Customer Orders
          </h3>
          {orders.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400 text-sm">
              No orders registered for this entity.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {orders.map((ord) => (
                <div
                  key={ord.id}
                  className="glass-card rounded-xl p-5 border border-slate-800 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-slate-200">
                      Order ID: {ord.id}
                    </span>
                    <StatusBadge status={ord.status || "CONFIRMED"} />
                  </div>
                  <div className="text-xl font-bold text-emerald-400 font-mono">
                    ${(ord.total_amount || ord.amount || 0).toLocaleString()} {ord.currency || "USD"}
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs text-slate-500 font-mono">
                    <span>Date: {new Date(ord.timestamp).toLocaleDateString()}</span>
                    <button
                      onClick={() => setWhyFactId(ord.id)}
                      className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300"
                    >
                      <Sparkles className="w-3 h-3" /> Why?
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Invoices */}
      {activeTab === "invoices" && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Invoices & Billing History
          </h3>
          {invoices.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400 text-sm">
              No invoices linked to this entity.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {invoices.map((inv) => (
                <div
                  key={inv.id}
                  className="glass-card rounded-xl p-5 border border-slate-800 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200 text-base">
                      {inv.invoice_number ? `Invoice #${inv.invoice_number}` : inv.id}
                    </span>
                    <StatusBadge status={inv.status || "SENT"} />
                  </div>
                  <div className="text-2xl font-extrabold text-slate-100 font-mono">
                    ${(inv.amount || 0).toLocaleString()} {inv.currency || "USD"}
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs text-slate-500 font-mono">
                    <span>Issued: {new Date(inv.timestamp).toLocaleDateString()}</span>
                    <button
                      onClick={() => setWhyFactId(inv.id)}
                      className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300"
                    >
                      <Sparkles className="w-3 h-3" /> Why?
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Communications */}
      {activeTab === "communications" && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Messages & Documents
          </h3>
          {communications.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400 text-sm">
              No direct communications recorded.
            </div>
          ) : (
            <div className="space-y-3">
              {communications.map((comm) => (
                <div
                  key={comm.id}
                  className="glass-card rounded-xl p-4 border border-slate-800 space-y-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-slate-400">{comm.sender}</span>
                      <span className="text-slate-600">&rarr;</span>
                      <span className="font-mono text-slate-400">{comm.recipient}</span>
                    </div>
                    <span className="text-slate-500 font-mono">
                      {new Date(comm.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-200">{comm.subject}</h4>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs text-slate-500">
                    <span className="font-mono">Raw Item: {comm.raw_item_id}</span>
                    <button
                      onClick={() => setWhyFactId(comm.raw_item_id || comm.id)}
                      className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium"
                    >
                      <Sparkles className="w-3 h-3" /> Inspect Evidence
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Commitments */}
      {activeTab === "commitments" && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Extracted Commitments & Action Items
          </h3>
          {commitments.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400 text-sm">
              No outstanding commitments recorded.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {commitments.map((comm) => (
                <div
                  key={comm.id}
                  className="glass-card rounded-xl p-5 border border-slate-800 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <StatusBadge status={comm.status} />
                    <span className="text-xs font-mono font-semibold text-indigo-400">
                      Confidence: {Math.round(comm.confidence * 100)}%
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-slate-100 leading-snug">
                    {comm.description}
                  </p>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs text-slate-500 font-mono">
                    <span>
                      Due: {comm.due_date ? new Date(comm.due_date).toLocaleDateString() : "No deadline"}
                    </span>
                    <button
                      onClick={() => setWhyFactId(comm.id)}
                      className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300"
                    >
                      <Sparkles className="w-3 h-3" /> Why?
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Relationships */}
      {activeTab === "relationships" && (
        <div className="space-y-6">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Entity Topology & Relationship Graph
          </h3>
          <RelationshipGraph
            currentEntityId={entity.id}
            currentEntityName={canonicalName}
            currentEntityType={entityType}
            relationships={relationships}
          />
        </div>
      )}

      {/* TAB CONTENT: Sources */}
      {activeTab === "sources" && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Underlying Layer 1 Source RawItems
          </h3>
          {sourceRawIds.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400 text-sm">
              No direct source records tracked.
            </div>
          ) : (
            <div className="space-y-3">
              {sourceRawIds.map((rawId) => (
                <div
                  key={rawId}
                  className="glass-card rounded-xl p-4 border border-slate-800 flex items-center justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-indigo-300 font-semibold">
                        RawItem: {rawId}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 font-mono">
                      Contributed to entity facts and timeline occurrences
                    </p>
                  </div>
                  <button
                    onClick={() => setWhyFactId(rawId)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-950/80 hover:bg-indigo-900 border border-indigo-800 text-indigo-300 text-xs font-medium transition"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Inspect Raw Evidence</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Why Modal */}
      <WhyModal factId={whyFactId} onClose={() => setWhyFactId(null)} />
    </div>
  );
}
