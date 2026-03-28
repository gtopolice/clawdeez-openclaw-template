#!/bin/bash

mkdir -p "$OPENCLAW_STATE_DIR"

if [ ! -f "$OPENCLAW_STATE_DIR/openclaw.json" ]; then
    echo "First boot detected. Provisioning ClawDeez agent headlessly..."
    
    # Notice the --model line now uses a dynamic variable
    openclaw onboard --non-interactive \
      --provider "openai-compatible" \
      --endpoint "https://openrouter.ai/api/v1" \
      --key "$INJECTED_OR_KEY" \
      --model "${INJECTED_OR_MODEL:-openrouter/auto}" \
      --yes
fi

echo "Starting OpenClaw Gateway..."
exec openclaw gateway start
