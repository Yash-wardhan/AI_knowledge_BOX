"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createItem, startIngestion } from "@/lib/api";
import { AlertIcon, ArrowLeftIcon, LinkIcon, NoteIcon, SparkIcon } from "@/components/icons";

type SourceType = "text" | "url";

const types: { key: SourceType; label: string; hint: string; icon: typeof NoteIcon }[] = [
  { key: "text", label: "Text note", hint: "Paste or write anything", icon: NoteIcon },
  { key: "url", label: "Web link", hint: "We'll fetch the page for you", icon: LinkIcon },
];

export default function NewItemPage() {
  const router = useRouter();
  const [sourceType, setSourceType] = useState<SourceType>("text");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [url, setUrl] = useState("");
  const [autoIngest, setAutoIngest] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const payload =
        sourceType === "text"
          ? { title, source_type: "text" as const, content }
          : { title, source_type: "url" as const, source_url: url };

      const result = await createItem(payload);
      const itemId = result.data.id;

      if (autoIngest) {
        await startIngestion(itemId);
      }

      router.push("/items");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const words = content.trim() ? content.trim().split(/\s+/).length : 0;

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      <Link
        href="/items"
        className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-foreground transition mb-6"
      >
        <ArrowLeftIcon width={16} height={16} /> Back to library
      </Link>

      <div className="mb-8 animate-fade-up">
        <h1 className="text-3xl font-semibold tracking-tight">Add to your library</h1>
        <p className="text-sm text-muted mt-1">
          Save a note or link — it&apos;ll be chunked, embedded, and ready to ask about.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card p-6 sm:p-8 space-y-6 animate-fade-up [animation-delay:80ms]">
        {/* Source type */}
        <fieldset>
          <legend className="text-sm font-medium mb-3">What are you saving?</legend>
          <div className="grid grid-cols-2 gap-3">
            {types.map(({ key, label, hint, icon: Icon }) => {
              const active = sourceType === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setSourceType(key)}
                  aria-pressed={active}
                  className={`relative flex flex-col items-start gap-3 rounded-2xl border p-4 text-left transition ${
                    active
                      ? "border-accent/60 bg-accent/5 ring-4 ring-accent/10"
                      : "border-line hover:border-foreground/20 hover:bg-surface-muted/50"
                  }`}
                >
                  <span
                    className={`grid place-items-center size-9 rounded-xl transition ${
                      active ? "bg-gradient-accent text-white shadow-md shadow-accent/30" : "bg-surface-muted text-muted"
                    }`}
                  >
                    <Icon width={18} height={18} />
                  </span>
                  <span>
                    <span className="block text-sm font-medium">{label}</span>
                    <span className="block text-xs text-muted mt-0.5">{hint}</span>
                  </span>
                  <span
                    className={`absolute top-4 right-4 size-4 rounded-full border-2 transition ${
                      active ? "border-accent bg-accent shadow-[inset_0_0_0_3px_var(--surface)]" : "border-line"
                    }`}
                  />
                </button>
              );
            })}
          </div>
        </fieldset>

        {/* Title */}
        <div>
          <label htmlFor="title" className="block text-sm font-medium mb-2">
            Title
          </label>
          <input
            id="title"
            required
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Give it a memorable name"
            className="field"
          />
        </div>

        {/* Content or URL */}
        {sourceType === "text" ? (
          <div key="text" className="animate-fade-up">
            <div className="flex items-baseline justify-between mb-2">
              <label htmlFor="content" className="text-sm font-medium">
                Content
              </label>
              <span className="text-xs text-muted tabular-nums">
                {words} {words === 1 ? "word" : "words"}
              </span>
            </div>
            <textarea
              id="content"
              required
              rows={9}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste or type your note here…"
              className="field resize-y min-h-40 leading-relaxed"
            />
          </div>
        ) : (
          <div key="url" className="animate-fade-up">
            <label htmlFor="url" className="block text-sm font-medium mb-2">
              URL
            </label>
            <div className="relative">
              <LinkIcon
                width={16}
                height={16}
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted pointer-events-none"
              />
              <input
                id="url"
                required
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/article"
                className="field pl-10!"
              />
            </div>
          </div>
        )}

        {/* Auto-ingest */}
        <div className="flex items-center justify-between gap-4 rounded-2xl border border-line bg-surface-muted/50 px-4 py-3.5">
          <div className="flex items-center gap-3">
            <SparkIcon width={18} height={18} className="text-accent shrink-0" />
            <div>
              <p id="auto-ingest-label" className="text-sm font-medium">
                Ingest right away
              </p>
              <p className="text-xs text-muted">Make it searchable as soon as it&apos;s saved</p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={autoIngest}
            aria-labelledby="auto-ingest-label"
            onClick={() => setAutoIngest((v) => !v)}
            className={`relative h-6 w-11 shrink-0 rounded-full transition ${
              autoIngest ? "bg-gradient-accent" : "bg-line"
            }`}
          >
            <span
              className={`absolute top-1 left-1 size-4 rounded-full bg-white shadow transition-transform ${
                autoIngest ? "translate-x-5" : ""
              }`}
            />
          </button>
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-600 dark:text-red-400">
            <AlertIcon width={16} height={16} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col-reverse sm:flex-row gap-3 pt-2">
          <button type="button" onClick={() => router.back()} className="btn-ghost px-5! py-2.5!">
            Cancel
          </button>
          <button type="submit" disabled={loading} className="btn-primary flex-1">
            {loading ? (
              <>
                <span className="size-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                Saving…
              </>
            ) : (
              "Save to library"
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
