import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.store import get_project, get_section
from app.services.script_generator import generate_script
from app.services.video.renderer import render_explainer_video, VideoRenderError
from app.services.video.jobs import create_job, get_job, update_job
from app.services.ai_router import ProviderError
from app.services.tts import VOICE_OPTIONS   # this is now a list, not a dict

router = APIRouter(prefix="/api/video", tags=["video"])


class VideoRequest(BaseModel):
    project_id: str
    section_id: str
    voice: str = "narrator"


@router.get("/voices")
async def list_voices():
    # VOICE_OPTIONS is a plain list — no .keys() needed
    return {"voices": VOICE_OPTIONS}


@router.post("/generate")
async def start_video_generation(req: VideoRequest):
    project = get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    section = get_section(req.project_id, req.section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    if req.voice not in VOICE_OPTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown voice '{req.voice}'. Valid options: {VOICE_OPTIONS}",
        )

    job = create_job()

    async def run():
        update_job(job.id, status="running", stage="writing script", progress=0.02)
        try:
            code_excerpt = section.code_blocks[0] if section.code_blocks else ""

            beats = await generate_script(
                title=section.title,
                content=section.content,
                concepts=sorted(section.concepts),
                code_excerpt=code_excerpt,
            )

            def progress_cb(stage: str, pct: float):
                update_job(job.id, stage=stage, progress=pct)

            output_path = await render_explainer_video(
                title=section.title,
                beats=beats,
                related_concepts=sorted(section.concepts) or ["MindFlow"],
                code_excerpt=code_excerpt,
                voice=req.voice,
                job_id=job.id,
                progress_cb=progress_cb,
            )
            update_job(job.id, status="done", stage="done", progress=1.0, output_path=output_path)

        except (VideoRenderError, ProviderError) as e:
            update_job(job.id, status="error", error=str(e))

        except BaseException as e:
            # Catch absolutely everything — asyncio.CancelledError, SystemExit, etc.
            # Without this, any unexpected exception silently leaves the job at
            # status="running" forever and the frontend polls endlessly.
            update_job(job.id, status="error", error=f"Unexpected error: {type(e).__name__}: {e}")
            raise  # re-raise so the event loop still knows about it

    # Use asyncio.create_task instead of BackgroundTasks — more reliable for
    # long-running async work that itself awaits multiple things (TTS calls,
    # subprocess ffmpeg, etc.). BackgroundTasks can behave unexpectedly when
    # the async task tree gets deep.
    asyncio.create_task(run())

    return {"job_id": job.id}


@router.get("/status/{job_id}")
async def video_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "status": job.status,
        "stage": job.stage,
        "progress": job.progress,
        "error": job.error,
        "ready": job.status == "done",
    }


@router.get("/download/{job_id}")
async def download_video(job_id: str):
    job = get_job(job_id)
    if not job or job.status != "done" or not job.output_path:
        raise HTTPException(status_code=404, detail="Video not ready.")
    return FileResponse(
        job.output_path,
        media_type="video/mp4",
        filename=f"mindflow-{job_id}.mp4",
    )
