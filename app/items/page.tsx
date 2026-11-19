"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getItems, deleteItem, startIngestion, type Item } from "@/lib/api";
import {
  AlertIcon,
  CheckIcon,
  LibraryIcon,
  LinkIcon,
  NoteIcon,
  PlusIcon,
  RefreshIcon,
  SearchIcon,
  TrashIcon,
} from "@/components/icons";

const statusStyle: Record<Item["status"], { label: string; badge: string; dot: string }> = {
  pending: {
    label: "Pending",
    badge: "bg-amber-500/10 text-amber-700 dark:text-amber-300 ring-amber-500/20",
    dot: "bg-amber-500",
  },
  processing: {
    label: "Processing",
    badge: "bg-sky-500/10 text-sky-700 dark:text-sky-300 ring-sky-500/20",
    dot: "bg-sky-500 animate-pulse",
  },
  completed: {
    label: "Ready",
    badge: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 ring-emerald-500/20",
    dot: "bg-emerald-500",
  },
  failed: {
    label: "Failed",
    badge: "bg-red-500/10 text-red-700 dark:text-red-300 ring-red-500/20",
    dot: "bg-red-500",
  },
};

type Filter = "all" | Item["status"];

type Toast = { kind: "success" | "error"; text: string } | null;

function formatDate(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function ItemsPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [toast, setToast] = useState<Toast>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [confirmId, setConfirmId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await getItems());
      setLoadError("");
    } catch (e: unknown) {
      setLoadError(e instanceof Error ? e.message : "Failed to load items");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    getItems()
      .then((data) => !cancelled && setItems(data))
      .catch((e: unknown) => {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : "Failed to load items");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  // Poll while anything is still being ingested
  const busy = items.some((i) => i.status === "pending" || i.status === "processing");
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [busy, load]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2800);
    return () => clearTimeout(t);
  }, [toast]);

  async function handleIngest(id: number) {
    try {
      await startIngestion(id);
      setItems((prev) => prev.map((i) => (i.id === id ? { ...i, status: "processing" } : i)));
      setToast({ kind: "success", text: "Ingestion started" });
      setTimeout(load, 1500);
    } catch (e: unknown) {
      setToast({ kind: "error", text: e instanceof Error ? e.message : "Error" });
    }
  }

  async function handleDelete(id: number) {
    setConfirmId(null);
    try {
      await deleteItem(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      setToast({ kind: "success", text: "Item deleted" });
    } catch (e: unknown) {
      setToast({ kind: "error", text: e instanceof Error ? e.message : "Error" });
    }
  }

  const counts = useMemo(() => {
    const c = { all: items.length, completed: 0, processing: 0, pending: 0, failed: 0 };
    for (const i of items) c[i.status]++;
    return c;
  }, [items]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter(
      (i) => (filter === "all" || i.status === filter) && (!q || i.title.toLowerCase().includes(q))
    );
  }, [items, query, filter]);

  const filters: { key: Filter; label: string }[] = [
    { key: "all", label: "All" },
    { key: "completed", label: "Ready" },
    { key: "processing", label: "Processing" },
    { key: "pending", label: "Pending" },
    { key: "failed", label: "Failed" },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8 animate-fade-up">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Library</h1>
          <p className="text-sm text-muted mt-1">Everything you&apos;ve saved, ready to search.</p>
        </div>
        <Link href="/items/new" className="btn-primary w-fit">
          <PlusIcon width={16} height={16} />
          Add Item
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Total items", value: counts.all, accent: "text-foreground" },
          { label: "Ready", value: counts.completed, accent: "text-emerald-500" },
          { label: "In progress", value: counts.processing + counts.pending, accent: "text-sky-500" },
          { label: "Failed", value: counts.failed, accent: "text-red-500" },
        ].map((s, i) => (
          <div
            key={s.label}
            className="card px-5 py-4 animate-fade-up"
            style={{ animationDelay: `${i * 50}ms` }}
          >
            <p className="text-xs text-muted">{s.label}</p>
            {loading ? (
              <div className="skeleton h-8 w-12 mt-1.5" />
            ) : (
              <p className={`mt-1 text-3xl font-semibold tabular-nums tracking-tight ${s.accent}`}>
                {s.value}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="relative flex-1">
          <SearchIcon
            width={16}
            height={16}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted pointer-events-none"
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title…"
            aria-label="Search items"
            className="field pl-10!"
          />
        </div>
        <div className="flex gap-1 overflow-x-auto rounded-xl border border-line bg-surface p-1">
          {filters.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              aria-pressed={filter === f.key}
              className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                filter === f.key
                  ? "bg-accent/10 text-accent"
                  : "text-muted hover:text-foreground hover:bg-surface-muted"
              }`}
            >
              {f.label}
              <span className="ml-1.5 tabular-nums opacity-60">{counts[f.key]}</span>
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      {loading ? (
        <div className="card divide-y divide-line">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-5 py-4">
              <div className="skeleton size-10 rounded-xl" />
              <div className="flex-1 space-y-2">
                <div className="skeleton h-3.5 w-1/3" />
                <div className="skeleton h-3 w-1/5" />
              </div>
            </div>
          ))}
        </div>
      ) : loadError ? (
        <div className="card flex flex-col items-center text-center px-6 py-16">
          <div className="grid place-items-center size-12 rounded-2xl bg-red-500/10 text-red-500 mb-4">
            <AlertIcon />
          </div>
          <p className="font-medium">Couldn&apos;t load your library</p>
          <p className="text-sm text-muted mt-1">{loadError}. Is the backend running?</p>
          <button onClick={() => { setLoading(true); load(); }} className="btn-ghost mt-5">
            <RefreshIcon width={14} height={14} /> Try again
          </button>
        </div>
      ) : items.length === 0 ? (
        <div className="card flex flex-col items-center text-center px-6 py-20 animate-fade-up">
          <div className="grid place-items-center size-14 rounded-2xl bg-accent/10 text-accent mb-5">
            <LibraryIcon width={26} height={26} />
          </div>
          <p className="text-lg font-semibold tracking-tight">Your library is empty</p>
          <p className="text-sm text-muted mt-1 max-w-sm">
            Save a note or a link and it&apos;ll be indexed so you can ask questions about it.
          </p>
          <Link href="/items/new" className="btn-primary mt-6">
            <PlusIcon width={16} height={16} /> Add your first item
          </Link>
        </div>
      ) : visible.length === 0 ? (
        <div className="card text-center px-6 py-14 text-sm text-muted">
          No items match your filters.
        </div>
      ) : (
        <ul className="card divide-y divide-line overflow-hidden">
          {visible.map((item, i) => {
            const st = statusStyle[item.status];
            const TypeIcon = item.source_type === "url" ? LinkIcon : NoteIcon;
            return (
              <li
                key={item.id}
                className="group flex items-center gap-4 px-4 sm:px-5 py-4 transition-colors hover:bg-surface-muted/60 animate-fade-up"
                style={{ animationDelay: `${Math.min(i, 10) * 30}ms` }}
              >
                <div
                  className={`grid place-items-center size-10 shrink-0 rounded-xl ${
                    item.source_type === "url"
                      ? "bg-sky-500/10 text-sky-600 dark:text-sky-400"
                      : "bg-violet-500/10 text-violet-600 dark:text-violet-400"
                  }`}
                >
                  <TypeIcon />
                </div>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{item.title}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {item.source_type === "url" ? "Link" : "Note"}
                    {item.created_at && <> · {formatDate(item.created_at)}</>}
                  </p>
                </div>

                <span
                  className={`hidden sm:inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${st.badge}`}
                >
                  <span className={`size-1.5 rounded-full ${st.dot}`} />
                  {st.label}
                </span>

                <div className="flex items-center gap-1.5">
                  {confirmId === item.id ? (
                    <>
                      <button
                        onClick={() => handleDelete(item.id)}
                        className="rounded-lg bg-red-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-600 transition"
                      >
                        Delete
                      </button>
                      <button onClick={() => setConfirmId(null)} className="btn-ghost py-1.5! px-3!">
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      {item.status !== "processing" && (
                        <button
                          onClick={() => handleIngest(item.id)}
                          className="btn-ghost py-1.5! px-3!"
                          title={item.status === "completed" ? "Re-ingest" : "Ingest"}
                        >
                          <RefreshIcon width={14} height={14} />
                          <span className="hidden sm:inline">
                            {item.status === "completed" ? "Re-ingest" : "Ingest"}
                          </span>
                        </button>
                      )}
                      <button
                        onClick={() => setConfirmId(item.id)}
                        aria-label={`Delete ${item.title}`}
                        className="rounded-lg p-2 text-muted transition hover:bg-red-500/10 hover:text-red-500"
                      >
                        <TrashIcon width={16} height={16} />
                      </button>
                    </>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* Toast */}
      {toast && (
        <div
          role="status"
          className="fixed bottom-20 md:bottom-6 left-1/2 -translate-x-1/2 z-50 animate-fade-up"
        >
          <div className="flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2.5 text-sm shadow-xl">
            {toast.kind === "success" ? (
              <CheckIcon width={16} height={16} className="text-emerald-500" />
            ) : (
              <AlertIcon width={16} height={16} className="text-red-500" />
            )}
            {toast.text}
          </div>
        </div>
      )}
    </div>
  );
}
