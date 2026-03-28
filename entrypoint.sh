#!/bin/bash

# Ensure the data directory exists
mkdir -p "$OPENCLAW_STATE_DIR"

# Check if the agent has already been configured on this volume
if [ ! -f "$OPENCLAW_STATE_DIR/openclaw.json" ]; then
    echo "First boot detected. Provisioning ClawDeez agent headlessly..."
    
    # Run the non-interactive onboarding command using the injected key
    openclaw onboard --non-interactive \
      --provider "openai-compatible" \
      --endpoint "https://openrouter.ai/api/v1" \
      --key "$INJECTED_OR_KEY" \
      --model "openrouter/auto" \
      --yes
fi

echo "Starting OpenClaw Gateway..."
# Execute the main daemon
exec openclaw gateway start