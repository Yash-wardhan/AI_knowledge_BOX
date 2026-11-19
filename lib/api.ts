const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────────────────────

export interface Item {
  id: number;
  title: string;
  source_type: "text" | "url";
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
}

export interface ItemDetail extends Item {
  raw_content: string;
  source_url: string | null;
}

export interface Citation {
  source_label: string;
  chunk_id: number;
  item_id: number;
  title: string;
  source_url: string | null;
  content: string;
}

export interface AskResponse {
  question: string;
  answer: string;
  citations: Citation[];
  session_id: string | null;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

// ── Items ────────────────────────────────────────────────────────────────────

export async function getItems(): Promise<Item[]> {
  const res = await fetch(`${BASE_URL}/items/`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch items");
  return res.json();
}

export async function getItem(id: number): Promise<ItemDetail> {
  const res = await fetch(`${BASE_URL}/items/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch item");
  return res.json();
}

export async function createItem(payload: {
  title: string;
  source_type: "text" | "url";
  content?: string;
  source_url?: string;
}): Promise<{ message: string; data: Item }> {
  const res = await fetch(`${BASE_URL}/items/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Failed to create item");
  }
  return res.json();
}

export async function deleteItem(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/items/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete item");
}

// ── Ingestion ─────────────────────────────────────────────────────────────────

export async function startIngestion(itemId: number) {
  const res = await fetch(`${BASE_URL}/ingestion/${itemId}`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Failed to start ingestion");
  }
  return res.json();
}

// ── Query / Ask ───────────────────────────────────────────────────────────────

export async function askQuestion(
  question: string,
  sessionId?: string | null,
  top_k = 5
): Promise<AskResponse> {
  const res = await fetch(`${BASE_URL}/query/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k, session_id: sessionId ?? null }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Failed to get answer");
  }
  return res.json();
}

// ── Conversations ─────────────────────────────────────────────────────────────

export class NotFoundError extends Error {}

export async function getConversationMessages(
  sessionId: string
): Promise<ConversationMessage[]> {
  const res = await fetch(`${BASE_URL}/conversations/${sessionId}/messages`, {
    cache: "no-store",
  });
  if (res.status === 404) throw new NotFoundError("Conversation not found");
  if (!res.ok) throw new Error("Failed to load conversation");
  const data: { messages: ConversationMessage[] } = await res.json();
  return data.messages;
}

export interface ConversationSummary {
  session_id: string;
  title: string;
  updated_at: string;
  message_count: number;
}

export async function listConversations(): Promise<ConversationSummary[]> {
  const res = await fetch(`${BASE_URL}/conversations/`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load conversations");
  const data: { conversations: ConversationSummary[] } = await res.json();
  return data.conversations;
}

export async function deleteConversation(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/conversations/${sessionId}`, { method: "DELETE" });
  if (!res.ok && res.status !== 404) throw new Error("Failed to delete conversation");
}
