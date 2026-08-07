#!/usr/bin/env python3
"""Claude Code status line — single line, color-coded.

Shows: model · effort · thinking/fast flags │ context progress bar
(used/max tokens) │ 5h/7d rate-limit usage.

Reads the status line JSON object from stdin (see Claude Code docs for the
schema). Every optional field is handled gracefully — a field missing from
a given session's input (effort, thinking, fast_mode, rate_limits, ...) is
simply dropped from the line rather than shown as blank/broken.
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"


def fg256(code: int) -> str:
    return f"\x1b[38;5;{code}m"


CYAN = fg256(37)
GRAY = fg256(244)
BLUE = fg256(33)
MAGENTA = fg256(170)
YELLOW = fg256(220)

# 256-color gradient, light-to-dark: green -> lime -> gold -> orange -> red.
GREEN = fg256(70)
LIME = fg256(148)
GOLD = fg256(220)
ORANGE = fg256(208)
RED = fg256(196)

DEFAULT_MAX_SIZE = 200_000  # fallback window size when none is provided

STYLE_STATE_FILE = os.path.expanduser("~/.ai-dev-toolkit/style-last")
STYLE_LABELS = {"lite": "caveman lite", "full": "caveman full", "ultra": "caveman ultra"}
STYLE_COLORS = {"lite": BLUE, "full": YELLOW, "ultra": ORANGE}


def read_active_style() -> tuple[str, str] | None:
    try:
        with open(STYLE_STATE_FILE, encoding="utf-8") as f:
            value = f.read().strip()
    except OSError:
        return None
    label = STYLE_LABELS.get(value)
    if not label:
        return None
    return label, STYLE_COLORS[value]


def color_for_pct(pct: float) -> str:
    if pct >= 90:
        return RED
    if pct >= 70:
        return YELLOW
    return GREEN


# Context color scale depends on the active model's max window, not a flat
# percentage: a 200K model (Haiku) gets a simple 3-tier scale, while a 1M
# model (Sonnet/Opus 5) gets a finer 5-tier scale whose first two shade
# changes still land at the same 100K/200K absolute marks — so a 150K-token
# session always reads as "yellowish" whichever model produced it, but a 1M
# session has more room to show gradually escalating color past that point.
def color_for_context_tokens(used_tokens: float, max_size: float | None) -> str:
    if max_size and max_size <= 200_000:
        if used_tokens >= 180_000:
            return RED
        if used_tokens >= 100_000:
            return YELLOW
        return GREEN

    # 1M-class (or unknown/larger) window: 5-tier scale.
    if used_tokens >= 700_000:
        return RED
    if used_tokens >= 400_000:
        return ORANGE
    if used_tokens >= 200_000:
        return GOLD
    if used_tokens >= 100_000:
        return LIME
    return GREEN


def fmt_tokens(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{round(n / 1000)}K"
    return str(int(n))


def progress_bar(pct: float, width: int = 6) -> str:
    filled = round((pct / 100) * width)
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def fmt_time_remaining(resets_at: float) -> str | None:
    remaining = resets_at - time.time()
    if remaining <= 0:
        return None
    days, rem = divmod(int(remaining), 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d{hours:02d}h"
    if hours:
        return f"{hours}h{minutes:02d}"
    return f"{minutes}min"


def fmt_reset_date(resets_at: float) -> str | None:
    if resets_at - time.time() <= 0:
        return None
    return time.strftime("%b %d, %H:%M", time.localtime(resets_at))


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    parts = []

    # --- model / effort / thinking / fast mode ---
    model_name = (data.get("model") or {}).get("display_name") or "Claude"
    head = f"{BOLD}{CYAN}{model_name}{RESET}"

    effort = (data.get("effort") or {}).get("level")
    if effort:
        head += f" {GRAY}·{RESET} {MAGENTA}{effort}{RESET}"

    if data.get("fast_mode"):
        head += f" {GRAY}·{RESET} {YELLOW}fast{RESET}"

    style = read_active_style()
    if style:
        style_label, style_color = style
        head += f" {GRAY}·{RESET} {style_color}{style_label}{RESET}"

    parts.append(head)

    # --- context window usage ---
    ctx = data.get("context_window") or {}
    used_pct = ctx.get("used_percentage")
    max_size = ctx.get("context_window_size")
    total_in = ctx.get("total_input_tokens")
    total_out = ctx.get("total_output_tokens")

    if used_pct is None and ctx.get("remaining_percentage") is not None:
        used_pct = 100 - ctx["remaining_percentage"]

    if used_pct is not None:
        used_tokens = (total_in or 0) + (total_out or 0)
        if not used_tokens:
            # No raw token counts in this input — approximate from the
            # percentage, falling back to a sane default window size so the
            # color scale still reflects reality when max_size is missing.
            used_tokens = (used_pct / 100) * (max_size or DEFAULT_MAX_SIZE)

        c = color_for_context_tokens(used_tokens, max_size)
        bar = progress_bar(used_pct)
        piece = f"{c}[{bar}]{RESET} {c}{round(used_pct)}%{RESET}"
        if max_size:
            piece += f" {GRAY}({fmt_tokens(used_tokens)}/{fmt_tokens(max_size)}){RESET}"
        parts.append(piece)

    # --- rate limits (with time remaining before reset) ---
    rl = data.get("rate_limits") or {}
    five = (rl.get("five_hour") or {}).get("used_percentage")
    five_resets = (rl.get("five_hour") or {}).get("resets_at")
    week = (rl.get("seven_day") or {}).get("used_percentage")
    week_resets = (rl.get("seven_day") or {}).get("resets_at")

    if five is not None:
        c = color_for_pct(five)
        bar = progress_bar(five, width=4)
        piece = f"5h {c}[{bar}]{RESET} {c}{round(five)}%{RESET}"
        if five_resets:
            remaining = fmt_time_remaining(five_resets)
            if remaining:
                piece += f" {GRAY}({remaining}){RESET}"
        parts.append(piece)

    if week is not None:
        c = color_for_pct(week)
        bar = progress_bar(week, width=4)
        piece = f"7d {c}[{bar}]{RESET} {c}{round(week)}%{RESET}"
        if week_resets:
            reset_date = fmt_reset_date(week_resets)
            if reset_date:
                piece += f" {GRAY}({reset_date}){RESET}"
        parts.append(piece)

    sep = f" {GRAY}│{RESET} "
    sys.stdout.write(sep.join(parts))


if __name__ == "__main__":
    main()
