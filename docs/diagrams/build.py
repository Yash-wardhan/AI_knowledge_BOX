"""
Generate the architecture diagrams as HTML/SVG, then render them to PNG.

    python3 docs/diagrams/build.py          # writes docs/diagrams/*.html and docs/*.png

No dependencies beyond Python 3 and Google Chrome (used headless to rasterise).
Edit the data below (tables / steps) and re-run to update the PNGs.
"""

import html
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]

ACCENT = "#6d5dfc"
ACCENT_2 = "#b061ff"

BASE_CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
  background: #f7f7fb; color: #18181b; -webkit-font-smoothing: antialiased;
}}
.canvas {{ position: relative; overflow: hidden;
  background:
    radial-gradient(900px 500px at 100% 0%, rgba(109,93,252,.10), transparent 60%),
    radial-gradient(rgba(24,24,27,.06) 1px, transparent 1px) 0 0/22px 22px, #f7f7fb; }}
h1 {{ font-size: 30px; letter-spacing: -.02em; font-weight: 700; }}
.sub {{ color: #71717a; font-size: 15px; margin-top: 6px; }}
.grad {{ background: linear-gradient(120deg, {ACCENT}, {ACCENT_2}); -webkit-background-clip: text; color: transparent; }}
.mono {{ font-family: "SF Mono", ui-monospace, Menlo, monospace; }}
"""


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# ───────────────────────────────────────────────────────────────────────────────
# 1. Database design (ER diagram)
# ───────────────────────────────────────────────────────────────────────────────

ROW_H = 34
HEAD_H = 58

# (name, type, tags, note)   tags: PK, FK, UQ, IDX
TABLES = {
    "items": dict(x=60, y=230, w=450, color="#6d5dfc", subtitle="Saved notes & URLs", rows=[
        ("id", "integer", "PK", ""),
        ("title", "varchar(255)", "", ""),
        ("source_type", "varchar(20)", "", "text | url"),
        ("source_url", "text", "", "nullable"),
        ("raw_content", "text", "", "URL page text"),
        ("content_hash", "varchar(64)", "IDX", "unused"),
        ("status", "varchar(20)", "", "pending · done · failed"),
        ("created_at", "timestamptz", "", ""),
        ("updated_at", "timestamptz", "", ""),
    ]),
    "chunks": dict(x=630, y=70, w=450, color="#0ea5e9", subtitle="Embedded text pieces (RAG)", rows=[
        ("id", "integer", "PK", ""),
        ("item_id", "integer", "FK", "→ items.id"),
        ("chunk_index", "integer", "", "order in item"),
        ("content", "text", "", "≤500 tokens"),
        ("embedding", "vector(768)", "", "pgvector"),
        ("token_count", "integer", "", "nullable"),
    ]),
    "ingestion_jobs": dict(x=630, y=560, w=450, color="#a1a1aa", subtitle="Job tracking — not written yet", rows=[
        ("id", "integer", "PK", ""),
        ("item_id", "integer", "FK", "→ items.id"),
        ("status", "varchar(20)", "", ""),
        ("attempts", "integer", "", ""),
        ("error_message", "text", "", "nullable"),
        ("created_at", "timestamptz", "", ""),
        ("updated_at", "timestamptz", "", ""),
    ]),
    "conversations": dict(x=1170, y=70, w=450, color="#10b981", subtitle="One chat window = one session", rows=[
        ("id", "uuid", "PK", "internal"),
        ("session_id", "uuid", "UQ", "public · /c/{id}"),
        ("created_at", "timestamptz", "", ""),
        ("updated_at", "timestamptz", "", ""),
    ]),
    "messages": dict(x=1170, y=390, w=450, color="#f59e0b", subtitle="Chat history", rows=[
        ("id", "integer", "PK", ""),
        ("conversation_id", "uuid", "FK", "→ conversations"),
        ("role", "varchar(20)", "", "user | assistant"),
        ("content", "text", "", ""),
        ("citations", "jsonb", "", "sources"),
        ("created_at", "timestamptz", "", ""),
    ]),
}

# (from_table, from_row, to_table, to_row, label)
RELATIONS = [
    ("items", 0, "chunks", 1, "1 : N"),
    ("items", 0, "ingestion_jobs", 1, "1 : N"),
    ("conversations", 0, "messages", 1, "1 : N"),
]

TAG_STYLE = {
    "PK": "background:#fef3c7;color:#92400e",
    "FK": "background:#e0e7ff;color:#3730a3",
    "UQ": "background:#d1fae5;color:#065f46",
    "IDX": "background:#f4f4f5;color:#52525b",
}


def row_y(t, i):
    return TABLES[t]["y"] + HEAD_H + i * ROW_H + ROW_H / 2


def table_html(name, t):
    rows = []
    for col, typ, tag, note in t["rows"]:
        badge = f'<span class="tag" style="{TAG_STYLE[tag]}">{tag}</span>' if tag else '<span class="tag ghost"></span>'
        rows.append(
            f'<div class="row">{badge}<span class="col mono">{esc(col)}</span>'
            f'<span class="typ mono">{esc(typ)}</span><span class="note">{esc(note)}</span></div>'
        )
    return (
        f'<div class="table" style="left:{t["x"]}px;top:{t["y"]}px;width:{t["w"]}px">'
        f'<div class="thead" style="--c:{t["color"]}"><span class="dot"></span>'
        f'<span class="tname mono">{name}</span><span class="tsub">{esc(t["subtitle"])}</span></div>'
        + "".join(rows) + "</div>"
    )


def relation_svg(a, ai, b, bi, label):
    ta, tb = TABLES[a], TABLES[b]
    y1, y2 = row_y(a, ai), row_y(b, bi)
    if ta["x"] == tb["x"]:  # stacked tables → loop out on the left
        x1 = x2 = ta["x"]
        path = f"M{x1} {y1} C{x1 - 70} {y1}, {x2 - 70} {y2}, {x2} {y2}"
        lx, ly = x1 - 58, (y1 + y2) / 2 + 4
        anchor = "middle"
    else:
        x1, x2 = ta["x"] + ta["w"], tb["x"]
        mid = (x1 + x2) / 2
        path = f"M{x1} {y1} C{mid} {y1}, {mid} {y2}, {x2} {y2}"
        lx, ly = mid, (y1 + y2) / 2 - 10
        anchor = "middle"
    return (
        f'<path d="{path}" fill="none" stroke="{ACCENT}" stroke-width="2" stroke-opacity=".55" '
        f'marker-start="url(#one)" marker-end="url(#many)"/>'
        f'<text x="{lx}" y="{ly}" text-anchor="{anchor}" class="rel">{esc(label)}</text>'
    )


def build_er() -> str:
    W, H = 1660, 1010
    svg = "".join(relation_svg(*r) for r in RELATIONS)
    tables = "".join(table_html(n, t) for n, t in TABLES.items())
    notes = [
        ("pgvector", "chunks.embedding is <b>vector(768)</b>. Retrieval orders by <b>cosine distance</b> and takes top_k (default 5)."),
        ("Cascades", "All 1:N links are DB-level <b>ON DELETE CASCADE</b>: deleting an item removes its chunks &amp; jobs; deleting a conversation removes its messages."),
        ("Sessions", "<b>session_id</b> is the public id used in the UI URL <span class='mono'>/c/{session_id}</span>; <b>id</b> stays internal."),
        ("Citations", "Stored as <b>jsonb</b> on assistant messages so sources survive reloads. Never replayed to the LLM."),
        ("Gaps", "No ANN index on embedding (sequential scan). <b>ingestion_jobs</b> and <b>content_hash</b> exist but aren't populated."),
    ]
    notes_html = "".join(
        f'<div class="nrow"><span class="nkey">{k}</span><span class="nval">{v}</span></div>' for k, v in notes
    )
    css = BASE_CSS + f"""
    .table {{ position:absolute; background:#fff; border:1px solid #e6e6ea; border-radius:16px; overflow:hidden;
      box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 12px 32px -14px rgba(24,24,27,.18); }}
    .thead {{ height:{HEAD_H}px; display:flex; align-items:center; gap:10px; padding:0 16px;
      background: linear-gradient(180deg, color-mix(in oklab, var(--c) 12%, #fff), #fff); border-bottom:1px solid #eee; }}
    .dot {{ width:10px; height:10px; border-radius:3px; background:var(--c); }}
    .tname {{ font-weight:700; font-size:16px; }}
    .tsub {{ margin-left:auto; font-size:12px; color:#71717a; }}
    .row {{ height:{ROW_H}px; display:flex; align-items:center; gap:10px; padding:0 16px; font-size:13px; border-top:1px solid #f4f4f5; }}
    .row:first-of-type {{ border-top:0; }}
    .tag {{ font-size:10px; font-weight:700; padding:2px 6px; border-radius:6px; width:34px; text-align:center; flex-shrink:0; }}
    .tag.ghost {{ background:transparent; }}
    .col {{ font-weight:600; width:140px; flex-shrink:0; }}
    .typ {{ color:{ACCENT}; font-size:12px; width:100px; flex-shrink:0; }}
    .note {{ color:#a1a1aa; font-size:11.5px; margin-left:auto; text-align:right; white-space:nowrap; }}
    svg {{ position:absolute; inset:0; }}
    .rel {{ font-size:13px; fill:{ACCENT}; font-weight:700; paint-order:stroke; stroke:#f7f7fb; stroke-width:6px; }}
    .header {{ position:absolute; left:60px; top:56px; width:480px; }}
    .notes {{ position:absolute; left:60px; top:640px; width:500px; background:#fff; border:1px solid #e6e6ea;
      border-radius:16px; padding:18px 20px; box-shadow: 0 12px 32px -18px rgba(24,24,27,.2); }}
    .notes h3 {{ font-size:13px; text-transform:uppercase; letter-spacing:.08em; color:#71717a; margin-bottom:10px; }}
    .nrow {{ display:flex; gap:12px; font-size:12.5px; line-height:1.45; padding:5px 0; }}
    .nkey {{ min-width:72px; font-weight:700; color:{ACCENT}; }}
    .nval {{ color:#3f3f46; }}
    .legend {{ position:absolute; right:60px; bottom:36px; display:flex; gap:14px; font-size:12px; color:#52525b; align-items:center; }}
    """
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="canvas" style="width:{W}px;height:{H}px">
  <svg width="{W}" height="{H}">
    <defs>
      <marker id="one" viewBox="0 0 12 12" refX="2" refY="6" markerWidth="12" markerHeight="12" orient="auto-start-reverse">
        <path d="M2 1 V11" stroke="{ACCENT}" stroke-width="2"/></marker>
      <marker id="many" viewBox="0 0 14 14" refX="13" refY="7" markerWidth="14" markerHeight="14" orient="auto">
        <path d="M13 7 L1 1 M13 7 L1 13 M13 7 L1 7" stroke="{ACCENT}" stroke-width="1.8" fill="none"/></marker>
    </defs>
    {svg}
  </svg>
  <div class="header"><h1>Knowledge Inbox · <span class="grad">Database design</span></h1>
    <p class="sub">PostgreSQL + pgvector · 5 tables · migration head <span class="mono">b7c1d2e3f4a5</span></p></div>
  {tables}
  <div class="notes"><h3>Design notes</h3>{notes_html}</div>
  <div class="legend">
    <span class="tag" style="{TAG_STYLE['PK']}">PK</span>primary key
    <span class="tag" style="{TAG_STYLE['FK']}">FK</span>foreign key
    <span class="tag" style="{TAG_STYLE['UQ']}">UQ</span>unique index
    <span class="tag" style="{TAG_STYLE['IDX']}">IDX</span>index
    <svg width="60" height="14" style="position:static"><path d="M4 7 H52" stroke="{ACCENT}" stroke-width="2"/>
      <path d="M4 2 V12" stroke="{ACCENT}" stroke-width="2"/><path d="M56 7 L46 2 M56 7 L46 12" stroke="{ACCENT}" stroke-width="1.8"/></svg>one-to-many
  </div>
</div></body></html>"""


# ───────────────────────────────────────────────────────────────────────────────
# 2. Sequence-style flow diagrams
# ───────────────────────────────────────────────────────────────────────────────

LANE_COLORS = ["#6d5dfc", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444"]


def build_flow(title, subtitle, lanes, steps, footer_notes, height):
    """
    lanes: [(name, detail)]
    steps: [(from_lane, to_lane, label, detail, kind)]   kind: call | return | self | note
    """
    W = 1660
    left, right = 150, W - 150
    lane_x = [left + i * (right - left) / (len(lanes) - 1) for i in range(len(lanes))]
    top = 210
    step_h = 66

    parts = []
    # lifelines
    for i, x in enumerate(lane_x):
        parts.append(f'<line x1="{x}" y1="{top - 20}" x2="{x}" y2="{height - 150}" stroke="{LANE_COLORS[i]}" '
                     f'stroke-opacity=".35" stroke-width="2" stroke-dasharray="6 6"/>')

    y = top + 20
    n = 0
    for frm, to, label, detail, kind in steps:
        if kind == "note":
            x1, x2 = lane_x[frm], lane_x[to]
            parts.append(
                f'<foreignObject x="{min(x1, x2) - 260}" y="{y - 22}" width="{abs(x2 - x1) + 520}" height="40">'
                f'<div class="note">{label}</div></foreignObject>'
            )
            y += step_h * 0.85
            continue
        n += 1
        color = LANE_COLORS[frm]
        badge = f'<circle cx="{{bx}}" cy="{y}" r="12" fill="{color}"/><text x="{{bx}}" y="{y + 4}" class="num">{n}</text>'
        if kind == "self":
            x = lane_x[frm]
            parts.append(f'<path d="M{x} {y - 10} h48 v22 h-46" fill="none" stroke="{color}" stroke-width="2" marker-end="url(#arrow)"/>')
            parts.append(badge.replace("{bx}", str(x - 24)))
            parts.append(f'<text x="{x + 60}" y="{y - 2}" class="lbl">{label}</text>')
            if detail:
                parts.append(f'<text x="{x + 60}" y="{y + 15}" class="det">{detail}</text>')
        else:
            x1, x2 = lane_x[frm], lane_x[to]
            dash = ' stroke-dasharray="6 5"' if kind == "return" else ""
            d = 1 if x2 > x1 else -1
            parts.append(f'<line x1="{x1 + d * 8}" y1="{y}" x2="{x2 - d * 10}" y2="{y}" stroke="{color}" '
                         f'stroke-width="2"{dash} marker-end="url(#arrow)"/>')
            parts.append(badge.replace("{bx}", str(x1 - d * 22)))
            mid = (x1 + x2) / 2
            parts.append(f'<text x="{mid}" y="{y - 10}" text-anchor="middle" class="lbl">{label}</text>')
            if detail:
                parts.append(f'<text x="{mid}" y="{y + 19}" text-anchor="middle" class="det">{detail}</text>')
        y += step_h

    heads = "".join(
        f'<div class="lane" style="left:{x - 125}px;--c:{LANE_COLORS[i]}"><b>{esc(name)}</b><span>{esc(det)}</span></div>'
        for i, ((name, det), x) in enumerate(zip(lanes, lane_x))
    )
    notes = "".join(f"<li>{t}</li>" for t in footer_notes)

    css = BASE_CSS + f"""
    svg {{ position:absolute; inset:0; }}
    .header {{ position:absolute; left:60px; top:40px; }}
    .lane {{ position:absolute; top:122px; width:250px; text-align:center; background:#fff; border:1px solid #e6e6ea;
      border-top:4px solid var(--c); border-radius:14px; padding:10px 8px; box-shadow:0 10px 26px -16px rgba(0,0,0,.25); }}
    .lane b {{ display:block; font-size:15px; }}
    .lane span {{ display:block; font-size:11.5px; color:#71717a; margin-top:2px; }}
    .lbl {{ font-size:13.5px; font-weight:600; fill:#18181b; paint-order:stroke; stroke:#f7f7fb; stroke-width:6px; }}
    .det {{ font-size:11.5px; fill:#71717a; font-family:"SF Mono",ui-monospace,Menlo,monospace; paint-order:stroke; stroke:#f7f7fb; stroke-width:6px; }}
    .num {{ font-size:12px; font-weight:700; fill:#fff; text-anchor:middle; }}
    .note {{ margin:0 auto; width:fit-content; white-space:nowrap; font-size:12px; color:#92400e; background:#fffbeb; border:1px solid #fde68a;
      border-radius:999px; padding:6px 14px; }}
    .foot {{ position:absolute; left:60px; right:60px; bottom:28px; background:#fff; border:1px solid #e6e6ea; border-radius:16px;
      padding:14px 22px; font-size:12.5px; color:#3f3f46; line-height:1.55; }}
    .foot ul {{ columns:2; column-gap:40px; padding-left:16px; }}
    .foot b {{ color:{ACCENT}; }}
    """
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="canvas" style="width:{W}px;height:{height}px">
  <svg width="{W}" height="{height}">
    <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
      <path d="M0 0 L10 5 L0 10 z" fill="#52525b"/></marker></defs>
    {''.join(parts)}
  </svg>
  <div class="header"><h1>Knowledge Inbox · <span class="grad">{esc(title)}</span></h1><p class="sub">{subtitle}</p></div>
  {heads}
  <div class="foot"><ul>{notes}</ul></div>
</div></body></html>"""


ASK_LANES = [
    ("Next.js UI", "components/Chat.tsx · /c/[sessionId]"),
    ("FastAPI route", "POST /api/v1/query/ask"),
    ("RAG + Guardrails", "rag_service · guardrail_service"),
    ("Model APIs", "LLM (chat) · embedding model"),
    ("PostgreSQL", "pgvector · conversations"),
]
ASK_STEPS = [
    (0, 1, "POST /query/ask  { question, session_id? }", "no session_id → new chat", "call"),
    (1, 4, "Load conversation + last 6 messages", "404 if session_id unknown", "call"),
    (1, 2, "answer_question(question, history)", "history: role + text only, old [S#] stripped", "call"),
    (2, 3, "Input rail · self_check_input  (LLM call 1)", "attack / harm? → Yes | No", "call"),
    (2, 2, "note", "", "note"),
    (2, 3, "Embed query = previous question + question", "embedding model · 768-d", "call"),
    (2, 4, "Vector search · ORDER BY cosine distance LIMIT top_k", "chunks ⨝ items → [S1]…[Sk]", "call"),
    (2, 3, "Generate answer  (LLM call 2)", "context [S#] + rules · history", "call"),
    (2, 3, "Output rail · self_check_output  (LLM call 3)", "leak / harm / injected instructions?", "call"),
    (2, 2, "Keep only cited, valid [S#] → citations", "", "self"),
    (2, 1, "{ answer, citations }", "", "return"),
    (1, 4, "Create conversation (if new) · save user + assistant msgs", "messages.citations = jsonb", "call"),
    (1, 0, "{ answer, citations, session_id }", "", "return"),
    (0, 0, "router.replace(/c/{session_id}) · refresh Recent chats", "", "self"),
]
# Fill the note text for the guardrail branch
ASK_STEPS[4] = (2, 2, "If blocked → canned refusal returned, nothing saved", "", "note")

ASK_NOTES = [
    "<b>3 LLM calls per question</b> — input rail, generation, output rail (+1 embedding call).",
    "<b>Rate limits</b>: rails retry 429/5xx with backoff (1.5s, 3s); still failing → <b>HTTP 429</b> “AI model is busy”.",
    "<b>Generation bypasses NeMo</b>: NeMo's Colang 1.0 generation drops system messages, so context/history go via <span class='mono'>llm_service</span>.",
    "<b>Citations</b>: only labels the answer actually cites are returned; stored as jsonb so sources survive reloads.",
    "<b>Reload</b>: <span class='mono'>GET /conversations/{id}/messages</span> restores text + sources; sidebar uses <span class='mono'>GET /conversations/</span>.",
    "<b>Follow-ups</b>: retrieval prepends the previous question so “does <i>it</i> support async?” stays on topic.",
]

INGEST_LANES = [
    ("Next.js UI", "/items/new · /items"),
    ("FastAPI routes", "/api/v1/items · /ingestion"),
    ("Background task", "ingestion_service"),
    ("External", "web page · embedding model"),
    ("PostgreSQL", "items · chunks"),
]
INGEST_STEPS = [
    (0, 1, "POST /items  { title, type, content | url }", "422 if content / url missing", "call"),
    (1, 4, "INSERT items  (status = pending)", "url items start with raw_content = ''", "call"),
    (1, 0, "201 { data: { id, status } }", "", "return"),
    (0, 1, "POST /ingestion/{id}   (auto-ingest toggle)", "409 if already processing", "call"),
    (1, 2, "BackgroundTasks.add_task(run_ingestion) → 202", "own DB session", "call"),
    (2, 4, "UPDATE items SET status = processing", "", "call"),
    (2, 3, "URL items: fetch page text → raw_content", "url_fetch_service", "call"),
    (2, 2, "Chunk: 500 tokens, 75 overlap (tiktoken)", "", "self"),
    (2, 3, "Embed all chunks in one batch", "768-d vectors", "call"),
    (2, 4, "DELETE old chunks · INSERT chunks + embeddings", "re-ingest replaces previous chunks", "call"),
    (2, 4, "status = completed   (on error: rollback, status = failed)", "", "call"),
    (0, 1, "GET /items every 3s while pending / processing", "Library page polling", "call"),
]
INGEST_NOTES = [
    "<b>Async by design</b>: the API returns 202 immediately; the work runs in a FastAPI background task.",
    "<b>Statuses</b>: pending → processing → completed | failed (shown as badges in the Library).",
    "<b>Re-ingest</b> deletes the item's chunks first, so it's idempotent.",
    "<b>Delete item</b> cascades to chunks (and ingestion_jobs) in the database.",
    "<b>Not yet used</b>: ingestion_jobs rows and items.content_hash (duplicate detection).",
    "<b>Search</b> later embeds the question with the same model and compares by cosine distance.",
]


# ───────────────────────────────────────────────────────────────────────────────
# 4. RAG pipeline — simple boxes
# ───────────────────────────────────────────────────────────────────────────────

# (label, x-slot)  — slots are columns; the Vector DB and Search share a column
SAVE_ROW = [("Note / URL", 0), ("Chunk", 1), ("Embed", 2), ("Vector DB", 3)]
ASK_ROW = [("Question", 0), ("Input guardrail", 1), ("Embed", 2), ("Search", 3), ("Add context", 4),
           ("LLM", 5), ("Output guardrail", 6), ("Answer + Sources", 7)]
GUARD_NOTES = {"Input guardrail": "blocks attacks & harmful questions", "Output guardrail": "blocks leaks & harmful answers"}


def build_rag() -> str:
    W, H = 1760, 600
    bw, bh, step, x0 = 170, 76, 210, 60
    y_save, y_ask = 170, 380

    def x(slot):
        return x0 + slot * step

    def boxes(row, y, highlight=()):
        out = []
        for label, slot in row:
            cls = "box guard" if label in GUARD_NOTES else ("box hl" if label in highlight else "box")
            out.append(f'<div class="{cls}" style="left:{x(slot)}px;top:{y}px;width:{bw}px;height:{bh}px">{esc(label)}</div>')
        return "".join(out)

    def arrows(row, y):
        out = []
        for (_, a), (_, b) in zip(row, row[1:]):
            out.append(f'<line x1="{x(a) + bw + 6}" y1="{y + bh / 2}" x2="{x(b) - 8}" y2="{y + bh / 2}" class="ar"/>')
        return "".join(out)

    db_cx = x(3) + bw / 2
    svg = (arrows(SAVE_ROW, y_save) + arrows(ASK_ROW, y_ask)
           + f'<line x1="{db_cx - 18}" y1="{y_ask - 8}" x2="{db_cx - 18}" y2="{y_save + bh + 10}" class="ar"/>'
           + f'<line x1="{db_cx + 18}" y1="{y_save + bh + 8}" x2="{db_cx + 18}" y2="{y_ask - 10}" class="ar"/>'
           + f'<text x="{db_cx + 34}" y="{(y_save + bh + y_ask) / 2 + 5}" class="lab">top 5 matching chunks</text>')

    css = BASE_CSS + f"""
    svg {{ position:absolute; inset:0; }}
    .header {{ position:absolute; left:{x0}px; top:40px; }}
    .row {{ position:absolute; left:{x0}px; font-size:15px; font-weight:700; color:#3f3f46; }}
    .row span {{ font-weight:400; color:#a1a1aa; margin-left:8px; }}
    .box {{ position:absolute; display:flex; align-items:center; justify-content:center; text-align:center;
      background:#fff; border:2px solid #d4d4d8; border-radius:14px; font-size:16px; font-weight:600; padding:0 10px; }}
    .box.hl {{ border-color:{ACCENT}; color:{ACCENT}; background:#f5f3ff; }}
    .box.guard {{ border-color:#f59e0b; color:#b45309; background:#fffbeb; }}
    .gnote {{ position:absolute; width:{bw}px; text-align:center; font-size:13px; color:#b45309; line-height:1.35; }}
    .ar {{ stroke:#71717a; stroke-width:2; marker-end:url(#arrow); }}
    .lab {{ font-size:14px; fill:#71717a; }}
    """
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="canvas" style="width:{W}px;height:{H}px">
  <svg width="{W}" height="{H}"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M0 0 L10 5 L0 10 z" fill="#71717a"/></marker></defs>{svg}</svg>
  <div class="header"><h1>RAG <span class="grad">pipeline</span></h1>
    <p class="sub">Find the right pieces of your notes, then let the LLM answer from them — with guardrails on the way in and out.</p></div>
  <div class="row" style="top:{y_save - 34}px">1. Save<span>when you add a note or URL</span></div>
  <div class="row" style="top:{y_ask - 34}px">2. Ask<span>when you ask a question</span></div>
  {''.join(f'<div class="gnote" style="left:{x(slot)}px;top:{y_ask + bh + 12}px">{esc(GUARD_NOTES[label])}</div>' for label, slot in ASK_ROW if label in GUARD_NOTES)}
  {boxes(SAVE_ROW, y_save, highlight=("Vector DB",))}
  {boxes(ASK_ROW, y_ask, highlight=("LLM",))}
</div></body></html>"""


# ───────────────────────────────────────────────────────────────────────────────
# Render
# ───────────────────────────────────────────────────────────────────────────────

def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c and Path(c).exists():
            return c
    raise SystemExit("Google Chrome not found — open the .html files in a browser instead.")


def render(html_path: Path, png_path: Path, width: int, height: int, chrome: str):
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             f"--user-data-dir={profile}", f"--window-size={width},{height}",
             "--force-device-scale-factor=2", f"--screenshot={png_path}", html_path.as_uri()],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def main():
    diagrams = [
        ("database-design", build_er(), 1660, 1010),
        ("ask-flow", build_flow("Ask flow (RAG + chat sessions)",
                                "What happens when you send a question — from the chat window to the database and back",
                                ASK_LANES, ASK_STEPS, ASK_NOTES, 1340), 1660, 1340),
        ("rag-pipeline", build_rag(), 1760, 600),
        ("ingestion-flow", build_flow("Ingestion flow",
                                      "How a saved note or URL becomes searchable chunks",
                                      INGEST_LANES, INGEST_STEPS, INGEST_NOTES, 1180), 1660, 1180),
    ]
    chrome = find_chrome()
    for name, doc, w, h in diagrams:
        html_path = HERE / f"{name}.html"
        html_path.write_text(doc, encoding="utf-8")
        png_path = DOCS / f"{name}.png"
        render(html_path, png_path, w, h, chrome)
        print(f"wrote {png_path.relative_to(DOCS.parent)}")


if __name__ == "__main__":
    main()
