from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ai_router import generate, ProviderError
from app.services.store import get_project, get_section

router = APIRouter(prefix="/api/explain", tags=["explain"])

# ── System prompts ────────────────────────────────────────────────────────────

EXPLAIN_SYSTEM = """You are MindFlow — a brilliant coding mentor who makes complex software simple.

STRICT RULES:
1. Write like you're texting a smart friend who codes, not writing a textbook.
2. ALWAYS start with a one-sentence real-world analogy. Pick something vivid: bouncer at a club, pizza delivery tracker, post office sorting room. Make it specific.
3. Short sentences only. If a sentence has more than 18 words, break it into two.
4. Bold ONLY the most important term per section — not every noun.
5. Use ## for section headings. Use bullet points for lists. Never write paragraphs longer than 3 sentences.
6. If there's code: explain what EACH LINE does. Literally say "Line 1 does X. Line 2 does Y."
7. End EVERY response with exactly: "**In short:** [one punchy sentence]"
8. Never use these words: "crucial", "important", "note that", "it's worth", "leverage", "robust", "scalable"."""

INTERVIEW_SYSTEM = """You are a staff engineer at a top tech company (think Google, Stripe, Airbnb) who interviews candidates weekly.

You give brutally honest, specific interview prep based on what's ACTUALLY in the project — not generic advice.

RULES:
1. Read the project content carefully. Every question must reference something SPECIFIC from this actual project.
2. Don't ask generic "what is X" questions. Ask questions about THIS system's choices and tradeoffs.
3. For each question write: the question, then "**What they're testing:**" (one line), then "**Strong answer covers:**" (2-3 bullets of what a good answer includes).
4. Include a section called "How to talk about this project in 60 seconds" — write a sample pitch they can memorise.
5. Include "Red flags to avoid" — 3 specific things junior devs say that make interviewers cringe.
6. Be direct. If the architecture has weaknesses, say so — interviewers will ask about them.
7. Use ## for sections. Use numbered lists for questions."""

ARCHITECTURE_SYSTEM = """You are a senior engineer doing a code review and architecture walkthrough for a junior dev joining the team.

You explain things the way a good mentor would on day 1 — specific, honest, and practical.

RULES:
1. Base EVERYTHING on the actual content provided. Don't invent components that aren't there.
2. Start with "The one-sentence summary:" — describe what this project actually does.
3. Then explain the data flow as a numbered story: "1. User does X → 2. This triggers Y → 3. Which calls Z → 4. Which returns W"
4. For each major component: say what it does, what would break if you removed it, and one common mistake devs make with it.
5. Include a "Biggest risks" section — what are the actual weak points of THIS architecture.
6. Include "If you had to scale this" — what would you change first and why.
7. Never pad with generic advice. If there's not enough info to say something specific, say "Not enough info to assess this."
8. Use ## for sections. Bold component names."""


class ExplainRequest(BaseModel):
    project_id: str
    section_id: str
    mode: str = "explain"

class InterviewRequest(BaseModel):
    project_id: str

class ArchitectureRequest(BaseModel):
    project_id: str


MODE_PROMPTS = {
    "explain": (
        "Explain what this component does.\n"
        "Start with the real-world analogy. Then cover:\n"
        "- What it does (in plain English)\n"
        "- Why it exists (what breaks without it)\n"
        "- Who/what talks to it\n"
        "- One common mistake developers make with it\n"
        "End with: **In short:** [one sentence]"
    ),
    "analogy": (
        "Explain this concept using ONLY a real-world story. No technical terms at all.\n"
        "Pick a specific scenario (a restaurant, a concert venue, a post office, a hospital — pick the best fit).\n"
        "Walk through the whole story step by step.\n"
        "Then at the end reveal how each part of your story maps to the actual technical concept.\n"
        "Make it memorable. It's okay to be funny."
    ),
    "interview": (
        "Give 4 interview questions about this SPECIFIC concept as it appears in this project.\n"
        "Easy (anyone), Medium (1yr exp), Hard (senior), Tricky (gotcha question).\n"
        "For each: write the question, **What they're testing:** (one line), **Strong answer covers:** (2-3 bullets)\n"
        "End with: **The question that trips most people up:** and explain why."
    ),
    "mistakes": (
        "List the 4 most common mistakes developers make with this concept.\n"
        "For each:\n"
        "- **Mistake:** [name it in one line]\n"
        "- **Why it happens:** [one sentence]\n"
        "- **What goes wrong:** [the actual consequence]\n"
        "- **The fix:** [concrete solution]\n\n"
        "Be specific to this component, not generic advice."
    ),
}


@router.post("")
async def explain_section(req: ExplainRequest):
    project = get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    section = get_section(req.project_id, req.section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    instruction = MODE_PROMPTS.get(req.mode, MODE_PROMPTS["explain"])
    code_part = ""
    if section.code_blocks:
        code_part = f"\n\nActual code from this section:\n```\n{section.code_blocks[0][:1500]}\n```"

    prompt = (
        f"{instruction}\n\n"
        f"---\n"
        f"Component: {section.title}\n"
        f"Related concepts in this system: {', '.join(sorted(section.concepts)) or 'none detected'}\n"
        f"Content from the docs:\n{section.content[:2500]}"
        f"{code_part}"
    )

    try:
        result = await generate(prompt, system=EXPLAIN_SYSTEM)
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=f"All AI providers failed: {e}")
    return result


@router.post("/interview")
async def generate_interview_prep(req: InterviewRequest):
    project = get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    sections = project["sections"]
    filename = project["filename"]

    # Build a real summary of what's actually in the project
    section_titles = [s.title for s in sections.values()]
    all_concepts = set()
    content_chunks = []
    has_code = []

    for s in list(sections.values())[:10]:
        all_concepts.update(s.concepts)
        if s.content.strip():
            content_chunks.append(f"**{s.title}**\n{s.content[:600]}")
        if s.code_blocks:
            has_code.append(f"{s.title}: {s.code_blocks[0][:300]}")

    concepts_str = ", ".join(sorted(all_concepts)) or "general software concepts"
    content_str = "\n\n".join(content_chunks[:7])
    code_str = "\n\n".join(has_code[:3])

    prompt = (
        f"Project file: {filename}\n"
        f"Sections: {', '.join(section_titles)}\n"
        f"Technical concepts found: {concepts_str}\n\n"
        f"=== ACTUAL PROJECT CONTENT ===\n{content_str}\n\n"
        + (f"=== CODE EXAMPLES ===\n{code_str}\n\n" if code_str else "")
        + "Generate a complete interview prep guide for THIS specific project. "
        "Use the actual content above — don't give generic advice.\n\n"
        "Structure:\n"
        "## How to talk about this project (60-second pitch)\n"
        "[Write an actual script they can say out loud. First person. Confident. Specific numbers if you can infer them.]\n\n"
        "## What you actually built\n"
        "[Bullet points of specific technical decisions visible in the content above]\n\n"
        "## Technical questions (based on what's in this project)\n"
        "### Easy\n[3 questions with what-they-test and strong-answer-covers]\n\n"
        "### Medium\n[3 questions]\n\n"
        "### Hard\n[2 questions — these should be about tradeoffs and design decisions]\n\n"
        "## Architecture questions\n"
        "[3 questions specifically about how this is structured and why]\n\n"
        "## Red flags to avoid\n"
        "[3 specific things a junior dev might say about THIS project that would hurt them]\n\n"
        "## Weaknesses to be honest about\n"
        "[What are the real limitations of this project that an interviewer might probe?]"
    )

    try:
        result = await generate(prompt, system=INTERVIEW_SYSTEM)
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=f"All AI providers failed: {e}")
    return result


@router.post("/architecture")
async def explain_architecture(req: ArchitectureRequest):
    project = get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    sections = project["sections"]
    filename = project["filename"]

    section_titles = [s.title for s in sections.values()]
    all_concepts = set()
    content_chunks = []
    code_chunks = []

    for s in list(sections.values())[:12]:
        all_concepts.update(s.concepts)
        if s.content.strip():
            content_chunks.append(f"**{s.title}**\n{s.content[:700]}")
        if s.code_blocks:
            code_chunks.append(f"Code in '{s.title}':\n{s.code_blocks[0][:400]}")

    concepts_str = ", ".join(sorted(all_concepts)) or "general software"
    content_str = "\n\n".join(content_chunks[:8])
    code_str = "\n\n".join(code_chunks[:4])

    prompt = (
        f"Project: {filename}\n"
        f"Sections: {', '.join(section_titles)}\n"
        f"Technical concepts: {concepts_str}\n\n"
        f"=== ACTUAL CONTENT ===\n{content_str}\n\n"
        + (f"=== CODE ===\n{code_str}\n\n" if code_str else "")
        + "Explain the architecture of THIS specific project. Use only what's in the content above.\n\n"
        "Structure:\n"
        "## The one-sentence summary\n"
        "[What does this project actually do? One sentence.]\n\n"
        "## How it works (the data flow)\n"
        "[Number each step: 1. User does X → 2. Y happens → 3. Z is called → 4. Response is W]\n\n"
        "## The components\n"
        "[For each real component found in the content: what it does, what breaks without it, common mistake]\n\n"
        "## How the pieces connect\n"
        "[What talks to what? Draw it in text: Frontend → API → Database, etc.]\n\n"
        "## Biggest risks\n"
        "[What are the actual weak points of THIS architecture? Be honest. Max 3.]\n\n"
        "## If you had to scale this\n"
        "[What would you change first, and why? Be specific to what's here.]\n\n"
        "## What's missing\n"
        "[What would a production version need that this doesn't have?]"
    )

    try:
        result = await generate(prompt, system=ARCHITECTURE_SYSTEM)
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=f"All AI providers failed: {e}")
    return result
