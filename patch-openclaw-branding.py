#!/usr/bin/env python3
"""Merge ClawDeez branding into OpenClaw config and Control UI (connect shell + chat).

Reads Railway variables set by clawdeez-core provisioning (see backend `openclawProvisionBranding.ts`):

- OPENCLAW_UI_ASSISTANT_NAME -> ui.assistant.name + Gateway Dashboard title/text overrides
- OPENCLAW_UI_ASSISTANT_AVATAR -> ui.assistant.avatar; optional HTTPS override for Control UI logos
- OPENCLAW_UI_SEAM_COLOR -> ui.seamColor; overrides --primary/--accent on connect shell
- OPENCLAW_UI_GATEWAY_SUBTITLE -> replaces "Gateway Dashboard" (default: Panel del gateway)
- OPENCLAW_CONTROL_UI_BRAND_CSS_URL -> optional extra stylesheet (HTTPS); if unset, ./openclaw-control-ui-brand.css bundled in the image (same-origin, CSP-safe)
- OPENCLAW_COMPACTION_RESERVE_TOKENS_FLOOR -> minimum `agents.defaults.compaction.reserveTokensFloor` (default depends on **INJECTED_OR_MODEL**: `openrouter/auto` → high floor; MEDIUM/FREE constrained routes → modest floor so ~16k ctx models are not starved). **skip** / **0** skips raising the floor from env but still **clamps** an existing value above the tier ceiling (fixes onboard defaults that starve small-context routes).

Wire-up: see [clawdeez-openclaw-template](https://github.com/gtopolice/clawdeez-openclaw-template).
"""
from __future__ import annotations

import html
import json
import os
import pathlib
import re
import subprocess
import sys

# Mirrors `packages/clawdeez-config` OPENCLAW_COMPACTION_RESERVE_TOKENS_FLOOR_BY_TIER + ceilings.
# MEDIUM (`openrouter/auto:free,*-small*…`) often resolves to ~16k ctx — a floor near the
# context size makes `promptBudgetBeforeReserve` collapse and triggers immediate overflow.
_INJECTED_ADVANCED = "openrouter/auto"
_INJECTED_MEDIUM = "openrouter/auto:free,*-small*,*-mini*,*-nano*,*-flash*"
_INJECTED_FREE = "openrouter/free"


def _normalized_injected_model() -> str:
    """Strip provider prefixes Railway may omit but OpenClaw logs with (e.g. custom-openrouter-ai/)."""
    m = os.environ.get("INJECTED_OR_MODEL", "").strip()
    for prefix in ("custom-openrouter-ai/",):
        if m.startswith(prefix):
            return m[len(prefix) :]
    return m


def _compaction_floor_ceiling_from_injected_model() -> tuple[int, int]:
    """Return (default_floor, max_allowed) for reserveTokensFloor."""
    m = _normalized_injected_model()
    if m == _INJECTED_ADVANCED:
        return (98304, 200000)
    # 16k ctx: large reserveTokensFloor steals budget from system+workspace; keep floor/cap modest.
    if m == _INJECTED_MEDIUM:
        return (3072, 4096)
    if m == _INJECTED_FREE:
        return (2048, 3072)
    # Substring match: exact env string can differ slightly from constants across releases.
    if "openrouter/auto:free" in m and "*-small*" in m:
        return (3072, 4096)
    if m.startswith("openrouter/auto:free") and "*-small*" in m:
        return (3072, 4096)
    if m.startswith("openrouter/free"):
        return (2048, 3072)
    return (3072, 4096)


def npm_global_root() -> pathlib.Path:
    out = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
    return pathlib.Path(out)


SHELL_START = "<!-- clawdeez-brand-shell-start -->"
SHELL_END = "<!-- clawdeez-brand-shell-end -->"


def accent_hover(base_hex: str) -> str:
    raw = base_hex.strip().lstrip("#")
    if len(raw) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", raw):
        return "#1d4ed8"
    r = int(raw[0:2], 16)
    g = int(raw[2:4], 16)
    b = int(raw[4:6], 16)
    r = max(0, min(255, int(r * 0.88)))
    g = max(0, min(255, int(g * 0.88)))
    b = max(0, min(255, int(b * 0.92)))
    return f"#{r:02x}{g:02x}{b:02x}"


def merge_ui_from_env(cfg: dict) -> bool:
    name = os.environ.get("OPENCLAW_UI_ASSISTANT_NAME", "").strip()
    avatar = os.environ.get("OPENCLAW_UI_ASSISTANT_AVATAR", "").strip()
    seam = os.environ.get("OPENCLAW_UI_SEAM_COLOR", "").strip()

    if not name and not avatar and not seam:
        return False

    ui = cfg.setdefault("ui", {})
    if name:
        assistant = ui.setdefault("assistant", {})
        assistant["name"] = name
    if avatar:
        assistant = ui.setdefault("assistant", {})
        assistant["avatar"] = avatar
    if seam:
        ui["seamColor"] = seam
    return True


def merge_compaction_reserve_floor(cfg: dict) -> bool:
    """Merge reserveTokensFloor; cap by INJECTED_OR_MODEL so small-context routes do not overflow."""
    floor_default, ceiling = _compaction_floor_ceiling_from_injected_model()
    raw = os.environ.get(
        "OPENCLAW_COMPACTION_RESERVE_TOKENS_FLOOR",
        str(floor_default),
    ).strip()
    if not raw:
        raw = str(floor_default)

    agents = cfg.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    compaction = defaults.setdefault("compaction", {})
    cur_raw = compaction.get("reserveTokensFloor")
    try:
        current = int(cur_raw) if cur_raw is not None else 0
    except (TypeError, ValueError):
        current = 0

    # "skip" means do not raise the floor from env — but we still clamp an unsafe value
    # (e.g. onboard default 98304) so ~16k OpenRouter routes do not get promptBudgetBeforeReserve≈1.
    if raw.lower() in ("0", "false", "off", "skip", "none"):
        if current <= ceiling:
            return False
        new_val = min(current, ceiling)
        compaction["reserveTokensFloor"] = new_val
        return True

    try:
        floor_min = int(raw, 10)
    except ValueError:
        print(
            "OPENCLAW_COMPACTION_RESERVE_TOKENS_FLOOR invalid; using",
            floor_default,
            file=sys.stderr,
        )
        floor_min = floor_default
    if floor_min < 0:
        return False
    floor_min = min(floor_min, ceiling)
    new_val = min(max(floor_min, current), ceiling)
    if compaction.get("reserveTokensFloor") == new_val:
        return False
    compaction["reserveTokensFloor"] = new_val
    return True


def patch_openclaw_json() -> None:
    state_dir = os.environ.get("OPENCLAW_STATE_DIR", os.path.expanduser("~/.openclaw"))
    path = os.path.join(state_dir, "openclaw.json")
    if not os.path.isfile(path):
        return

    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)

    changed = merge_ui_from_env(cfg)
    changed = merge_compaction_reserve_floor(cfg) or changed
    if not changed:
        return

    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")

    print("Merged ClawDeez config into", path, file=sys.stderr)


def strip_brand_shell(html_text: str) -> str:
    pattern = re.escape(SHELL_START) + r".*?" + re.escape(SHELL_END)
    return re.sub(pattern, "", html_text, flags=re.DOTALL)


def build_brand_shell_block() -> str | None:
    name = os.environ.get("OPENCLAW_UI_ASSISTANT_NAME", "").strip()
    seam = os.environ.get("OPENCLAW_UI_SEAM_COLOR", "").strip()
    avatar = os.environ.get("OPENCLAW_UI_ASSISTANT_AVATAR", "").strip()
    subtitle = os.environ.get("OPENCLAW_UI_GATEWAY_SUBTITLE", "").strip() or "Panel del gateway"

    if not name and not seam and not avatar:
        return None

    accent = seam or "#2563eb"
    hover = accent_hover(accent)
    subtle = accent + "1a" if accent.startswith("#") and len(accent) == 7 else "#2563eb1a"
    glow = accent + "33" if accent.startswith("#") and len(accent) == 7 else "#2563eb33"

    lines = [
        SHELL_START,
        '<style type="text/css" data-clawdeez-brand-shell="1">',
        ":root{",
        f"--accent:{accent}!important;--primary:{accent}!important;--ring:{accent}!important;",
        f"--accent-hover:{hover}!important;--accent-muted:{accent}!important;",
        f"--accent-subtle:{subtle}!important;--accent-glow:{glow}!important;",
        "}",
        "</style>",
    ]
    if name:
        payload = {
            "assistantName": name,
            "gatewaySubtitle": subtitle,
            "avatarUrl": avatar,
        }
        lines.append(
            '<script type="application/json" id="clawdeez-brand-json">'
            + json.dumps(payload, ensure_ascii=False)
            + "</script>"
        )
        lines.append('<script defer src="./clawdeez-control-ui-brand.js"></script>')
    lines.append(SHELL_END)
    return "\n".join(lines) + "\n"


def patch_control_ui_index_html() -> None:
    ui_dir = npm_global_root() / "openclaw" / "dist" / "control-ui"
    index = ui_dir / "index.html"
    if not index.is_file():
        print("OpenClaw control-ui index.html not found:", index, file=sys.stderr)
        return

    text = index.read_text(encoding="utf-8")
    updated = strip_brand_shell(text)

    name = os.environ.get("OPENCLAW_UI_ASSISTANT_NAME", "").strip()
    if name:
        updated = re.sub(
            r"<title>[^<]*</title>",
            f"<title>{html.escape(name)} · Control</title>",
            updated,
            count=1,
        )

    css_url = os.environ.get("OPENCLAW_CONTROL_UI_BRAND_CSS_URL", "").strip()
    bundled_css = ui_dir / "openclaw-control-ui-brand.css"
    if not css_url and bundled_css.is_file():
        # Same-origin avoids OpenClaw Control UI CSP blocking cross-domain stylesheets
        # (e.g. apex marketing site vs *.clawdeez.cloud gateway).
        css_url = "./openclaw-control-ui-brand.css"
    css_marker = 'data-clawdeez-brand-css="1"'
    if css_url and css_marker not in updated:
        link = f'  <link rel="stylesheet" href="{html.escape(css_url)}" {css_marker} />\n'
        if "</head>" in updated:
            updated = updated.replace("</head>", link + "</head>", 1)

    shell = build_brand_shell_block()
    if shell and "</head>" in updated:
        updated = updated.replace("</head>", shell + "</head>", 1)

    if updated != text:
        index.write_text(updated, encoding="utf-8")
        print("Patched ClawDeez shell into", index, file=sys.stderr)


def main() -> int:
    try:
        patch_openclaw_json()
    except OSError as e:
        print("patch-openclaw-branding (openclaw.json):", e, file=sys.stderr)
        return 1
    try:
        patch_control_ui_index_html()
    except OSError as e:
        print(
            "patch-openclaw-branding (control-ui index, non-fatal):",
            e,
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
