"""
Parses a markdown document (e.g. README.md) into a structured outline:
heading hierarchy, code blocks attached to their nearest heading, and a
naive keyword scan for system-concept terms (API, database, auth, etc.)
so the graph builder has something to connect.

This is intentionally not a full semantic parser — it gives the AI router
a clean structured skeleton, and the AI fills in the actual explanations
per-node on demand (lazy, not pre-computed for every node up front).
"""
import re
from dataclasses import dataclass, field

from markdown_it import MarkdownIt

CONCEPT_KEYWORDS = {
    "api": "API",
    "database": "Database",
    "db": "Database",
    "auth": "Authentication",
    "authentication": "Authentication",
    "worker": "Workers",
    "queue": "Queue",
    "cache": "Cache",
    "redis": "Cache",
    "storage": "Storage",
    "frontend": "Frontend",
    "backend": "Backend",
    "service": "Services",
    "controller": "Controllers",
    "repository": "Repositories",
    "model": "Models",
    "route": "Routes",
    "endpoint": "Routes",
    "webhook": "Events",
    "event": "Events",
    "llm": "LLMs",
    "vector": "Vector Databases",
    "docker": "Infrastructure",
    "kubernetes": "Infrastructure",
    "deploy": "Infrastructure",
}


@dataclass
class Section:
    id: str
    title: str
    level: int
    content: str = ""
    code_blocks: list[str] = field(default_factory=list)
    concepts: set[str] = field(default_factory=set)
    parent_id: str | None = None


def _slugify(text: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"
    slug = base
    i = 2
    while slug in used:
        slug = f"{base}-{i}"
        i += 1
    used.add(slug)
    return slug


def _detect_concepts(text: str) -> set[str]:
    found = set()
    lowered = text.lower()
    for kw, label in CONCEPT_KEYWORDS.items():
        if re.search(rf"\b{re.escape(kw)}\b", lowered):
            found.add(label)
    return found


def parse_markdown(raw: str) -> list[Section]:
    md = MarkdownIt()
    tokens = md.parse(raw)

    sections: list[Section] = []
    used_slugs: set[str] = set()
    # stack of (level, section_id) for tracking parent headings
    stack: list[tuple[int, str]] = []

    current: Section | None = None
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok.type == "heading_open":
            level = int(tok.tag[1])  # h1 -> 1, h2 -> 2, etc.
            i += 1
            inline_tok = tokens[i]
            title = inline_tok.content.strip()
            slug = _slugify(title, used_slugs)

            # pop stack until we find a shallower level -> that's the parent
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent_id = stack[-1][1] if stack else None

            current = Section(id=slug, title=title, level=level, parent_id=parent_id)
            sections.append(current)
            stack.append((level, slug))

        elif tok.type == "fence" and current is not None:
            current.code_blocks.append(tok.content.strip())
            current.concepts |= _detect_concepts(tok.content)

        elif tok.type == "inline" and current is not None and tok.content:
            current.content += tok.content + "\n"
            current.concepts |= _detect_concepts(tok.content)

        i += 1

    # If the doc has no headings at all, treat the whole thing as one section
    if not sections:
        sections.append(
            Section(
                id="root",
                title="Document",
                level=1,
                content=raw[:4000],
                concepts=_detect_concepts(raw),
            )
        )

    return sections
