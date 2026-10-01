"use client";

import React, { useState } from "react";
import Link from "next/link";
import type { RelationshipItem } from "@/lib/types";
import { EntityTypeBadge } from "./Badge";
import { Network, ExternalLink } from "lucide-react";

interface RelationshipGraphProps {
  currentEntityId?: string;
  currentEntityName: string;
  currentEntityType: string;
  relationships: RelationshipItem[];
}

export function RelationshipGraph({
  currentEntityId: _currentEntityId,
  currentEntityName,
  currentEntityType,
  relationships,
}: RelationshipGraphProps) {
  const [hoveredRel, setHoveredRel] = useState<string | null>(null);

  if (!relationships || relationships.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900/40 rounded-2xl border border-slate-800">
        <Network className="w-10 h-10 mx-auto text-slate-600 mb-2" />
        <p className="text-slate-400 text-sm font-medium">No linked entity relationships found.</p>
        <p className="text-xs text-slate-500 mt-1">
          Relationships are discovered through orders, invoices, and semantic message extractions.
        </p>
      </div>
    );
  }

  // Dimensions for circular SVG layout
  const width = 640;
  const height = 400;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = 150;

  return (
    <div className="space-y-6">
      {/* SVG Canvas Graph */}
      <div className="relative w-full overflow-hidden rounded-2xl bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 border border-slate-800 p-4 shadow-xl">
        <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
          <span className="text-xs font-mono text-slate-400">Interactive Entity Topology</span>
        </div>

        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto max-h-[420px] select-none"
        >
          <defs>
            <marker
              id="arrow-marker"
              viewBox="0 0 10 10"
              refX="22"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#6366f1" opacity="0.8" />
            </marker>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Connections */}
          {relationships.map((rel, index) => {
            const angle = (2 * Math.PI * index) / relationships.length;
            const nodeX = centerX + radius * Math.cos(angle);
            const nodeY = centerY + radius * Math.sin(angle);
            const isHovered = hoveredRel === rel.id;

            return (
              <g key={`edge-${rel.id}`}>
                <line
                  x1={centerX}
                  y1={centerY}
                  x2={nodeX}
                  y2={nodeY}
                  stroke={isHovered ? "#818cf8" : "#334155"}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  strokeDasharray={rel.rel_type === "supplies" ? "4 2" : "none"}
                  markerEnd="url(#arrow-marker)"
                  className="transition-all duration-200"
                />
                {/* Edge Label Badge */}
                <rect
                  x={(centerX + nodeX) / 2 - 36}
                  y={(centerY + nodeY) / 2 - 10}
                  width="72"
                  height="20"
                  rx="6"
                  fill="#0f172a"
                  stroke={isHovered ? "#6366f1" : "#1e293b"}
                  strokeWidth="1"
                />
                <text
                  x={(centerX + nodeX) / 2}
                  y={(centerY + nodeY) / 2 + 3}
                  textAnchor="middle"
                  className="text-[10px] font-mono fill-indigo-300 font-semibold uppercase tracking-wider"
                >
                  {rel.rel_type}
                </text>
              </g>
            );
          })}

          {/* Center Root Node */}
          <g filter="url(#glow)">
            <circle
              cx={centerX}
              cy={centerY}
              r="40"
              fill="#1e1b4b"
              stroke="#6366f1"
              strokeWidth="2.5"
            />
            <text
              x={centerX}
              y={centerY - 6}
              textAnchor="middle"
              className="text-xs font-bold fill-white tracking-tight"
            >
              {currentEntityName.length > 14
                ? `${currentEntityName.slice(0, 12)}…`
                : currentEntityName}
            </text>
            <text
              x={centerX}
              y={centerY + 10}
              textAnchor="middle"
              className="text-[9px] font-mono uppercase fill-indigo-300 tracking-wider"
            >
              {currentEntityType}
            </text>
          </g>

          {/* Surrounding Nodes */}
          {relationships.map((rel, index) => {
            const angle = (2 * Math.PI * index) / relationships.length;
            const nodeX = centerX + radius * Math.cos(angle);
            const nodeY = centerY + radius * Math.sin(angle);
            const isHovered = hoveredRel === rel.id;

            return (
              <g
                key={`node-${rel.id}`}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredRel(rel.id)}
                onMouseLeave={() => setHoveredRel(null)}
              >
                <circle
                  cx={nodeX}
                  cy={nodeY}
                  r="30"
                  fill={isHovered ? "#1e293b" : "#0f172a"}
                  stroke={isHovered ? "#38bdf8" : "#334155"}
                  strokeWidth={isHovered ? 2 : 1}
                  className="transition-all duration-200"
                />
                <text
                  x={nodeX}
                  y={nodeY - 3}
                  textAnchor="middle"
                  className="text-[10px] font-medium fill-slate-200"
                >
                  {rel.other_entity_name.length > 10
                    ? `${rel.other_entity_name.slice(0, 9)}…`
                    : rel.other_entity_name}
                </text>
                <text
                  x={nodeX}
                  y={nodeY + 9}
                  textAnchor="middle"
                  className="text-[8px] font-mono uppercase fill-slate-400"
                >
                  {rel.other_entity_type}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Structured Cards List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {relationships.map((rel) => (
          <Link
            key={rel.id}
            href={`/entity/${encodeURIComponent(rel.other_entity_id)}`}
            className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-800/60 transition group flex items-center justify-between"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 font-mono font-semibold uppercase">
                  {rel.rel_type}
                </span>
                <EntityTypeBadge type={rel.other_entity_type} />
              </div>
              <h4 className="text-sm font-semibold text-slate-100 group-hover:text-indigo-400 transition">
                {rel.other_entity_name}
              </h4>
              <p className="text-xs text-slate-500 font-mono">ID: {rel.other_entity_id}</p>
            </div>
            <div className="p-2 rounded-lg bg-slate-800 group-hover:bg-indigo-600 text-slate-400 group-hover:text-white transition">
              <ExternalLink className="w-4 h-4" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
