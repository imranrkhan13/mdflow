"""
Simple in-memory store, keyed by project id, holding the parsed sections
and built graph for the current session. Matches the spec's "SQLite
initially, easy migration to Postgres later" note — for this vertical
slice, in-memory is enough and keeps the slice fast to run.
"""
import uuid
from app.parsers.markdown_parser import Section

_PROJECTS: dict[str, dict] = {}

# AI answers, keyed by (project_id, scope, key). Same section + mode asked
# twice (re-clicking a node, switching tabs and back) returns instantly
# instead of paying for another provider round-trip.
_ANSWERS: dict[tuple[str, str, str], dict] = {}


def get_cached_answer(project_id: str, scope: str, key: str) -> dict | None:
    return _ANSWERS.get((project_id, scope, key))


def set_cached_answer(project_id: str, scope: str, key: str, value: dict) -> None:
    _ANSWERS[(project_id, scope, key)] = value


def create_project(filename: str, sections: list[Section], graph: dict) -> str:
    project_id = str(uuid.uuid4())
    _PROJECTS[project_id] = {
        "id": project_id,
        "filename": filename,
        "sections": {s.id: s for s in sections},
        "graph": graph,
    }
    return project_id


def get_project(project_id: str) -> dict | None:
    return _PROJECTS.get(project_id)


def get_section(project_id: str, section_id: str) -> Section | None:
    proj = _PROJECTS.get(project_id)
    if not proj:
        return None
    return proj["sections"].get(section_id)
