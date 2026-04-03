#!/usr/bin/env python3
"""Merge Control UI settings into openclaw.json from env.

- allowedOrigins: OPENCLAW_PUBLIC_ORIGIN, RAILWAY_PUBLIC_DOMAIN, OPENCLAW_ALLOWED_ORIGINS
- dangerouslyDisableDeviceAuth: OPENCLAW_CONTROL_UI_DISABLE_DEVICE_AUTH (opt-in; see README)
"""
from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlparse


def env_truthy(name: str) -> bool:
    v = os.environ.get(name, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def to_origin(url_or_host: str) -> str | None:
    s = url_or_host.strip().rstrip("/")
    if not s:
        return None
    if "://" not in s:
        s = "https://" + s
    p = urlparse(s)
    if not p.scheme or not p.hostname:
        return None
    scheme = p.scheme.lower()
    host = p.hostname
    port = p.port
    if port:
        if (scheme, port) in (("http", 80), ("https", 443)):
            return f"{scheme}://{host}"
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def compute_origins() -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(o: str | None) -> None:
        if not o or o in seen:
            return
        seen.add(o)
        out.append(o)

    primary = os.environ.get("OPENCLAW_PUBLIC_ORIGIN") or os.environ.get("PUBLIC_APP_URL")
    railway = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if primary:
        add(to_origin(primary))
    elif railway:
        add(to_origin(railway))

    extra = os.environ.get("OPENCLAW_ALLOWED_ORIGINS", "")
    for part in extra.split(","):
        add(to_origin(part.strip()))

    return out


def main() -> int:
    state_dir = os.environ.get("OPENCLAW_STATE_DIR", os.path.expanduser("~/.openclaw"))
    path = os.path.join(state_dir, "openclaw.json")

    if not os.path.isfile(path):
        return 0

    computed = compute_origins()
    disable_device_auth = env_truthy("OPENCLAW_CONTROL_UI_DISABLE_DEVICE_AUTH")

    if not computed and not disable_device_auth:
        return 0

    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)

    gw = cfg.setdefault("gateway", {})
    cu = gw.setdefault("controlUi", {})

    if computed:
        existing = cu.get("allowedOrigins")
        if not isinstance(existing, list):
            existing = []
        normalized_existing: list[str] = []
        seen: set[str] = set()
        for x in existing:
            if not isinstance(x, str):
                continue
            o = to_origin(x)
            if o is None:
                s = x.strip().rstrip("/")
                if "://" in s:
                    o = s
            if o and o not in seen:
                seen.add(o)
                normalized_existing.append(o)

        merged: list[str] = []
        merged_seen: set[str] = set()
        for o in normalized_existing + computed:
            if o not in merged_seen:
                merged_seen.add(o)
                merged.append(o)

        cu["allowedOrigins"] = merged
        print(
            "Control UI allowedOrigins:",
            ", ".join(merged),
            file=sys.stderr,
        )

    if disable_device_auth:
        cu["dangerouslyDisableDeviceAuth"] = True
        print(
            "Control UI dangerouslyDisableDeviceAuth: true (pairing bypass — token-only trust)",
            file=sys.stderr,
        )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
