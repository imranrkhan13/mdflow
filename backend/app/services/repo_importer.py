"""
GitHub repo import: fetch a public repo's file tree, read each source file,
extract its imports/requires, resolve them to other files in the repo, and
build a file-level dependency graph.

This is deliberately best-effort and bounded:
  - only public repos, resolved through api.github.com / raw.githubusercontent.com
  - a curated set of text/code extensions (binaries, lockfiles, vendored dirs skipped)
  - a hard cap on file count and per-file bytes so a huge repo can't blow up memory

Output reuses the same {nodes, edges} React Flow shape the markdown slice
already produces, so the existing canvas/panel code works unchanged. Each
node carries `kind: "file"` plus its `path`/`lang` so the UI can render a
file chip instead of an h1/h2 chip.
"""
import asyncio
import posixpath
import re
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.parsers.markdown_parser import Section

# ── Limits ───────────────────────────────────────────────────────────────────
MAX_FILES = 500
MAX_FILE_BYTES = 120_000          # per file, fetched
MAX_CONTENT_KEPT = 6_000          # per file, stored for the explain panel
FETCH_CONCURRENCY = 12

# Directories that are never interesting for a dependency graph
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", ".nuxt",
    "vendor", "venv", ".venv", "env", "__pycache__", ".mypy_cache",
    ".pytest_cache", "coverage", ".idea", ".vscode", "target", "bin", "obj",
    "site-packages", ".cache", ".turbo",
}

# extension -> language family (drives which import parser runs)
LANG_BY_EXT = {
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js",
    ".ts": "ts", ".tsx": "ts",
    ".py": "py",
}
# extra text files worth showing as nodes, but with no import parsing
OTHER_TEXT_EXT = {
    ".json", ".yaml", ".yml", ".toml", ".md", ".markdown", ".txt",
    ".css", ".scss", ".html", ".sql", ".sh", ".cfg", ".ini",
}


class RepoImportError(Exception):
    pass


# ── URL parsing ──────────────────────────────────────────────────────────────

_SEG_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def parse_github_url(url: str) -> tuple[str, str, str | None]:
    """Return (owner, repo, branch_or_None). Raises RepoImportError."""
    url = (url or "").strip()
    if not url:
        raise RepoImportError("No URL provided.")
    if not re.match(r"^https?://", url):
        url = "https://" + url
    p = urlparse(url)
    host = (p.netloc or "").lower()
    if host not in ("github.com", "www.github.com"):
        raise RepoImportError("Only github.com URLs are supported right now.")
    parts = [s for s in p.path.split("/") if s]
    if len(parts) < 2:
        raise RepoImportError("URL must look like https://github.com/owner/repo")
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not _SEG_RE.match(owner) or not _SEG_RE.match(repo):
        raise RepoImportError("Invalid owner/repo in URL.")
    branch = None
    if len(parts) >= 4 and parts[2] in ("tree", "blob"):
        branch = parts[3]
    return owner, repo, branch


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "mindflow-importer"}
    if settings.github_token:
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


# ── Import statement extraction ──────────────────────────────────────────────

_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[^'"]*?\s+from\s+)?|export\s+[^'"]*?\s+from\s+|require\s*\(\s*|import\s*\(\s*)['"]([^'"]+)['"]"""
)
_PY_FROM_RE = re.compile(r"^\s*from\s+([.\w]+)\s+import\s+(.+)$", re.MULTILINE)
_PY_IMPORT_RE = re.compile(r"^\s*import\s+([.\w]+(?:\s*,\s*[.\w]+)*)", re.MULTILINE)


def _extract_specifiers(text: str, lang: str) -> list[str]:
    specs: list[str] = []
    if lang in ("js", "ts"):
        specs += _JS_IMPORT_RE.findall(text)
    elif lang == "py":
        for mod, names in _PY_FROM_RE.findall(text):
            specs.append(mod)
            if mod.strip(".") == "":  # from . import a, b
                for n in names.split(","):
                    n = n.strip().split(" as ")[0].strip()
                    if n:
                        specs.append(f"{mod}{n}")
        for mods in _PY_IMPORT_RE.findall(text):
            for m in mods.split(","):
                m = m.strip().split(" as ")[0].strip()
                if m:
                    specs.append(m)
    return specs


# ── Resolution: specifier -> file path within the repo ───────────────────────

_JS_CANDIDATES = ["", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
                  "/index.js", "/index.jsx", "/index.ts", "/index.tsx"]


def _resolve_js(spec: str, from_path: str, known: set[str]) -> str | None:
    if not spec.startswith("."):
        return None  # package import -> external, skip
    base = posixpath.normpath(posixpath.join(posixpath.dirname(from_path), spec))
    for suf in _JS_CANDIDATES:
        cand = base + suf
        if cand in known:
            return cand
    return None


def _resolve_py(spec: str, from_path: str, known: set[str]) -> str | None:
    # relative import: leading dots mean "go up N package levels"
    if spec.startswith("."):
        dots = len(spec) - len(spec.lstrip("."))
        rest = spec[dots:]
        pkg = posixpath.dirname(from_path).split("/")
        # one leading dot = current package; each extra dot goes up one level
        up = dots - 1
        if up > 0:
            pkg = pkg[:-up] if up <= len(pkg) else []
        parts = ([p for p in pkg if p] + rest.split(".")) if rest else pkg
        rel = "/".join([p for p in parts if p])
        for cand in (f"{rel}.py", f"{rel}/__init__.py"):
            if cand in known:
                return cand
        return None

    # absolute import: the module root may be a subdir (e.g. backend/), not
    # the repo root, so first try direct, then a unique path-segment suffix.
    rel = spec.replace(".", "/")
    for cand in (f"{rel}.py", f"{rel}/__init__.py"):
        if cand in known:
            return cand
    tails = (f"/{rel}.py", f"/{rel}/__init__.py")
    matches = [p for p in known if p.endswith(tails)]
    return matches[0] if len(matches) == 1 else None


def _resolve(spec: str, from_path: str, lang: str, known: set[str]) -> str | None:
    if lang in ("js", "ts"):
        return _resolve_js(spec, from_path, known)
    if lang == "py":
        return _resolve_py(spec, from_path, known)
    return None


# ── GitHub fetch ─────────────────────────────────────────────────────────────

async def _fetch_tree(client: httpx.AsyncClient, owner: str, repo: str, branch: str | None) -> tuple[str, list[dict]]:
    resolved = branch
    if not resolved:
        r = await client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=_headers())
        if r.status_code == 404:
            raise RepoImportError(f"Repo {owner}/{repo} not found (or is private).")
        if r.status_code != 200:
            raise RepoImportError(f"GitHub API error {r.status_code} fetching repo metadata.")
        resolved = r.json().get("default_branch") or "main"

    r = await client.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{resolved}",
        params={"recursive": "1"}, headers=_headers(),
    )
    if r.status_code != 200:
        raise RepoImportError(f"GitHub API error {r.status_code} fetching tree for branch '{resolved}'.")
    tree = r.json().get("tree", [])
    return resolved, tree


def _keep(path: str) -> bool:
    parts = path.split("/")
    if any(p in SKIP_DIRS for p in parts[:-1]):
        return False
    ext = "." + parts[-1].rsplit(".", 1)[-1].lower() if "." in parts[-1] else ""
    return ext in LANG_BY_EXT or ext in OTHER_TEXT_EXT


async def _fetch_file(client: httpx.AsyncClient, sem: asyncio.Semaphore,
                      owner: str, repo: str, branch: str, path: str) -> tuple[str, str] | None:
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    async with sem:
        try:
            r = await client.get(url, timeout=20)
        except httpx.RequestError:
            return None
    if r.status_code != 200:
        return None
    text = r.text[:MAX_FILE_BYTES]
    return path, text


# ── Layout ───────────────────────────────────────────────────────────────────

def _layout(paths: list[str]) -> dict[str, dict]:
    """x by directory depth, y by order within the directory. Deterministic."""
    depth_count: dict[int, int] = {}
    pos: dict[str, dict] = {}
    for path in sorted(paths):
        depth = path.count("/")
        row = depth_count.get(depth, 0)
        depth_count[depth] = row + 1
        pos[path] = {"x": depth * 300, "y": row * 120}
    return pos


def _lang_label(ext: str) -> str:
    return {
        ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
        ".ts": "TypeScript", ".tsx": "TypeScript", ".mjs": "JavaScript",
        ".cjs": "JavaScript", ".json": "JSON", ".md": "Markdown",
        ".css": "CSS", ".html": "HTML", ".yaml": "YAML", ".yml": "YAML",
        ".toml": "TOML", ".sql": "SQL", ".sh": "Shell",
    }.get(ext, ext.lstrip(".").upper() or "Text")


# ── Public entry point ───────────────────────────────────────────────────────

async def import_repo(url: str) -> tuple[str, list[Section], dict]:
    """Fetch + parse a GitHub repo. Returns (name, sections, react_flow_graph)."""
    owner, repo, branch = parse_github_url(url)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        branch, tree = await _fetch_tree(client, owner, repo, branch)

        blobs = [e for e in tree if e.get("type") == "blob" and _keep(e["path"])]
        # smallest-first isn't meaningful; keep tree order, cap count
        blobs = blobs[:MAX_FILES]

        sem = asyncio.Semaphore(FETCH_CONCURRENCY)
        results = await asyncio.gather(
            *[_fetch_file(client, sem, owner, repo, branch, e["path"]) for e in blobs]
        )

    files: dict[str, str] = {p: t for r in results if r for p, t in [r]}
    if not files:
        raise RepoImportError("No source files found (repo may be empty or all-binary).")

    known = set(files.keys())
    positions = _layout(list(files.keys()))

    # ── Build sections (reused by the explain panel) + nodes ─────────────────
    sections: list[Section] = []
    nodes: list[dict] = []
    for path, text in files.items():
        parts = path.split("/")
        ext = "." + parts[-1].rsplit(".", 1)[-1].lower() if "." in parts[-1] else ""
        lang = LANG_BY_EXT.get(ext)
        section = Section(
            id=path,
            title=parts[-1],
            level=1,
            content=text[:MAX_CONTENT_KEPT],
            concepts={_lang_label(ext)},
        )
        sections.append(section)
        nodes.append({
            "id": path,
            "type": "conceptNode",
            "position": positions.get(path, {"x": 0, "y": 0}),
            "data": {
                "title": parts[-1],
                "path": path,
                "lang": _lang_label(ext),
                "level": 1,
                "preview": (text[:140].replace("\n", " ").strip()),
                "hasCode": bool(lang),
                "concepts": [_lang_label(ext)],
                "kind": "file",
            },
        })

    # ── Import edges ─────────────────────────────────────────────────────────
    edges: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path, text in files.items():
        ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        lang = LANG_BY_EXT.get(ext)
        if not lang:
            continue
        for spec in _extract_specifiers(text, lang):
            target = _resolve(spec, path, lang, known)
            if not target or target == path:
                continue
            key = (path, target)
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "id": f"{path}->{target}",
                "source": path,
                "target": target,
                "animated": False,
                "data": {"kind": "import", "via": spec},
            })

    graph = {"nodes": nodes, "edges": edges}
    return f"{owner}/{repo}", sections, graph
