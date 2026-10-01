export type EntityType = "customer" | "supplier" | "product" | "order" | "invoice" | "employee";

export interface EntitySummary {
  id: string;
  entity_type: EntityType;
  canonical_name: string;
  status: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface CustomerEntity {
  id: string;
  canonical_name: string;
  aliases: string[];
  contact_names: string[];
  emails: string[];
  phones: string[];
  addresses: string[];
  status: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface SupplierEntity {
  id: string;
  canonical_name: string;
  aliases: string[];
  contact_names: string[];
  emails: string[];
  phones: string[];
  payment_terms: string;
  status: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface OrderEntity {
  id: string;
  customer_id: string;
  order_number: string;
  order_date: string;
  status: string;
  total_amount: number;
  currency: string;
}

export interface InvoiceEntity {
  id: string;
  customer_id?: string;
  supplier_id?: string;
  invoice_number: string;
  issue_date: string;
  due_date?: string;
  amount: number;
  currency: string;
  status: "DRAFT" | "SENT" | "PAID" | "OVERDUE" | "CANCELLED";
}

export interface TimelineItem {
  kind: "event" | "communication" | "commitment" | "order" | "invoice";
  id: string;
  type?: string;
  subject?: string;
  sender?: string;
  description?: string;
  status?: string;
  total_amount?: number;
  amount?: number;
  currency?: string;
  invoice_number?: string;
  timestamp: string;
  due_date?: string | null;
  confidence?: number;
  raw_item_id?: string;
  metadata?: Record<string, unknown>;
}

export interface RelationshipItem {
  id: string;
  from_id: string;
  to_id: string;
  rel_type: string;
  other_entity_id: string;
  other_entity_name: string;
  other_entity_type: string;
  created_at: string;
}

export interface CommunicationItem {
  id: string;
  type: string;
  sender: string;
  recipient: string;
  subject: string;
  timestamp: string;
  raw_item_id: string;
  thread_id?: string;
}

export interface CommitmentItem {
  id: string;
  related_entity_id: string;
  description: string;
  owner: string;
  due_date?: string | null;
  status: "OPEN" | "FULFILLED" | "CANCELLED";
  confidence: number;
  created_at: string;
}

export interface ProvenanceRecord {
  fact_id: string;
  raw_item_id: string;
  source: "gmail" | "drive" | "quickbooks";
  source_url?: string;
  extracted_at: string;
  confidence: number;
  extractor_name: string;
  raw_snippet?: string;
}

export interface RecentEvent {
  id: string;
  type: string;
  entity_id: string;
  timestamp: string;
  raw_item_id: string;
  metadata?: Record<string, unknown>;
}
