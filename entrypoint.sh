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
