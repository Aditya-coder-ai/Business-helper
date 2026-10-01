"use client";

import React, { Suspense, useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { fetchEntities } from "@/lib/api";
import type { EntitySummary } from "@/lib/types";
import { EntityTypeBadge, StatusBadge } from "@/components/Badge";
import {
  Search,
  Users,
  Building2,
  Package,
  ShoppingCart,
  Receipt,
  ArrowRight,
  Filter,
  Sparkles,
  RefreshCw,
} from "lucide-react";

const ENTITY_TYPES = [
  { id: "all", label: "All Entities", icon: Users },
  { id: "customer", label: "Customers", icon: Users },
  { id: "supplier", label: "Suppliers", icon: Building2 },
  { id: "order", label: "Orders", icon: ShoppingCart },
  { id: "invoice", label: "Invoices", icon: Receipt },
  { id: "product", label: "Products", icon: Package },
];

function EntitiesContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialQuery = searchParams.get("q") || "";
  const initialType = searchParams.get("entity_type") || "all";

  const [query, setQuery] = useState(initialQuery);
  const [selectedType, setSelectedType] = useState(initialType);
  const [entities, setEntities] = useState<EntitySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const loadData = async (searchQ: string, type: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEntities(searchQ, type);
      setEntities(data.entities || []);
    } catch (err: any) {
      setError(err.message || "Failed to load entities");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(query, selectedType);
  }, [selectedType]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData(query, selectedType);
  };

  const handleTypeSelect = (typeId: string) => {
    setSelectedType(typeId);
    startTransition(() => {
      const params = new URLSearchParams();
      if (query) params.set("q", query);
      if (typeId !== "all") params.set("entity_type", typeId);
      router.push(`/entity?${params.toString()}`);
    });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header & Subtitle */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              Business Memory Entities
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800">
              {entities.length} Total
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Canonical enterprise entities resolved and linked across Gmail, Drive, and QuickBooks
          </p>
        </div>

        <button
          id="btn-refresh-entities"
          onClick={() => loadData(query, selectedType)}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs font-medium transition self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-indigo-400" : ""}`} />
          Refresh Memory
        </button>
      </div>

      {/* Controls: Search & Entity Type Pills */}
      <div className="space-y-4">
        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="relative max-w-2xl">
          <Search className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            id="entity-search-input"
            type="text"
            placeholder="Search by name, company, or keyword (press Enter)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full pl-11 pr-24 py-3 rounded-2xl bg-slate-900/90 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 shadow-inner transition"
          />
          <button
            id="btn-search-submit"
            type="submit"
            className="absolute right-2 top-1/2 -translate-y-1/2 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition shadow-md shadow-indigo-600/20"
          >
            Search
          </button>
        </form>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2">
          {ENTITY_TYPES.map((t) => {
            const Icon = t.icon;
            const isSelected = selectedType === t.id;
            return (
              <button
                key={t.id}
                id={`filter-${t.id}`}
                onClick={() => handleTypeSelect(t.id)}
                className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition ${
                  isSelected
                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 border border-indigo-500"
                    : "bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800/80 hover:border-slate-700"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm">
          Failed to load business memory entities: {error}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="py-20 flex flex-col items-center justify-center text-slate-400">
          <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-sm font-medium">Scanning memory database...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && entities.length === 0 && (
        <div className="py-20 text-center rounded-2xl border border-slate-800 bg-slate-900/30 p-8">
          <Filter className="w-12 h-12 mx-auto text-slate-600 mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No entities found</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            No business entities match the query &ldquo;{query}&rdquo; and filter &ldquo;{selectedType}&rdquo;. Try
            adjusting your search terms or clearing the filter.
          </p>
          <button
            onClick={() => {
              setQuery("");
              setSelectedType("all");
              loadData("", "all");
            }}
            className="mt-4 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition"
          >
            Clear Filters
          </button>
        </div>
      )}

      {/* Entity Cards Grid */}
      {!loading && entities.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {entities.map((entity) => (
            <Link
              key={entity.id}
              id={`entity-card-${entity.id}`}
              href={`/entity/${encodeURIComponent(entity.id)}`}
              className="glass-card rounded-2xl p-5 flex flex-col justify-between group border border-slate-800/80 hover:border-indigo-500/50 transition-all duration-200"
            >
              <div className="space-y-3">
                {/* Badges Row */}
                <div className="flex items-center justify-between gap-2">
                  <EntityTypeBadge type={entity.entity_type} />
                  <StatusBadge status={entity.status || "ACTIVE"} />
                </div>

                {/* Canonical Name */}
                <div>
                  <h3 className="text-lg font-bold text-slate-100 group-hover:text-indigo-400 transition-colors line-clamp-1">
                    {entity.canonical_name}
                  </h3>
                  <p className="text-xs text-slate-500 font-mono mt-0.5 truncate">
                    ID: {entity.id}
                  </p>
                </div>

                {/* Metadata Tags */}
                {entity.metadata && Object.keys(entity.metadata).length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {Object.entries(entity.metadata).map(([k, v]) => (
                      <span
                        key={k}
                        className="text-[10px] px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 font-mono border border-slate-700/50"
                      >
                        {k}: {String(v)}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Card Footer */}
              <div className="pt-5 mt-4 border-t border-slate-800/60 flex items-center justify-between text-xs">
                <span className="text-slate-500 font-mono text-[11px]">
                  {entity.updated_at
                    ? `Updated ${new Date(entity.updated_at).toLocaleDateString()}`
                    : "Canonical record"}
                </span>
                <span className="inline-flex items-center gap-1 text-indigo-400 font-medium group-hover:translate-x-0.5 transition-transform">
                  View Profile <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function EntitiesPage() {
  return (
    <Suspense
      fallback={
        <div className="py-20 flex flex-col items-center justify-center text-slate-400">
          <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-sm font-medium">Scanning memory database...</p>
        </div>
      }
    >
      <EntitiesContent />
    </Suspense>
  );
}
