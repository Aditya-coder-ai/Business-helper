import type {
  CommitmentItem,
  CommunicationItem,
  EntitySummary,
  InvoiceEntity,
  ProvenanceRecord,
  RecentEvent,
  RelationshipItem,
  TimelineItem,
} from "./types";

const BASE_URL = typeof window === "undefined"
  ? (process.env.INTERNAL_API_URL || "http://127.0.0.1:8000")
  : "";

async function fetchJson<T>(path: string): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchEntities(
  q?: string,
  entityType?: string,
  limit = 100
): Promise<{ entities: EntitySummary[]; count: number }> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (entityType && entityType !== "all") params.set("entity_type", entityType);
  if (limit) params.set("limit", limit.toString());
  const qs = params.toString() ? `?${params.toString()}` : "";
  return fetchJson<{ entities: EntitySummary[]; count: number }>(`/api/entities${qs}`);
}

export async function fetchEntity(id: string): Promise<Record<string, unknown>> {
  return fetchJson<Record<string, unknown>>(`/api/entities/${encodeURIComponent(id)}`);
}

export async function fetchTimeline(id: string): Promise<{ timeline: TimelineItem[] }> {
  return fetchJson<{ timeline: TimelineItem[] }>(`/api/entities/${encodeURIComponent(id)}/timeline`);
}

export async function fetchRelationships(id: string): Promise<{ relationships: RelationshipItem[] }> {
  return fetchJson<{ relationships: RelationshipItem[] }>(`/api/entities/${encodeURIComponent(id)}/relationships`);
}

export async function fetchCommunications(id: string): Promise<{ communications: CommunicationItem[] }> {
  return fetchJson<{ communications: CommunicationItem[] }>(`/api/entities/${encodeURIComponent(id)}/communications`);
}

export async function fetchEntityCommitments(id: string): Promise<{ commitments: CommitmentItem[] }> {
  return fetchJson<{ commitments: CommitmentItem[] }>(`/api/entities/${encodeURIComponent(id)}/commitments`);
}

export async function fetchOpenCommitments(): Promise<{ commitments: CommitmentItem[] }> {
  return fetchJson<{ commitments: CommitmentItem[] }>("/api/commitments/open");
}

export async function fetchOverdueInvoices(): Promise<{ invoices: InvoiceEntity[] }> {
  return fetchJson<{ invoices: InvoiceEntity[] }>("/api/invoices/overdue");
}

export async function fetchRecentEvents(limit = 20): Promise<{ events: RecentEvent[] }> {
  return fetchJson<{ events: RecentEvent[] }>(`/api/events/recent?limit=${limit}`);
}

export async function fetchProvenance(factId: string): Promise<{ provenance: ProvenanceRecord[] }> {
  return fetchJson<{ provenance: ProvenanceRecord[] }>(`/api/provenance/${encodeURIComponent(factId)}`);
}
