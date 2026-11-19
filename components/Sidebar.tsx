"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { deleteConversation, listConversations, type ConversationSummary } from "@/lib/api";
import { chatCache, CONVERSATIONS_CHANGED } from "@/lib/chat-store";
import { BrainMark, ChatIcon, LibraryIcon, PlusIcon, TrashIcon } from "./icons";

const nav = [
  { href: "/", label: "New chat", short: "Chat", icon: ChatIcon },
  { href: "/items", label: "Library", short: "Library", icon: LibraryIcon },
  { href: "/items/new", label: "Add Item", short: "Add", icon: PlusIcon },
];

function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (Number.isNaN(diff)) return "";
  if (diff < 60) return "now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function Sidebar() {
  return <SidebarView pathname={usePathname()} />;
}

/**
 * Static stand-in rendered while the pathname is unknown during prerendering
 * (dynamic routes like /c/[sessionId] with cacheComponents). Same layout, no
 * active state, no data fetching — so nothing shifts when the real one mounts.
 */
export function SidebarFallback() {
  return <SidebarView pathname={null} />;
}

function SidebarView({ pathname }: { pathname: string | null }) {
  const router = useRouter();
  const [chats, setChats] = useState<ConversationSummary[] | null>(null);
  const live = pathname !== null;

  // Load recent chats; refresh whenever a chat gets a new message
  useEffect(() => {
    if (!live) return;
    let cancelled = false;
    const fetchChats = () =>
      listConversations()
        .then((c) => !cancelled && setChats(c))
        .catch(() => !cancelled && setChats((prev) => prev ?? []));
    fetchChats();
    window.addEventListener(CONVERSATIONS_CHANGED, fetchChats);
    return () => {
      cancelled = true;
      window.removeEventListener(CONVERSATIONS_CHANGED, fetchChats);
    };
  }, [live]);

  async function removeChat(id: string) {
    setChats((prev) => prev?.filter((c) => c.session_id !== id) ?? null);
    chatCache.delete(id);
    if (pathname === `/c/${id}`) router.push("/");
    try {
      await deleteConversation(id);
    } catch {
      listConversations().then(setChats).catch(() => {});
    }
  }

  const inChat = pathname === "/" || Boolean(pathname?.startsWith("/c/"));

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-line bg-surface/70 backdrop-blur-xl">
        <div className="flex items-center gap-3 px-5 h-16">
          <span className="grid place-items-center size-9 rounded-xl bg-gradient-accent text-white shadow-lg shadow-accent/30">
            <BrainMark width={20} height={20} />
          </span>
          <div className="leading-tight">
            <p className="text-[15px] font-semibold tracking-tight">Knowledge Inbox</p>
            <p className="text-xs text-muted">Your second brain</p>
          </div>
        </div>

        <nav className="flex flex-col gap-1 p-3 mt-2">
          <p className="px-3 pb-2 text-[11px] font-medium uppercase tracking-wider text-muted/80">
            Workspace
          </p>
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                  active
                    ? "bg-accent/10 text-accent"
                    : "text-muted hover:bg-surface-muted hover:text-foreground"
                }`}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-1 rounded-r-full bg-gradient-accent" />
                )}
                <Icon className="transition-transform group-hover:scale-110" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Recent chats — each one is its own session window at /c/<session_id> */}
        <div className="flex min-h-0 flex-1 flex-col px-3">
          <p className="px-3 pb-2 pt-2 text-[11px] font-medium uppercase tracking-wider text-muted/80">
            Recent chats
          </p>
          <div className="min-h-0 flex-1 overflow-y-auto space-y-0.5 pb-2">
            {chats === null ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="skeleton mx-3 my-2 h-4" style={{ width: `${70 - i * 12}%` }} />
              ))
            ) : chats.length === 0 ? (
              <p className="px-3 py-2 text-xs text-muted/70">No conversations yet</p>
            ) : (
              chats.map((c) => {
                const href = `/c/${c.session_id}`;
                const active = pathname === href;
                return (
                  <div key={c.session_id} className="group relative">
                    <Link
                      href={href}
                      aria-current={active ? "page" : undefined}
                      title={c.title}
                      className={`flex items-center gap-2 rounded-lg py-2 pl-3 pr-9 text-[13px] transition-colors ${
                        active
                          ? "bg-accent/10 text-accent font-medium"
                          : "text-muted hover:bg-surface-muted hover:text-foreground"
                      }`}
                    >
                      <span className="min-w-0 flex-1 truncate">{c.title}</span>
                      <span className="shrink-0 text-[11px] tabular-nums opacity-60 group-hover:opacity-0">
                        {timeAgo(c.updated_at)}
                      </span>
                    </Link>
                    <button
                      onClick={() => removeChat(c.session_id)}
                      aria-label={`Delete conversation: ${c.title}`}
                      className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted opacity-0 transition hover:bg-red-500/10 hover:text-red-500 focus:opacity-100 group-hover:opacity-100"
                    >
                      <TrashIcon width={14} height={14} />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="m-3 rounded-2xl border border-line bg-surface-muted/60 p-4">
          <div className="flex items-center gap-2">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
            </span>
            <p className="text-xs font-medium">Local LLM</p>
          </div>
          <p className="mt-1 text-xs text-muted">Private · runs on your machine</p>
          <p className="mt-3 text-[11px] text-muted/70 font-mono">v0.1.0</p>
        </div>
      </aside>

      {/* Mobile bottom bar */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 flex justify-around border-t border-line bg-surface/85 backdrop-blur-xl pb-[env(safe-area-inset-bottom)]">
        {nav.map(({ href, short, icon: Icon }) => {
          const active = href === "/" ? inChat : pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium ${
                active ? "text-accent" : "text-muted"
              }`}
            >
              <Icon width={20} height={20} />
              {short}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
