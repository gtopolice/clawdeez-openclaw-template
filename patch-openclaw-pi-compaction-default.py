#!/usr/bin/env python3
"""Lower OpenClaw's DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR in the global npm install.

Upstream `ensurePiCompactionReserveTokens` bumps reserveTokens up to the default (20k)
whenever current < default. That overrides clawdeez `openclaw.json` (e.g. 3072) and
exceeds ~16k-context models — logs: reserveTokens≈16384, promptBudgetBeforeReserve=1.

The published package ships a **hashed** chunk (e.g. dist/pi-settings-*.js) with
`const DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR = 2e4` (not a literal 20000).

We set it to 2048 so sub-20k reserves from config are preserved. Advanced tiers still
set explicit high floors in openclaw.json.

Idempotent: safe to run on every image build.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys


def npm_global_root() -> pathlib.Path:
    out = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
    return pathlib.Path(out)


def find_pi_settings_chunks(root: pathlib.Path) -> list[pathlib.Path]:
    dist = root / "openclaw" / "dist"
    if not dist.is_dir():
        return []
    # Rollup/Vite emits pi-settings-<hash>.js
    return sorted(dist.glob("pi-settings-*.js"))


def patch_file(path: pathlib.Path) -> bool:
    """Return True if this file defines the constant and is OK (already or after patch)."""
    text = path.read_text(encoding="utf-8")
    if "DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR" not in text:
        return True
    if re.search(r"const DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR = 2048\b", text):
        return True
    # Published openclaw uses scientific notation 2e4 for 20000
    patterns = (
        (r"(const DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR = )2e4\b", r"\g<1>2048"),
        (r"(const DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR = )20_000\b", r"\g<1>2048"),
        (r"(const DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR = )20000\b", r"\g<1>2048"),
    )
    for pat, repl in patterns:
        new_text, n = re.subn(pat, repl, text, count=1)
        if n == 1:
            path.write_text(new_text, encoding="utf-8")
            print("Patched", path, "DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR -> 2048", file=sys.stderr)
            return True
    return False


def main() -> int:
    root = npm_global_root()
    chunks = find_pi_settings_chunks(root)
    if not chunks:
        print(
            "patch-openclaw-pi-compaction-default: no dist/pi-settings-*.js under",
            root / "openclaw",
            file=sys.stderr,
        )
        return 1

    found_definition = False
    for path in chunks:
        t = path.read_text(encoding="utf-8")
        if "DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR" in t:
            found_definition = True
            if not patch_file(path):
                print(
                    "patch-openclaw-pi-compaction-default: unrecognized constant format in",
                    path,
                    file=sys.stderr,
                )
                return 1

    if not found_definition:
        print(
            "patch-openclaw-pi-compaction-default: no DEFAULT_PI_COMPACTION_RESERVE_TOKENS_FLOOR in",
            chunks,
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
