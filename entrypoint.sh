#!/bin/bash
set -euo pipefail

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

echo "Starting OpenClaw Gateway..."
exec openclaw gateway run --bind lan --port "$GATEWAY_PORT"
