"""
Orchestrates: script beats → per-beat TTS audio → synced frame sequences
→ concatenated audio → ffmpeg mux into MP4.

Audio files from edge-tts come as MP3; from Gemini as WAV. Both are
handled — ffmpeg's concat demuxer accepts both formats natively.
Duration measurement uses mutagen (pure Python, no ffmpeg needed at
this step).
"""
import os
import shutil
import subprocess
import uuid
import wave

from app.services import tts
from app.services.video.frame_renderer import VISUAL_RENDERERS, FPS

OUTPUT_DIR = os.path.join("/tmp", "mindflow_videos")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class VideoRenderError(Exception):
    pass


def _audio_duration_seconds(path: str) -> float:
    """
    Returns duration in seconds for both MP3 and WAV files.
    Uses mutagen for MP3 (pure Python, no ffmpeg), wave stdlib for WAV.
    """
    if path.endswith(".wav"):
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())

    # MP3 — use mutagen (pure Python, always available)
    try:
        from mutagen.mp3 import MP3
        audio = MP3(path)
        return audio.info.length
    except Exception as e:
        raise VideoRenderError(f"Could not read audio duration from {path}: {e}")


def _render_beat_frames(
    beat: dict, title: str, related: list[str],
    duration: float, frame_dir: str, start_index: int,
    beat_idx: int = 0, total_beats: int = 1,
) -> int:
    renderer = VISUAL_RENDERERS.get(beat["visual"], VISUAL_RENDERERS["highlight_node"])
    n_frames = max(1, int(duration * FPS))
    narration = beat.get("narration", "")

    for i in range(n_frames):
        t = i / FPS

        # Build kwargs supported by the renderer
        kwargs = dict(
            narration=narration,
            duration=duration,
            beat_idx=beat_idx,
            total_beats=total_beats,
        )

        if beat["visual"] == "title":
            frame = renderer(t, title, **kwargs)
        elif beat["visual"] == "summary":
            frame = renderer(t, title, **kwargs)
        elif beat["visual"] == "show_code":
            frame = renderer(t, title, beat.get("code", ""), beat.get("emphasis", ""), **kwargs)
        elif beat["visual"] == "concepts":
            frame = renderer(t, title, related, beat.get("emphasis", ""), **kwargs)
        else:
            frame = renderer(t, title, related, beat.get("emphasis", ""), **kwargs)

        frame.save(os.path.join(frame_dir, f"frame_{start_index + i:06d}.png"))

    return n_frames


async def render_explainer_video(
    title: str,
    beats: list[dict],
    related_concepts: list[str],
    code_excerpt: str = "",
    voice: str = "narrator",
    job_id: str | None = None,
    progress_cb=None,
) -> str:
    job_id = job_id or str(uuid.uuid4())
    work_dir  = os.path.join(OUTPUT_DIR, job_id)
    frame_dir = os.path.join(work_dir, "frames")
    audio_dir = os.path.join(work_dir, "audio")
    os.makedirs(frame_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    def report(stage: str, pct: float):
        if progress_cb:
            progress_cb(stage, pct)

    # 1. Generate per-beat audio ────────────────────────────────────────────
    beat_audio_paths = []
    for i, beat in enumerate(beats):
        if not beat.get("narration"):
            continue
        report(f"voicing beat {i + 1}/{len(beats)}", 0.05 + 0.35 * (i / max(1, len(beats))))

        try:
            audio_bytes, ext = await tts.synthesize(beat["narration"], voice=voice)
        except tts.TTSError as e:
            raise VideoRenderError(f"Voiceover failed on beat {i + 1}: {e}")

        path = os.path.join(audio_dir, f"beat_{i:03d}.{ext}")
        with open(path, "wb") as f:
            f.write(audio_bytes)
        beat_audio_paths.append((beat, path))

    if not beat_audio_paths:
        raise VideoRenderError("No narration beats produced usable audio.")

    # Attach code excerpt to show_code beats
    if code_excerpt:
        for beat, _ in beat_audio_paths:
            if beat["visual"] == "show_code":
                beat["code"] = code_excerpt

    # 2. Render frames timed to each beat's actual audio duration ───────────
    frame_index = 0
    for i, (beat, audio_path) in enumerate(beat_audio_paths):
        duration = _audio_duration_seconds(audio_path) + 0.3  # small tail pad
        report(f"animating beat {i + 1}/{len(beat_audio_paths)}", 0.4 + 0.4 * (i / len(beat_audio_paths)))
        n = _render_beat_frames(
            beat, title, related_concepts, duration, frame_dir, frame_index,
            beat_idx=i, total_beats=len(beat_audio_paths),
        )
        frame_index += n

    # 3. Concatenate audio tracks ────────────────────────────────────────────
    concat_list = os.path.join(work_dir, "audio_concat.txt")
    with open(concat_list, "w") as f:
        for _, audio_path in beat_audio_paths:
            f.write(f"file '{audio_path}'\n")

    combined_audio = os.path.join(work_dir, "combined_audio.wav")
    report("mixing audio", 0.82)
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-ar", "24000", "-ac", "1",   # normalise sample rate across MP3+WAV mix
        combined_audio,
    ])

    # 4. Encode frames + audio → MP4 ─────────────────────────────────────────
    report("encoding video", 0.90)
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frame_dir, "frame_%06d.png"),
        "-i", combined_audio,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        output_path,
    ])

    report("done", 1.0)
    shutil.rmtree(frame_dir, ignore_errors=True)
    shutil.rmtree(audio_dir, ignore_errors=True)
    return output_path


def _run_ffmpeg(cmd: list[str]):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise VideoRenderError(
            "ffmpeg not found on your system.\n"
            "Install it with:  brew install ffmpeg\n"
            "Then restart the backend server with:  uvicorn app.main:app --reload --port 8000"
        )
    if result.returncode != 0:
        raise VideoRenderError(f"ffmpeg error: {result.stderr[-800:]}")
