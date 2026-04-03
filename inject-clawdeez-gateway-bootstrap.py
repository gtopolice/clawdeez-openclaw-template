#!/usr/bin/env python3
"""Copy ClawDeez gateway bootstrap into OpenClaw's Control UI and inject <script> before </body>."""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys


def npm_global_root() -> pathlib.Path:
    out = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
    return pathlib.Path(out)


def main() -> int:
    root = npm_global_root()
    ui_dir = root / "openclaw" / "dist" / "control-ui"
    index = ui_dir / "index.html"
    src_js = pathlib.Path("/app/clawdeez-gateway-bootstrap.js")
    dst_js = ui_dir / "clawdeez-gateway-bootstrap.js"

    if not index.is_file():
        print("OpenClaw control-ui index.html not found:", index, file=sys.stderr)
        return 1
    if not src_js.is_file():
        print("Bootstrap source missing:", src_js, file=sys.stderr)
        return 1

    shutil.copyfile(src_js, dst_js)

    text = index.read_text(encoding="utf-8")
    marker = "clawdeez-gateway-bootstrap.js"
    if marker in text:
        return 0

    inject = (
        '    <script src="./clawdeez-gateway-bootstrap.js"></script>\n'
        "  </body>"
    )
    if "</body>" not in text:
        print("No </body> in control-ui index.html", file=sys.stderr)
        return 1

    text = text.replace("</body>", inject, 1)
    index.write_text(text, encoding="utf-8")
    print("Injected ClawDeez gateway bootstrap into", index, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
