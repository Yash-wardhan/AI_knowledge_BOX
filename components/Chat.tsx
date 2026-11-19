"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { askQuestion, getConversationMessages, NotFoundError } from "@/lib/api";
import { chatCache, notifyConversationsChanged, type ChatMessage } from "@/lib/chat-store";
import {
  AlertIcon,
  BrainMark,
  ExternalIcon,
  PlusIcon,
  SendIcon,
  ShieldIcon,
  SparkIcon,
} from "@/components/icons";

type Message = ChatMessage;

const suggestions = [
  "Summarize what I've saved recently",
  "What are the key ideas across my notes?",
  "Find anything I saved about productivity",
  "Which sources mention AI agents?",
];

/**
 * One conversation window.
 * - No `sessionId` → a brand-new chat. The first successful answer creates a
 *   session on the backend and we move to /c/<session_id>.
 * - With `sessionId` → loads that conversation's history and continues it.
 * Mount with `key={sessionId}` so switching chats starts from fresh state.
 */
export default function Chat({ sessionId }: { sessionId?: string }) {
  const router = useRouter();
  const cached = sessionId ? chatCache.get(sessionId) : undefined;

  const [messages, setMessages] = useState<Message[]>(cached ?? []);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [restoring, setRestoring] = useState(Boolean(sessionId && !cached));
  const [notFound, setNotFound] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load this session's history from the server (unless already cached in this tab)
  useEffect(() => {
    if (!sessionId || chatCache.has(sessionId)) return;
    let cancelled = false;
    getConversationMessages(sessionId)
      .then((history) => {
        if (cancelled) return;
        const restored = history.map((m) => ({
          role: m.role,
          content: m.content,
          citations: m.citations,
        }));
        chatCache.set(sessionId, restored);
        setMessages(restored);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (e instanceof NotFoundError) setNotFound(true);
        else setError(e instanceof Error ? e.message : "Failed to load conversation");
      })
      .finally(() => !cancelled && setRestoring(false));
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Auto-grow the textarea
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [input]);

  async function send(text: string) {
    const question = text.trim();
    if (!question || loading) return;

    const withQuestion: Message[] = [...messages, { role: "user", content: question }];
    setInput("");
    setError("");
    setMessages(withQuestion);
    setLoading(true);

    try {
      const res = await askQuestion(question, sessionId ?? null);
      const done: Message[] = [
        ...withQuestion,
        { role: "assistant", content: res.answer, citations: res.citations },
      ];
      setMessages(done);

      const id = res.session_id ?? sessionId;
      if (id) {
        chatCache.set(id, done);
        notifyConversationsChanged();
        // New chat just got its session → give it its own URL
        if (!sessionId) router.replace(`/c/${id}`);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    send(input);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send(input);
    }
  }

  const empty = messages.length === 0 && !restoring && !notFound;
  const title = messages.find((m) => m.role === "user")?.content ?? "New chat";

  if (notFound) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6 text-center animate-fade-up">
        <div className="grid place-items-center size-12 rounded-2xl bg-surface-muted text-muted mb-4">
          <AlertIcon />
        </div>
        <p className="font-medium">Conversation not found</p>
        <p className="mt-1 text-sm text-muted">It may have been deleted.</p>
        <Link href="/" className="btn-primary mt-6">
          <PlusIcon width={16} height={16} /> Start a new chat
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto px-4 sm:px-6">
      {/* Header */}
      <header className="flex items-center justify-between py-5">
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold tracking-tight">
            {restoring ? <span className="skeleton inline-block h-5 w-48 align-middle" /> : title}
          </h1>
          <p className="text-xs text-muted mt-0.5">Grounded in your saved items</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full border border-line bg-surface/80 px-3 py-1 text-xs text-muted">
            <ShieldIcon width={14} height={14} className="text-emerald-500" />
            NeMo Guardrails
          </span>
          {sessionId && (
            <Link href="/" className="btn-ghost py-1.5! px-3! rounded-full!">
              <PlusIcon width={14} height={14} />
              New chat
            </Link>
          )}
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto -mx-4 px-4 sm:-mx-6 sm:px-6">
        {empty ? (
          <div className="flex flex-col items-center justify-center text-center min-h-full py-10 animate-fade-up">
            <div className="relative mb-6">
              <div className="absolute inset-0 rounded-3xl bg-gradient-accent blur-2xl opacity-40" />
              <div className="relative grid place-items-center size-16 rounded-3xl bg-gradient-accent text-white shadow-xl">
                <SparkIcon width={30} height={30} />
              </div>
            </div>
            <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight">
              What would you like to <span className="text-gradient">know</span>?
            </h2>
            <p className="mt-3 max-w-md text-sm text-muted">
              Ask anything about your saved notes and links. Every answer comes with
              sources you can check.
            </p>

            <div className="mt-10 grid w-full max-w-xl grid-cols-1 sm:grid-cols-2 gap-3">
              {suggestions.map((s, i) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  style={{ animationDelay: `${100 + i * 60}ms` }}
                  className="card animate-fade-up group text-left px-4 py-3.5 text-sm transition hover:-translate-y-0.5 hover:border-accent/40"
                >
                  <span className="text-foreground/90 group-hover:text-foreground">{s}</span>
                  <SendIcon
                    width={14}
                    height={14}
                    className="inline ml-1.5 -translate-x-1 opacity-0 text-accent transition group-hover:translate-x-0 group-hover:opacity-100"
                  />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-6 py-4">
            {restoring && (
              <div className="space-y-6" aria-label="Loading conversation">
                <div className="flex justify-end"><div className="skeleton h-11 w-2/5 rounded-2xl" /></div>
                <div className="flex gap-3"><div className="skeleton size-8 rounded-xl" /><div className="skeleton h-24 flex-1 rounded-2xl" /></div>
              </div>
            )}
            {messages.map((msg, i) =>
              msg.role === "user" ? (
                <div key={i} className="flex justify-end animate-fade-up">
                  <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-accent px-4 py-3 text-sm leading-relaxed text-white shadow-lg shadow-accent/20">
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ) : (
                <div key={i} className="flex gap-3 animate-fade-up">
                  <Avatar />
                  <div className="min-w-0 flex-1">
                    <div className="card rounded-tl-md px-5 py-4 text-[15px] leading-relaxed">
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>

                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3">
                        <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted">
                          Sources · {msg.citations.length}
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {msg.citations.map((c) => (
                            <div
                              key={c.chunk_id}
                              className="group rounded-xl border border-line bg-surface/70 p-3 transition hover:border-accent/40 hover:bg-surface"
                            >
                              <div className="flex items-center gap-2">
                                <span className="grid place-items-center min-w-6 h-6 px-1.5 rounded-md bg-accent/10 text-[11px] font-semibold text-accent">
                                  {c.source_label}
                                </span>
                                <span className="truncate text-xs font-medium">{c.title}</span>
                                {c.source_url && (
                                  <a
                                    href={c.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    aria-label={`Open ${c.title}`}
                                    className="ml-auto shrink-0 rounded-md p-1 text-muted hover:bg-surface-muted hover:text-accent"
                                  >
                                    <ExternalIcon width={14} height={14} />
                                  </a>
                                )}
                              </div>
                              <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted">
                                {c.content}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            )}

            {loading && (
              <div className="flex gap-3 animate-fade-up">
                <Avatar pulsing />
                <div className="card rounded-tl-md px-5 py-4 flex items-center gap-3">
                  <div className="flex gap-1">
                    <span className="size-1.5 rounded-full bg-accent animate-bounce [animation-delay:-0.3s]" />
                    <span className="size-1.5 rounded-full bg-accent animate-bounce [animation-delay:-0.15s]" />
                    <span className="size-1.5 rounded-full bg-accent animate-bounce" />
                  </div>
                  <span className="text-xs text-muted">Searching your knowledge…</span>
                </div>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="my-4 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-600 dark:text-red-400 animate-fade-up">
            <AlertIcon width={16} height={16} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <div className="pt-2 pb-5">
        <form
          onSubmit={handleSubmit}
          className="card flex items-end gap-2 p-2 pl-4 transition focus-within:border-accent/50 focus-within:shadow-[0_0_0_4px_color-mix(in_oklab,var(--accent)_12%,transparent)]"
        >
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your notes…"
            aria-label="Your question"
            className="flex-1 resize-none bg-transparent py-2.5 text-[15px] outline-none placeholder:text-muted/70"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            aria-label="Send"
            className="btn-primary size-10 p-0! shrink-0 rounded-xl"
          >
            <SendIcon width={18} height={18} />
          </button>
        </form>
        <p className="mt-2 text-center text-[11px] text-muted/70">
          <kbd className="font-mono">Enter</kbd> to send ·{" "}
          <kbd className="font-mono">Shift + Enter</kbd> for a new line
        </p>
      </div>
    </div>
  );
}

function Avatar({ pulsing = false }: { pulsing?: boolean }) {
  return (
    <div
      className={`grid place-items-center size-8 shrink-0 rounded-xl bg-gradient-accent text-white shadow-md shadow-accent/25 ${
        pulsing ? "animate-pulse" : ""
      }`}
    >
      <BrainMark width={16} height={16} />
    </div>
  );
}
