import type { Citation } from "./api";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

/**
 * In-memory messages per session for this browser tab, so switching between
 * chats (and the /  →  /c/[id] redirect) is instant. A full page reload falls
 * back to the history stored on the server, which includes citations.
 */
export const chatCache = new Map<string, ChatMessage[]>();

export const CONVERSATIONS_CHANGED = "ki:conversations-changed";

/** Tell the sidebar to refresh its "Recent chats" list. */
export function notifyConversationsChanged() {
  window.dispatchEvent(new Event(CONVERSATIONS_CHANGED));
}
