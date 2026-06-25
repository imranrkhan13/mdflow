"""
Generates a short narration script for a section, broken into "beats" —
each beat is one sentence-ish chunk of narration paired with a visual
instruction (which node to highlight, whether to show code, etc). The
video renderer later turns each beat into one timed segment.

Asking the LLM for structured JSON beats (rather than one paragraph) is
what makes the animation able to sync to the voiceover instead of just
playing a generic loop underneath it.
"""
import json
import re

from app.services.ai_router import generate, ProviderError

SYSTEM_PROMPT = (
    "You write short narration scripts for an animated explainer video about a software concept. "
    "Output ONLY valid JSON — no markdown fences, no commentary, just the raw JSON array. "
    "The JSON must be a list of 4 to 6 beats. Each beat is an object with exactly these keys: "
    '"narration" (1-2 short spoken sentences, plain English, max 25 words each), '
    '"visual" (one of: "title", "highlight_node", "concepts", "show_code", "summary"), '
    '"emphasis" (a single short word or phrase — the key term of this beat, or empty string). '
    "Rules: "
    "1. First beat MUST have visual=title. Last beat MUST have visual=summary. "
    "2. Use concepts visual when listing multiple related ideas. "
    "3. Use show_code only if there is actual code to show. "
    "4. Keep narration plain — no jargon, use analogies like a good teacher would. "
    "5. Each beat should feel like one clear thought, not a paragraph. "
    "6. Total narration should be 60-90 seconds of spoken audio (about 140-200 words total). "
    "Example beat: {\"narration\": \"Think of this like a bouncer at a club.\", \"visual\": \"highlight_node\", \"emphasis\": \"Authentication\"}"
)


def _extract_json(raw: str) -> list[dict]:
    # Models sometimes wrap JSON in ```json fences despite instructions —
    # strip those defensively before parsing.
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)


async def generate_script(title: str, content: str, concepts: list[str], code_excerpt: str = "") -> list[dict]:
    prompt = (
        f"Concept title: {title}\n"
        f"Detected related concepts: {', '.join(concepts) or 'none'}\n"
        f"Source content:\n{content[:1500]}\n"
    )
    if code_excerpt:
        prompt += f"\nRelevant code:\n```\n{code_excerpt[:800]}\n```\n"

    try:
        result = await generate(prompt, system=SYSTEM_PROMPT)
    except ProviderError as e:
        raise

    try:
        beats = _extract_json(result["text"])
    except (json.JSONDecodeError, TypeError) as e:
        # Fall back to a single-beat script rather than failing the whole
        # video — a flat narration is still better than nothing.
        beats = [
            {"narration": title, "visual": "title", "emphasis": title},
            {
                "narration": result["text"][:400],
                "visual": "highlight_node",
                "emphasis": "",
            },
            {"narration": f"That's {title} in a nutshell.", "visual": "summary", "emphasis": ""},
        ]

    # Defensive normalization in case the model omits a key or returns
    # something malformed for one beat.
    normalized = []
    for b in beats:
        if not isinstance(b, dict) or "narration" not in b:
            continue
        normalized.append(
            {
                "narration": str(b.get("narration", "")).strip(),
                "visual": b.get("visual", "highlight_node"),
                "emphasis": str(b.get("emphasis", "")).strip(),
            }
        )

    if not normalized:
        raise ProviderError("Script generation produced no usable beats.")

    return normalized
