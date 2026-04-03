#!/usr/bin/env python3
"""Merge ClawDeez branding into OpenClaw config and optional Control UI stylesheet link.

Reads Railway variables set by clawdeez-core provisioning (see backend `openclawProvisionBranding.ts`):

- OPENCLAW_UI_ASSISTANT_NAME -> ui.assistant.name
- OPENCLAW_UI_ASSISTANT_AVATAR -> ui.assistant.avatar (HTTPS image URL)
- OPENCLAW_UI_SEAM_COLOR -> ui.seamColor
- OPENCLAW_CONTROL_UI_BRAND_CSS_URL -> inject <link rel="stylesheet"> into control-ui index.html

Wire-up in [clawdeez-openclaw-template](https://github.com/gtopolice/clawdeez-openclaw-template):

**Dockerfile** (with the other COPY/chmod lines for entrypoint and origins):

  COPY patch-openclaw-branding.py /app/patch-openclaw-branding.py
  RUN chmod +x /app/patch-openclaw-branding.py
  # append branding to the existing chmod line that lists entrypoint + origins, e.g.:
  # RUN chmod +x /app/entrypoint.sh /app/patch-openclaw-origins.py /app/patch-openclaw-branding.py

**entrypoint.sh** (immediately after `python3 /app/patch-openclaw-origins.py`):

  python3 /app/patch-openclaw-branding.py
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys


def npm_global_root() -> pathlib.Path:
    out = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
    return pathlib.Path(out)


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


def patch_openclaw_json() -> None:
    state_dir = os.environ.get("OPENCLAW_STATE_DIR", os.path.expanduser("~/.openclaw"))
    path = os.path.join(state_dir, "openclaw.json")
    if not os.path.isfile(path):
        return

    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)

    if not merge_ui_from_env(cfg):
        return

    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")

    print("Merged ClawDeez UI branding into", path, file=sys.stderr)


def inject_brand_stylesheet() -> None:
    url = os.environ.get("OPENCLAW_CONTROL_UI_BRAND_CSS_URL", "").strip()
    if not url:
        return

    ui_dir = npm_global_root() / "openclaw" / "dist" / "control-ui"
    index = ui_dir / "index.html"
    if not index.is_file():
        print("OpenClaw control-ui index.html not found:", index, file=sys.stderr)
        return

    text = index.read_text(encoding="utf-8")
    marker = 'data-clawdeez-brand-css="1"'
    if marker in text:
        return

    link = f'  <link rel="stylesheet" href="{url}" {marker} />\n'
    if "</head>" in text:
        text = text.replace("</head>", link + "</head>", 1)
    elif "</body>" in text:
        text = text.replace("</body>", link + "</body>", 1)
    else:
        print("No </head> or </body> in control-ui index.html", file=sys.stderr)
        return

    index.write_text(text, encoding="utf-8")
    print("Injected ClawDeez brand stylesheet link into", index, file=sys.stderr)


def main() -> int:
    try:
        patch_openclaw_json()
    except OSError as e:
        print("patch-openclaw-branding (openclaw.json):", e, file=sys.stderr)
        return 1
    try:
        inject_brand_stylesheet()
    except OSError as e:
        # Global npm openclaw path may be read-only on some hosts; UI config still applies.
        print(
            "patch-openclaw-branding (stylesheet inject, non-fatal):",
            e,
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
