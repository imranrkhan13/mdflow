from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.repo_importer import import_repo, RepoImportError
from app.services.store import create_project

router = APIRouter(prefix="/api/repo", tags=["repo"])


class RepoImportRequest(BaseModel):
    url: str


@router.post("/import")
async def import_repository(req: RepoImportRequest):
    try:
        name, sections, graph = await import_repo(req.url)
    except RepoImportError as e:
        raise HTTPException(status_code=400, detail=str(e))

    project_id = create_project(name, sections, graph)
    return {
        "project_id": project_id,
        "filename": name,
        "graph": graph,
        "section_count": len(sections),
        "kind": "repo",
    }
