#!/usr/bin/env python3
"""Generate README and social-preview PNGs (Sibyl Royal palette).

Regenerate when the TUI or pill changes. Requires Pillow:

    uv run --with pillow python scripts/generate_brand_assets.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"

# Sibyl Royal — notes/BRAND.md
BG = (8, 14, 26)
PANEL = (12, 22, 51)
PANEL2 = (16, 32, 64)
BORDER = (30, 58, 110)
TEXT = (232, 228, 217)
MUTED = (122, 138, 168)
GOLD = (201, 162, 39)
LIVE = (90, 143, 196)
PILL_BG = (0, 0, 0, 180)
ACCENT = (123, 47, 247)
ACCENT2 = (249, 115, 22)


def _font(size: int):
    from PIL import ImageFont

    candidates = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _draw_tui_dashboard(path: Path) -> None:
    from PIL import Image, ImageDraw

    w, h = 960, 540
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    font = _font(14)
    font_sm = _font(11)
    font_lg = _font(16)

    def bar(y: int, height: int, fill: tuple[int, int, int]) -> None:
        draw.rectangle([0, y, w, y + height], fill=fill, outline=BORDER)

    bar(0, 36, PANEL)
    draw.text((16, 10), "✦", fill=GOLD, font=font_lg)
    draw.text((40, 10), "sybl", fill=TEXT, font=font_lg)
    draw.text((100, 12), "● live", fill=GOLD, font=font)
    draw.text((170, 12), "idle", fill=MUTED, font=font)
    draw.text((650, 12), "v0.1.2 · up 2h14m · 38 today", fill=MUTED, font=font_sm)

    bar(36, 28, PANEL2)
    draw.text(
        (16, 42),
        "mic: default · deepgram · ctrl+alt+space · ipc connected",
        fill=MUTED,
        font=font_sm,
    )

    bar(64, 72, PANEL)
    draw.text((16, 72), "◌ IDLE", fill=MUTED, font=font)
    draw.text((120, 78), "▰▰▱▱▱▱▱▱", fill=GOLD, font=font)
    draw.text(
        (280, 72),
        "hold hotkey · double-press to toggle",
        fill=MUTED,
        font=font_sm,
    )

    body_top = 136
    draw.rectangle([0, body_top, 280, h - 80], fill=BG, outline=BORDER)
    draw.rectangle([280, body_top, w, h - 80], fill=BG, outline=BORDER)
    draw.line([280, body_top + 200, w, body_top + 200], fill=BORDER)

    draw.text((16, body_top + 8), "PIPELINE", fill=GOLD, font=font_sm)
    draw.text((16, body_top + 28), "capture → transcribe", fill=MUTED, font=font_sm)
    draw.text((16, body_top + 48), "→ cleanup → inject", fill=MUTED, font=font_sm)
    draw.text((16, body_top + 80), "PROVIDER", fill=GOLD, font=font_sm)
    draw.text((16, body_top + 100), "deepgram", fill=TEXT, font=font_sm)
    draw.text((16, body_top + 130), "HOTKEY", fill=GOLD, font=font_sm)
    draw.text((16, body_top + 150), "ctrl+alt+space", fill=TEXT, font=font_sm)

    draw.text((296, body_top + 8), "TRANSCRIPTS", fill=GOLD, font=font_sm)
    draw.text(
        (296, body_top + 32),
        "12w · 4s · groq",
        fill=MUTED,
        font=font_sm,
    )
    draw.text(
        (296, body_top + 52),
        '"Meeting notes for the release"',
        fill=TEXT,
        font=font_sm,
    )
    draw.text((296, body_top + 220), "LOGS", fill=GOLD, font=font_sm)
    draw.text(
        (296, body_top + 244),
        "12:04:02  daemon listening on hotkey",
        fill=MUTED,
        font=font_sm,
    )

    bar(h - 80, 36, PANEL)
    draw.text(
        (16, h - 68),
        'LIVE  last: "Meeting notes for the release"',
        fill=LIVE,
        font=font_sm,
    )

    bar(h - 44, 44, PANEL2)
    draw.text(
        (16, h - 32),
        "s settings  ? help  / filter  y copy  q quit",
        fill=MUTED,
        font=font_sm,
    )

    img.save(path)


def _draw_listening_pill(path: Path) -> None:
    from PIL import Image, ImageDraw

    w, h = 960, 200
    img = Image.new("RGB", (w, h), (20, 24, 32))
    draw = ImageDraw.Draw(img)
    font = _font(13)

    pill_w, pill_h = 280, 44
    x0 = (w - pill_w) // 2
    y0 = 0
    draw.rounded_rectangle(
        [x0, y0, x0 + pill_w, y0 + pill_h],
        radius=22,
        fill=(0, 0, 0),
    )

    bx = x0 + 14
    cy = y0 + pill_h // 2
    factors = [0.4, 0.55, 0.7, 0.85, 0.95, 0.75, 0.6]
    for i, factor in enumerate(factors):
        color = ACCENT if i % 2 == 0 else ACCENT2
        bar_h = int(8 + 14 * factor)
        draw.rectangle(
            [bx + i * 7, cy - bar_h // 2, bx + i * 7 + 4, cy + bar_h // 2],
            fill=color,
        )

    draw.text((x0 + 100, cy - 8), "Listening…", fill=TEXT, font=font)
    draw.text((x0 + pill_w - 52, cy - 8), "0:42", fill=MUTED, font=font)

    img.save(path)


def _draw_cli_banner(path: Path) -> None:
    from PIL import Image, ImageDraw

    w, h = 720, 420
    img = Image.new("RGB", (w, h), (12, 12, 16))
    draw = ImageDraw.Draw(img)
    font = _font(14)
    font_sm = _font(12)

    lines = [
        "    ✦  sybl",
        "   ─────────",
        "  speak · type · anywhere",
        "",
        "  open-source BYOK voice dictation — speak anywhere, type it in",
        "",
        "  Daemon",
        "    start   stop   restart   status   logs",
        "  Configuration",
        "    config   setup   providers",
    ]
    y = 24
    for line in lines:
        color = (86, 182, 194) if "sybl" in line or "✦" in line else (180, 180, 180)
        if line.startswith("  open-source"):
            color = (120, 120, 120)
        if line.strip() in {"Daemon", "Configuration"}:
            color = (201, 162, 39)
        draw.text((32, y), line, fill=color, font=font_sm if line.startswith("    ") else font)
        y += 22

    img.save(path)


def _draw_social_preview(path: Path) -> None:
    from PIL import Image

    w, h = 1280, 640
    canvas = Image.new("RGB", (w, h), BG)

    tui = Image.open(OUT / "tui-dashboard.png").convert("RGB")
    pill = Image.open(OUT / "listening-pill.png").convert("RGB")

    tui = tui.resize((760, 428))
    pill = pill.resize((480, 100))
    canvas.paste(tui, (480, 120))
    canvas.paste(pill, (400, 8))

    from PIL import ImageDraw

    draw = ImageDraw.Draw(canvas)
    font_lg = _font(48)
    font_md = _font(22)
    draw.text((48, 180), "✦ sybl", fill=GOLD, font=font_lg)
    draw.text(
        (48, 250),
        "Open-source BYOK voice dictation",
        fill=TEXT,
        font=font_md,
    )
    draw.text(
        (48, 290),
        "Global hotkey · terminal dashboard · dock listening pill",
        fill=MUTED,
        font=_font(18),
    )

    canvas.save(path)


def main() -> int:
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("Install Pillow: uv run --with pillow python scripts/generate_brand_assets.py")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    _draw_tui_dashboard(OUT / "tui-dashboard.png")
    _draw_listening_pill(OUT / "listening-pill.png")
    _draw_cli_banner(OUT / "cli-banner.png")
    _draw_social_preview(OUT / "social-preview.png")
    print(f"Wrote assets to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
