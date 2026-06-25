"""
Simple in-memory job store for video generation. Video rendering takes
real wall-clock time (multiple sequential TTS calls + frame rendering +
ffmpeg encode), so it runs as a background task while the frontend polls
job status rather than holding one HTTP request open the whole time.
"""
import uuid
from dataclasses import dataclass, field
from typing import Literal

JobStatus = Literal["pending", "running", "done", "error"]


@dataclass
class VideoJob:
    id: str
    status: JobStatus = "pending"
    stage: str = "queued"
    progress: float = 0.0
    output_path: str | None = None
    error: str | None = None


_JOBS: dict[str, VideoJob] = {}


def create_job() -> VideoJob:
    job = VideoJob(id=str(uuid.uuid4()))
    _JOBS[job.id] = job
    return job


def get_job(job_id: str) -> VideoJob | None:
    return _JOBS.get(job_id)


def update_job(job_id: str, **kwargs):
    job = _JOBS.get(job_id)
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
