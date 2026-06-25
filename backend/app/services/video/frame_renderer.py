"""
Enhanced MindFlow video frame renderer.

Upgrades over v1:
  - Burned-in animated captions (word-by-word with highlight box)
  - Slide-in concept cards with stagger animation
  - Bottom progress bar showing position in video
  - Richer code frame with syntax token colours
  - Smoother easing, better motion timing
  - MindFlow watermark / branding bar
  - All same Pillow/ffmpeg stack — zero new dependencies
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH, HEIGHT = 1280, 720
FPS = 30

FONT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "assets", "fonts", "Inter-Variable.ttf"
)

# ── Theme ─────────────────────────────────────────────────────────────────────
PAPER      = (253, 252, 250)
PAPER_100  = (250, 248, 244)
PAPER_200  = (243, 239, 231)
UMBER_900  = (61,  43,  31)
UMBER_700  = (94,  69,  52)
UMBER_500  = (139, 90,  60)
UMBER_400  = (168, 122, 82)
UMBER_300  = (201, 168, 118)
UMBER_200  = (221, 201, 163)
UMBER_100  = (237, 226, 205)
CLAY       = (181, 103, 63)
CLAY_LIGHT = (220, 150, 100)
SAGE       = (107, 124, 94)
WHITE      = (255, 255, 255)

# Caption bar
CAPTION_BG   = (30, 20, 14)          # near-black for legibility
CAPTION_FG   = (255, 255, 255)       # white text
CAPTION_HI   = (255, 190, 120)       # highlighted word — warm amber
CAPTION_H    = 72                    # caption bar height in px

# Progress bar
PROGRESS_H   = 6
PROGRESS_BG  = UMBER_200
PROGRESS_FG  = CLAY


# ── Fonts ────────────────────────────────────────────────────────────────────

def _font(weight: int, size: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(FONT_PATH, size)
    try:
        f.set_variation_by_axes([min(size, 32), weight])
    except Exception:
        pass
    return f


# ── Easing ───────────────────────────────────────────────────────────────────

def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - pow(1 - t, 3)

def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 3*t*t - 2*t*t*t

def _spring(t: float, overshoot: float = 0.12) -> float:
    """Spring ease — overshoots then settles."""
    t = max(0.0, min(1.0, t))
    e = _ease_out_cubic(t)
    if t > 0.7:
        bounce = math.sin((t - 0.7) / 0.3 * math.pi) * overshoot * (1 - t)
        return e + bounce
    return e


# ── Base canvas ───────────────────────────────────────────────────────────────

def _base_canvas(progress: float = 0.0, beat_idx: int = 0, total_beats: int = 1) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(img)

    # Dot grid
    for x in range(0, WIDTH, 28):
        for y in range(0, HEIGHT - CAPTION_H - PROGRESS_H, 28):
            draw.ellipse([x, y, x+1.5, y+1.5], fill=PAPER_200)

    # Top branding bar
    draw.rectangle([0, 0, WIDTH, 40], fill=UMBER_900)
    logo_font = _font(700, 15)
    draw.text((20, 20), "MINDFLOW", font=logo_font, fill=CLAY, anchor="lm")
    # Beat dots
    dot_x = WIDTH - 20
    for i in range(total_beats):
        active = i == beat_idx
        col = CLAY if active else UMBER_700
        draw.ellipse([dot_x - 7, 14, dot_x + 7, 26], fill=col)
        dot_x -= 22

    # Caption bar (always at bottom)
    draw.rectangle([0, HEIGHT - CAPTION_H - PROGRESS_H, WIDTH, HEIGHT], fill=CAPTION_BG)

    # Progress bar
    bar_y = HEIGHT - PROGRESS_H
    draw.rectangle([0, bar_y, WIDTH, HEIGHT], fill=PROGRESS_BG)
    draw.rectangle([0, bar_y, int(WIDTH * progress), HEIGHT], fill=PROGRESS_FG)

    return img


# ── Caption rendering (word-by-word highlight) ───────────────────────────────

def _draw_caption(draw, narration: str, t: float, duration: float):
    """
    Renders narration text in the caption bar with a moving highlight
    that tracks approximately which word is being spoken.
    """
    if not narration:
        return

    words = narration.split()
    if not words:
        return

    font = _font(500, 24)
    hi_font = _font(700, 24)

    # Which word is "active" based on time position
    frac = min(1.0, t / max(0.1, duration))
    active_idx = int(frac * len(words))
    active_idx = min(active_idx, len(words) - 1)

    # Measure total line width to centre it
    space_w = draw.textlength(" ", font=font)
    total_w = sum(draw.textlength(w, font=hi_font if i == active_idx else font)
                  for i, w in enumerate(words)) + space_w * (len(words) - 1)

    # Wrap into max 2 lines if needed
    max_w = WIDTH - 80
    if total_w > max_w:
        # Split roughly at midpoint
        mid = len(words) // 2
        lines_words = [words[:mid], words[mid:]]
    else:
        lines_words = [words]

    caption_top = HEIGHT - CAPTION_H - PROGRESS_H
    line_h = 34
    n_lines = len(lines_words)
    start_y = caption_top + (CAPTION_H - n_lines * line_h) // 2

    word_offset = 0
    for li, line in enumerate(lines_words):
        # Measure this line
        line_w = sum(draw.textlength(w, font=hi_font if (word_offset + i) == active_idx else font)
                     for i, w in enumerate(line)) + space_w * (len(line) - 1)
        x = (WIDTH - line_w) / 2
        y = start_y + li * line_h

        for i, word in enumerate(line):
            gi = word_offset + i
            is_hi = gi == active_idx
            f = hi_font if is_hi else font
            w = word + (" " if i < len(line) - 1 else "")
            ww = draw.textlength(w, font=f)

            if is_hi:
                # Highlight box behind the active word
                pad = 4
                draw.rounded_rectangle(
                    [x - pad, y - pad, x + ww - draw.textlength(" ", font=f) + pad, y + 26 + pad],
                    radius=6, fill=(80, 50, 20)
                )
                draw.text((x, y), word, font=f, fill=CAPTION_HI)
            else:
                col = (200, 190, 180) if gi < active_idx else (160, 150, 140)
                draw.text((x, y), word, font=f, fill=col)

            x += ww
        word_offset += len(line)


# ── Individual beat renderers ─────────────────────────────────────────────────

def render_title_frame(
    t: float, title: str,
    subtitle: str = "MindFlow explains",
    narration: str = "", duration: float = 3.0,
    beat_idx: int = 0, total_beats: int = 1,
) -> Image.Image:
    progress = min(1.0, t / max(0.1, duration))
    img = _base_canvas(progress, beat_idx, total_beats)
    draw = ImageDraw.Draw(img)

    ease = _spring(min(1.0, t / 0.6))
    offset_y = (1 - ease) * 30

    # Eyebrow
    eyebrow_font = _font(600, 17)
    draw.text(
        (WIDTH / 2, HEIGHT / 2 - 80 - offset_y),
        subtitle.upper(),
        font=eyebrow_font, fill=CLAY, anchor="mm",
    )

    # Divider line that draws in
    line_w = int(120 * ease)
    draw.rectangle(
        [WIDTH//2 - line_w//2, HEIGHT//2 - 55 - offset_y,
         WIDTH//2 + line_w//2, HEIGHT//2 - 51 - offset_y],
        fill=CLAY
    )

    # Title
    title_font = _font(800, 54)
    words = title.split()
    # Build lines
    test_draw = ImageDraw.Draw(img)
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if test_draw.textlength(trial, font=title_font) <= WIDTH - 160:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    total_h = len(lines) * 66
    sy = HEIGHT / 2 - total_h / 2 + 10 - offset_y
    for i, line in enumerate(lines):
        alpha_t = _ease_out_cubic(max(0, (t - i * 0.08) / 0.4))
        col = tuple(int(UMBER_900[c] + (PAPER[c] - UMBER_900[c]) * (1 - alpha_t)) for c in range(3))
        draw.text((WIDTH/2, sy + i * 66), line, font=title_font, fill=col, anchor="mm")

    # Blur dissolve in
    if ease < 1.0:
        img = img.filter(ImageFilter.GaussianBlur(radius=(1 - ease) * 5))

    draw = ImageDraw.Draw(img)
    _draw_caption(draw, narration, t, duration)
    return img


def render_node_highlight_frame(
    t: float, title: str, related: list[str], emphasis: str,
    narration: str = "", duration: float = 3.0,
    beat_idx: int = 0, total_beats: int = 1,
) -> Image.Image:
    progress = min(1.0, t / max(0.1, duration))
    img = _base_canvas(progress, beat_idx, total_beats)
    draw = ImageDraw.Draw(img)

    # Usable canvas height (between top bar and caption bar)
    canvas_top = 48
    canvas_bot = HEIGHT - CAPTION_H - PROGRESS_H - 8
    cx = WIDTH / 2
    cy = canvas_top + (canvas_bot - canvas_top) / 2

    main_w, main_h = 260, 100
    pulse_norm = 0.85 + 0.15 * math.sin(t * 5.5)

    # Draw connections + related nodes first
    n = max(1, len(related))
    radius = 210
    positions = []
    for i, label in enumerate(related[:5]):
        angle = (2 * math.pi * i / n) - math.pi / 2
        nx = cx + radius * math.cos(angle)
        ny = cy + radius * math.sin(angle) * 0.55
        positions.append((nx, ny, label))

        # Animated dotted connection line
        appear_t = _ease_out_cubic(max(0, (t - 0.08 - i * 0.06) / 0.3))
        steps = 20
        for s in range(int(steps * appear_t)):
            p = s / steps
            lx = cx + (nx - cx) * p
            ly = cy + (ny - cy) * p
            if s % 2 == 0:  # dashed
                draw.ellipse([lx-2, ly-2, lx+2, ly+2], fill=UMBER_300)

    # Related node cards (slide in with spring)
    for i, (nx, ny, label) in enumerate(positions):
        appear = _spring(max(0, (t - 0.15 - i * 0.07) / 0.35))
        if appear <= 0.01:
            continue
        w, h = 148 * appear, 52 * appear
        box = [nx - w/2, ny - h/2, nx + w/2, ny + h/2]
        draw.rounded_rectangle(box, radius=int(12 * appear), fill=WHITE, outline=UMBER_200, width=2)
        if appear > 0.5:
            font = _font(600, 14)
            draw.text((nx, ny), label, font=font, fill=UMBER_700, anchor="mm")

    # Glow behind main node
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    halo_pad = 28
    gd.rounded_rectangle(
        [cx - main_w/2 - halo_pad, cy - main_h/2 - halo_pad,
         cx + main_w/2 + halo_pad, cy + main_h/2 + halo_pad],
        radius=32, fill=(*CLAY, int(130 * pulse_norm))
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=20))
    img = Image.alpha_composite(img.convert("RGBA"), glow_layer).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Main node card
    box_enter = _spring(min(1.0, t / 0.4))
    mw = main_w * box_enter
    mh = main_h * box_enter
    draw.rounded_rectangle(
        [cx - mw/2, cy - mh/2, cx + mw/2, cy + mh/2],
        radius=16, fill=WHITE, outline=CLAY, width=3
    )

    if box_enter > 0.5:
        tf = _font(700, 22)
        lines_t = []
        cur = ""
        for w in title.split():
            trial = (cur + " " + w).strip()
            if draw.textlength(trial, font=tf) <= mw - 30:
                cur = trial
            else:
                if cur: lines_t.append(cur)
                cur = w
        if cur: lines_t.append(cur)
        sy = cy - (len(lines_t) * 26) / 2 + 13
        for i, line in enumerate(lines_t[:2]):
            draw.text((cx, sy + i * 26), line, font=tf, fill=UMBER_900, anchor="mm")

    # Emphasis badge
    if emphasis and t > 0.7:
        alpha_t = _ease_out_cubic(min(1.0, (t - 0.7) / 0.3))
        ef = _font(700, 18)
        etw = draw.textlength(emphasis.upper(), font=ef)
        ex = WIDTH / 2 - etw / 2
        ey = canvas_bot - 36
        draw.rounded_rectangle(
            [ex - 14, ey - 6, ex + etw + 14, ey + 24],
            radius=14,
            outline=CLAY, width=2
        )
        draw.text((ex, ey), emphasis.upper(), font=ef, fill=CLAY)

    _draw_caption(draw, narration, t, duration)
    return img


def render_code_frame(
    t: float, title: str, code: str, emphasis: str,
    narration: str = "", duration: float = 3.0,
    beat_idx: int = 0, total_beats: int = 1,
) -> Image.Image:
    progress = min(1.0, t / max(0.1, duration))
    img = _base_canvas(progress, beat_idx, total_beats)
    draw = ImageDraw.Draw(img)

    canvas_top = 48
    canvas_bot = HEIGHT - CAPTION_H - PROGRESS_H - 8

    pad = 60
    panel_top = canvas_top + 10
    panel_bot = canvas_bot - 6
    panel_box = [pad, panel_top, WIDTH - pad, panel_bot]

    # Slide up enter
    enter = _spring(min(1.0, t / 0.45))
    offset = (1 - enter) * 20
    panel_box = [pad, panel_top + offset, WIDTH - pad, panel_bot + offset]

    draw.rounded_rectangle(panel_box, radius=16, fill=UMBER_900, outline=UMBER_700, width=2)

    # Traffic lights
    for i, color in enumerate([CLAY, UMBER_300, SAGE]):
        draw.ellipse([pad + 20 + i*22, panel_top + offset + 14,
                      pad + 20 + i*22 + 12, panel_top + offset + 26], fill=color)

    # File title
    label_font = _font(600, 15)
    draw.text((pad + 20, panel_top + offset + 38), title, font=label_font, fill=UMBER_300)

    # Code lines with typewriter reveal
    code_font = _font(400, 17)
    lines = (code or "# no code excerpt").strip().split("\n")[:12]
    reveal_frac = _ease_out_cubic(min(1.0, t / max(0.5, duration * 0.7)))
    visible = max(1, int(reveal_frac * len(lines)))

    # Basic keyword colouring
    KEYWORD_COLS = {
        "def": (150, 180, 255), "return": (150, 180, 255), "class": (150, 180, 255),
        "import": (150, 180, 255), "from": (150, 180, 255), "if": (150, 180, 255),
        "else": (150, 180, 255), "for": (150, 180, 255), "async": (150, 180, 255),
        "await": (150, 180, 255),
    }
    STRING_COL = (180, 230, 160)
    DEFAULT_COL = (230, 224, 214)

    for i, line in enumerate(lines):
        if i >= visible:
            break
        y = panel_top + offset + 70 + i * 27
        if y > panel_bot + offset - 20:
            break

        x = pad + 28
        tokens = line.replace("\t", "    ")
        # Simple tokeniser — colour keywords
        parts = tokens.split(" ")
        for part in parts:
            stripped = part.lstrip()
            if stripped in KEYWORD_COLS:
                col = KEYWORD_COLS[stripped]
            elif stripped.startswith('"') or stripped.startswith("'"):
                col = STRING_COL
            elif stripped.startswith("#"):
                col = (140, 130, 120)
            else:
                col = DEFAULT_COL
            w = draw.textlength(part + " ", font=code_font)
            draw.text((x, y), part, font=code_font, fill=col)
            x += w

    _draw_caption(draw, narration, t, duration)
    return img


def render_concepts_frame(
    t: float, title: str, concepts: list[str], explanation: str,
    narration: str = "", duration: float = 3.0,
    beat_idx: int = 0, total_beats: int = 1,
) -> Image.Image:
    """NEW: Shows concept cards in a grid, each sliding in with stagger."""
    progress = min(1.0, t / max(0.1, duration))
    img = _base_canvas(progress, beat_idx, total_beats)
    draw = ImageDraw.Draw(img)

    canvas_top = 52
    canvas_bot = HEIGHT - CAPTION_H - PROGRESS_H - 8

    # Section title
    title_font = _font(700, 28)
    title_enter = _ease_out_cubic(min(1.0, t / 0.3))
    draw.text((80, canvas_top + 20), title, font=title_font, fill=UMBER_900,
              anchor="lm" if False else None)

    # Concept cards in a 2-column grid
    concepts_to_show = concepts[:6]
    n = len(concepts_to_show)
    cols = 2
    rows = math.ceil(n / cols)
    card_w = 500
    card_h = 72
    gap_x = 30
    gap_y = 16
    grid_w = cols * card_w + (cols - 1) * gap_x
    grid_x = (WIDTH - grid_w) / 2
    grid_y = canvas_top + 65

    for i, concept in enumerate(concepts_to_show):
        row = i // cols
        col = i % cols
        stagger = 0.12 + i * 0.06
        card_t = _spring(max(0, (t - stagger) / 0.35))
        if card_t <= 0.01:
            continue

        x = grid_x + col * (card_w + gap_x)
        y = grid_y + row * (card_h + gap_y) + (1 - card_t) * 20
        box = [x, y, x + card_w * card_t + card_w * (1 - card_t), y + card_h]
        draw.rounded_rectangle(box, radius=14, fill=WHITE, outline=UMBER_200, width=2)

        if card_t > 0.5:
            icon_box = [x + 12, y + 12, x + 48, y + card_h - 12]
            draw.rounded_rectangle(icon_box, radius=8, fill=CLAY, outline=None)
            num_font = _font(700, 18)
            draw.text(((icon_box[0]+icon_box[2])//2, (icon_box[1]+icon_box[3])//2),
                      str(i+1), font=num_font, fill=WHITE, anchor="mm")
            cf = _font(600, 17)
            draw.text((x + 62, y + card_h//2), concept, font=cf, fill=UMBER_900, anchor="lm")

    _draw_caption(draw, narration, t, duration)
    return img


def render_summary_frame(
    t: float, title: str, narration: str = "",
    duration: float = 3.0, beat_idx: int = 0, total_beats: int = 1,
) -> Image.Image:
    progress = min(1.0, t / max(0.1, duration))
    img = _base_canvas(progress, beat_idx, total_beats)
    draw = ImageDraw.Draw(img)

    canvas_top = 48
    canvas_bot = HEIGHT - CAPTION_H - PROGRESS_H - 8
    cy_mid = canvas_top + (canvas_bot - canvas_top) / 2

    ease = _spring(min(1.0, t / 0.5))

    # Big checkmark circle
    cr = max(4, int(52 * ease))
    cx_c = WIDTH // 2
    cy_c = int(cy_mid - 70)
    draw.ellipse([cx_c - cr, cy_c - cr, cx_c + cr, cy_c + cr], fill=SAGE)
    cf = _font(700, max(8, int(44 * ease)))
    draw.text((cx_c, cy_c), "✓", font=cf, fill=WHITE, anchor="mm")

    # "In short:" label
    label_f = _font(600, 16)
    draw.text((WIDTH//2, cy_mid - 5), "IN SHORT", font=label_f, fill=CLAY, anchor="mm")

    # Title
    tf = _font(700, 38)
    draw.text((WIDTH//2, cy_mid + 40), title, font=tf, fill=UMBER_900, anchor="mm")

    # Summary text
    bf = _font(500, 20)
    words = narration.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=bf) <= WIDTH - 300:
            cur = trial
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)

    sy = cy_mid + 88
    for i, line in enumerate(lines[:3]):
        line_t = _ease_out_cubic(max(0, (t - 0.3 - i * 0.1) / 0.3))
        col = tuple(int(UMBER_500[c] + (PAPER[c] - UMBER_500[c]) * (1 - line_t)) for c in range(3))
        draw.text((WIDTH//2, sy + i * 30), line, font=bf, fill=col, anchor="mm")

    _draw_caption(draw, narration, t, duration)
    return img


VISUAL_RENDERERS = {
    "title":          render_title_frame,
    "highlight_node": render_node_highlight_frame,
    "show_code":      render_code_frame,
    "show_connections": render_node_highlight_frame,
    "concepts":       render_concepts_frame,
    "summary":        render_summary_frame,
}
