"""Shared task formatter — categorize, clean, cap, render.

Used by morning_push.py (focus), telegram_bot.py (evening recap + /tasks).
Single source of truth for: bucket assignment, Markdown cleanup, capping, layout.

Buckets (German labels with emoji):
  🏢 Arbeit      — HoldeinePlakette/HDP job, consulting, Spring Week, career prep
  📱 Apps        — HorseFinder, MyWardrobe, Market Tools, Cognify, infra/tooling
  🏠 Persönlich  — TUM, courses, personal finance/learning
"""

from __future__ import annotations

import re

ARBEIT = "🏢 Arbeit"
APPS = "📱 Apps"
PERSOENLICH = "🏠 Persönlich"
BUCKETS = [ARBEIT, APPS, PERSOENLICH]
_DEFAULT_BUCKET = APPS

# Keyword → bucket. Checked against "<subsection> <task text>" (lowercased).
# Arbeit is checked first so career-prep keywords win over generic ones.
_KEYWORDS: list[tuple[str, list[str]]] = [
    (ARBEIT, [
        "bewerbung", "cover letter", "case prep", "case in point", "preplounge",
        "bcg", "mckinsey", "spring week", "rothschild", "financial modeling",
        "biws", "consulting", "investment banking", "hubspot", "holdeineplakette",
        "hdp", "claims", "prüf", "regionalleiter", "okr", "personio",
    ]),
    (PERSOENLICH, [
        "tum", "mmt", "fcff", "dcf", "lbo", "kurs", "course", "portfolio-tracking",
        "aptitude", "supervisor",
    ]),
    (APPS, [
        "horsefinder", "nennung", "mywardrobe", "wardrobe", "market tools",
        "cognify", "scraper", "stripe", "koyfin", "ghostfolio", "lovable",
        "domain", "plausible", "analytics", "n8n", "gbrain", "hermes",
        "watchlist", "portfolio.tsx", "impressum", "datenschutz", "seo",
    ]),
]

# Section heading keyword → bucket (fallback when no keyword in the task matched).
_SECTIONS: list[tuple[str, str]] = [
    ("beruf", ARBEIT), ("hdp", ARBEIT), ("claims", ARBEIT), ("career", ARBEIT),
    ("consulting", ARBEIT), ("investment banking", ARBEIT), ("ausbildung", ARBEIT),
    ("tum", PERSOENLICH), ("knowledge & finance", PERSOENLICH),
    ("horsefinder", APPS), ("mywardrobe", APPS), ("market tools", APPS),
    ("cognify", APPS), ("projekte", APPS), ("system", APPS),
    ("infrastruktur", APPS), ("langfristig", APPS), ("dringend", APPS),
]


def bucket_for(label: str, text: str = "") -> str:
    """Return the bucket for a task given its section/subsection label and text."""
    hay = f"{label} {text}".lower()
    for bucket, words in _KEYWORDS:
        if any(w in hay for w in words):
            return bucket
    low_label = label.lower()
    for needle, bucket in _SECTIONS:
        if needle in low_label:
            return bucket
    return _DEFAULT_BUCKET


def clean_task(raw: str) -> str:
    """Strip checkbox, [Label] prefix, trailing '← …', and raw Markdown (** / `)."""
    s = raw.strip()
    s = re.sub(r"^- \[[ xX]\]\s*", "", s)          # checkbox
    s = re.sub(r"^\[[^\]]+\]\s*", "", s)            # [Label] prefix
    if "←" in s:
        s = s[: s.index("←")]
    s = s.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", s).strip()


def parse_open_tasks(md: str) -> list[tuple[str, str]]:
    """Parse OPEN_TASKS.md into [(bucket, clean_text)] for every '- [ ]' item.

    Tracks ## section and ### subsection so each task is bucketed by its context.
    """
    items: list[tuple[str, str]] = []
    seen: set[str] = set()
    section = ""
    subsection = ""
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip()
            subsection = ""
        elif stripped.startswith("### "):
            subsection = stripped[4:].strip()
        elif stripped.startswith("- [ ]"):
            text = clean_task(stripped)
            if not text:
                continue
            key = text.lower()
            if key in seen:          # same task listed under two sections (e.g. 🔴 + project)
                continue
            seen.add(key)
            label = subsection or section
            items.append((bucket_for(label, text), text))
    return items


def group_and_cap(
    items: list[tuple[str, str]], cap_per_bucket: int = 4
) -> dict[str, list[str]]:
    """Group (bucket, text) pairs into ordered buckets (no cap applied to data)."""
    groups: dict[str, list[str]] = {b: [] for b in BUCKETS}
    for bucket, text in items:
        groups.setdefault(bucket, []).append(text)
    return groups


def render_groups(
    items: list[tuple[str, str]], cap_per_bucket: int = 4
) -> str:
    """Render categorized tasks as clean Markdown-v1 text, capped per bucket."""
    groups = group_and_cap(items)
    out: list[str] = []
    for bucket in BUCKETS:
        tasks = groups.get(bucket, [])
        if not tasks:
            continue
        out.append(f"*{bucket}*")
        for t in tasks[:cap_per_bucket]:
            out.append(f"• {t}")
        if len(tasks) > cap_per_bucket:
            out.append(f"_(+{len(tasks) - cap_per_bucket} weitere)_")
        out.append("")
    return "\n".join(out).strip()


# ---------------------------------------------------------------------------
# MarkdownV2 rendering (Telegram) — expandable blockquote for overflow
# ---------------------------------------------------------------------------

# Emoji + label split so the emoji sits OUTSIDE the bold marker (Telegram breaks
# bold when an emoji immediately follows the '*').
BUCKET_META: dict[str, tuple[str, str]] = {
    ARBEIT: ("🏢", "Arbeit"),
    APPS: ("📱", "Apps"),
    PERSOENLICH: ("🏠", "Persönlich"),
}

_MD2_SPECIAL = set("_*[]()~`>#+-=|{}.!\\")


def esc_v2(text: str) -> str:
    """Escape arbitrary text for Telegram MarkdownV2."""
    return "".join("\\" + c if c in _MD2_SPECIAL else c for c in text)


def bold_v2(text: str) -> str:
    """Bold an escaped plain string (Markdown V2)."""
    return f"*{esc_v2(text)}*"


def header_v2(emoji: str, label: str) -> str:
    """Section header: emoji outside the bold so Telegram renders it cleanly."""
    return f"{emoji} *{esc_v2(label)}*"


def expandable_v2(lead: str, lines: list[str]) -> str:
    """Telegram MarkdownV2 expandable blockquote.

    `lead` is the visible peek line; `lines` are collapsed until tapped.
    First line prefixed '**>', the rest '>', last line ends with '||'.
    """
    body = [lead, *lines]
    quoted = [("**>" if i == 0 else ">") + esc_v2(line) for i, line in enumerate(body)]
    quoted[-1] += "||"
    return "\n".join(quoted)


def render_groups_v2(items: list[tuple[str, str]], cap_per_bucket: int = 3) -> str:
    """Categorized tasks as MarkdownV2: capped bullets + expandable overflow."""
    groups = group_and_cap(items)
    blocks: list[str] = []
    for bucket in BUCKETS:
        tasks = groups.get(bucket, [])
        if not tasks:
            continue
        emoji, label = BUCKET_META[bucket]
        lines = [header_v2(emoji, label)]
        lines += [f"• {esc_v2(t)}" for t in tasks[:cap_per_bucket]]
        overflow = tasks[cap_per_bucket:]
        if overflow:
            lines.append(expandable_v2(f"+{len(overflow)} weitere", [f"• {t}" for t in overflow]))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
