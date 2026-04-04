#!/bin/bash
set -euo pipefail

# ClawDeez brand line in Railway logs (blue ANSI; harmless if stripped)
CLAWDEEZ_DIM='\033[2m'
CLAWDEEZ_BLUE='\033[0;34m'
CLAWDEEZ_BOLD='\033[1;34m'
CLR='\033[0m'
echo -e "${CLAWDEEZ_BOLD}ClawDeez${CLR} ${CLAWDEEZ_DIM}·${CLR} ${CLAWDEEZ_BLUE}OpenClaw gateway on Railway${CLR} ${CLAWDEEZ_DIM}(template)${CLR}"

mkdir -p "$OPENCLAW_STATE_DIR" "${OPENCLAW_WORKSPACE_DIR:-/data/workspace}"

GATEWAY_PORT="${PORT:-18789}"
MODEL_ID="${INJECTED_OR_MODEL:-openrouter/auto}"

if [ ! -f "$OPENCLAW_STATE_DIR/openclaw.json" ]; then
    echo "First boot detected. Provisioning ClawDeez agent headlessly..."
    : "${INJECTED_OR_KEY:?INJECTED_OR_KEY is required on first boot}"

    openclaw onboard --non-interactive \
      --accept-risk \
      --auth-choice custom-api-key \
      --custom-base-url "https://openrouter.ai/api/v1" \
      --custom-model-id "$MODEL_ID" \
      --custom-api-key "$INJECTED_OR_KEY" \
      --secret-input-mode plaintext \
      --custom-compatibility openai \
      --skip-health \
      --no-install-daemon \
      --gateway-bind lan \
      --gateway-port "$GATEWAY_PORT" \
      --workspace "${OPENCLAW_WORKSPACE_DIR:-/data/workspace}"
fi

# Ensure gateway.controlUi.allowedOrigins includes this deployment's browser origin
# (required for non-loopback Control UI; see README).
python3 /app/patch-openclaw-origins.py
python3 /app/patch-openclaw-branding.py

# Idempotent ClawDeez fragments (Spanish-first, Control UI scope, identity name). Skips if markers exist.
# Disable with CLAWDEEZ_SKIP_WORKSPACE_FRAGMENTS=1. Runs after onboard so upstream workspace files exist.
clawdeez_apply_workspace_fragments() {
    local ws="${OPENCLAW_WORKSPACE_DIR:-/data/workspace}"
    if [[ "${CLAWDEEZ_SKIP_WORKSPACE_FRAGMENTS:-0}" == "1" ]]; then
        return 0
    fi
    mkdir -p "$ws"
    # Empty when Railway omits OPENCLAW_UI_ASSISTANT_NAME so OpenClaw onboard defaults apply in the UI.
    export CLAWDEEZ_ASSISTANT_NAME="${OPENCLAW_UI_ASSISTANT_NAME:-}"
    python3 -c '
import os, pathlib
src = pathlib.Path("/app/workspace-fragments/clawdeez-identity.md").read_text(encoding="utf-8")
raw = os.environ.get("CLAWDEEZ_ASSISTANT_NAME", "").strip()
fallback = "_(sin nombre fijado por ClawDeez; la UI usa la configuración por defecto de OpenClaw hasta que el usuario defina el nombre — p. ej. `OPENCLAW_UI_ASSISTANT_NAME` o IDENTITY.md)_"
display = raw if raw else fallback
pathlib.Path("/tmp/clawdeez-identity-resolved.md").write_text(
    src.replace("__CLAWDEEZ_ASSISTANT_NAME__", display), encoding="utf-8"
)
'
    clawdeez_prepend_if_absent() {
        local target="$1"
        local marker="$2"
        local fragment_path="$3"
        [[ -f "$target" ]] || return 0
        grep -qF "$marker" "$target" 2>/dev/null && return 0
        local tmp
        tmp="$(mktemp)"
        cat "$fragment_path" "$target" >"$tmp"
        mv "$tmp" "$target"
    }
    clawdeez_prepend_if_absent "$ws/AGENTS.md" "<!-- clawdeez-scope -->" \
        "/app/workspace-fragments/clawdeez-preamble-agents.md"
    clawdeez_prepend_if_absent "$ws/IDENTITY.md" "<!-- clawdeez-identity -->" \
        "/tmp/clawdeez-identity-resolved.md"
    clawdeez_prepend_if_absent "$ws/SOUL.md" "<!-- clawdeez-soul -->" \
        "/app/workspace-fragments/clawdeez-soul-prefix.md"
    clawdeez_prepend_if_absent "$ws/USER.md" "<!-- clawdeez-user-scope -->" \
        "/app/workspace-fragments/clawdeez-user-prefix.md"
    rm -f /tmp/clawdeez-identity-resolved.md
}

clawdeez_apply_workspace_fragments

# OpenClaw injects workspace bootstrap files (e.g. AGENTS.md) into the assistant system
# context — see https://docs.openclaw.ai/concepts/system-prompt
clawdeez_append_workspace_hosting_context() {
    local ws="${OPENCLAW_WORKSPACE_DIR:-/data/workspace}"
    local f="$ws/AGENTS.md"
    local m="<!-- clawdeez-hosting-context -->"

    mkdir -p "$ws"
    if [[ -f "$f" ]] && grep -qF "$m" "$f" 2>/dev/null; then
        return 0
    fi

    {
        echo ""
        echo "$m"
        echo "## Hosting (ClawDeez · Railway)"
        echo "This OpenClaw gateway runs in a container on **Railway**, provisioned through **ClawDeez** (managed agent hosting)."
        echo "When asked where you run, who operates the infrastructure, or what platform this is, answer accurately: **OpenClaw on Railway via ClawDeez**—not a vague “cloud” answer, and do not deny Railway or ClawDeez when the user states them."
        echo "LLM inference for chat uses **OpenRouter** with the model/tier configured for this deployment (not a single fixed vendor story in replies unless relevant)."
        if [[ -n "${OPENCLAW_PUBLIC_ORIGIN:-}" ]]; then
            echo "Users typically open this Control UI at: ${OPENCLAW_PUBLIC_ORIGIN}"
        elif [[ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]]; then
            echo "Railway public hostname: ${RAILWAY_PUBLIC_DOMAIN} (HTTPS is usually https://${RAILWAY_PUBLIC_DOMAIN})."
        fi
        echo "$m"
    } >>"$f"
}

clawdeez_append_workspace_hosting_context

echo -e "${CLAWDEEZ_BLUE}Starting OpenClaw gateway…${CLR}"
exec openclaw gateway run --bind lan --port "$GATEWAY_PORT"
