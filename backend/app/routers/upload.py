from fastapi import APIRouter, UploadFile, File, HTTPException

from app.parsers.markdown_parser import parse_markdown
from app.services.graph_builder import build_graph
from app.services.store import create_project

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt"}


@router.post("")
async def upload_document(file: UploadFile = File(...)):
    name = file.filename or "untitled.md"
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. This vertical slice handles "
                "markdown (.md, .markdown, .txt) only — PDF/DOCX/source parsing "
                "are planned but not yet wired up."
            ),
        )

    raw_bytes = await file.read()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 text.")

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="File is empty.")

    sections = parse_markdown(raw_text)
    graph = build_graph(sections)
    project_id = create_project(name, sections, graph)

    return {
        "project_id": project_id,
        "filename": name,
        "graph": graph,
        "section_count": len(sections),
    }
