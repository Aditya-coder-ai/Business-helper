"use client";

import React, { useEffect, useState } from "react";
import { fetchProvenance } from "@/lib/api";
import type { ProvenanceRecord } from "@/lib/types";
import { SourceBadge } from "./Badge";
import { ExternalLink, ShieldCheck, Sparkles, X, FileText } from "lucide-react";

interface WhyModalProps {
  factId: string | null;
  onClose: () => void;
}

export function WhyModal({ factId, onClose }: WhyModalProps) {
  const [provenance, setProvenance] = useState<ProvenanceRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!factId) return;
    let isCurrent = true;
    const timer = setTimeout(() => {
      if (isCurrent) setLoading(true);
    }, 0);
    fetchProvenance(factId)
      .then((data) => {
        if (isCurrent) {
          setProvenance(data.provenance || []);
          setError(null);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isCurrent) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => {
      isCurrent = false;
      clearTimeout(timer);
    };
  }, [factId]);

  if (!factId) return null;

  return (
    <div
      id="provenance-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        id="provenance-modal-content"
        className="relative w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl p-6 text-slate-100 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20 text-indigo-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold tracking-tight text-white flex items-center gap-2">
                Ground Truth Evidence
                <span className="text-xs px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono">
                  Why?
                </span>
              </h3>
              <p className="text-xs text-slate-400 font-mono">Fact ID: {factId}</p>
            </div>
          </div>
          <button
            id="btn-close-why-modal"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {loading && (
          <div className="py-12 flex flex-col items-center justify-center text-slate-400">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3"></div>
            <p className="text-sm">Retrieving audit provenance from Layer 1 store...</p>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-800/60 rounded-xl text-rose-300 text-sm">
            Failed to load provenance chain: {error}
          </div>
        )}

        {!loading && !error && provenance.length === 0 && (
          <div className="py-10 text-center text-slate-400">
            <FileText className="w-10 h-10 mx-auto text-slate-600 mb-2" />
            <p className="text-sm">No explicit provenance record found for this identifier.</p>
            <p className="text-xs text-slate-500 mt-1">
              This entity or attribute was derived through canonical resolution rules.
            </p>
          </div>
        )}

        {!loading && provenance.length > 0 && (
          <div className="space-y-4">
            {provenance.map((p, idx) => (
              <div
                key={`${p.raw_item_id}-${idx}`}
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-3"
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <SourceBadge source={p.source} />
                    <span className="font-mono text-slate-400">{p.raw_item_id}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-indigo-400 font-medium">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Extractor: {p.extractor_name}</span>
                  </div>
                </div>

                {/* Confidence Bar */}
                <div>
                  <div className="flex justify-between text-xs text-slate-400 mb-1">
                    <span>Inference Confidence</span>
                    <span className="font-mono font-semibold text-slate-200">
                      {Math.round(p.confidence * 100)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        p.confidence >= 0.85
                          ? "bg-emerald-500"
                          : p.confidence >= 0.6
                          ? "bg-amber-500"
                          : "bg-rose-500"
                      }`}
                      style={{ width: `${Math.round(p.confidence * 100)}%` }}
                    />
                  </div>
                </div>

                {/* Raw Snippet */}
                {p.raw_snippet && (
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                      Raw Source Excerpt (Layer 1)
                    </label>
                    <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-300 leading-relaxed whitespace-pre-wrap select-text">
                      {p.raw_snippet}
                    </div>
                  </div>
                )}

                {/* Metadata Footer */}
                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                  <span>Extracted: {new Date(p.extracted_at).toLocaleString()}</span>
                  {p.source_url && (
                    <a
                      href={p.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 underline"
                    >
                      View Source Document <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
