# ClawDeez Railway template — installs upstream OpenClaw CLI (see OPENCLAW_VERSION).
# OpenClaw requires Node >= 22.14; on Node 20, bare `npm i -g openclaw` resolves to a
# name-squat placeholder (0.0.1) with no CLI — use Node 22+.
# Default OPENCLAW_VERSION=latest (npm dist-tag). Override the Docker build arg to pin (e.g. 2026.4.2).
FROM node:22-slim

LABEL org.opencontainers.image.title="ClawDeez · OpenClaw gateway (Railway)"
LABEL org.opencontainers.image.description="ClawDeez-hosted OpenClaw gateway: persistent /data, Control UI origin patch, OpenRouter onboarding."
LABEL org.opencontainers.image.vendor="ClawDeez"
LABEL org.opencontainers.image.source="https://github.com/gtopolice/clawdeez-openclaw-template"
LABEL org.opencontainers.image.documentation="https://github.com/gtopolice/clawdeez-openclaw-template#readme"
LABEL com.clawdeez.template="openclaw-railway"
LABEL com.clawdeez.palette="blue-600"

ARG OPENCLAW_VERSION=latest

RUN apt-get update && apt-get install -y --no-install-recommends git python3 python3-pip && \
    rm -rf /var/lib/apt/lists/* && \
    npm install -g "openclaw@${OPENCLAW_VERSION}" && \
    openclaw --version

# OpenClaw's ensurePiCompactionReserveTokens() forces reserveTokens >= 20_000 (pi-settings.ts).
# That overrides clawdeez.json (e.g. 3072) and exceeds 16k-context models → precheck overflow.
COPY patch-openclaw-pi-compaction-default.py /app/patch-openclaw-pi-compaction-default.py
RUN chmod +x /app/patch-openclaw-pi-compaction-default.py && \
    python3 /app/patch-openclaw-pi-compaction-default.py

# ClawDeez favicons (synced from clawdeez-core frontend/src/app); overrides OpenClaw defaults in dist/control-ui
COPY clawdeez-control-ui-icons/ /app/clawdeez-control-ui-icons/
COPY clawdeez-favicon.svg /app/clawdeez-favicon.svg
RUN UI="$(npm root -g)/openclaw/dist/control-ui" && \
    cp /app/clawdeez-control-ui-icons/favicon.ico "$UI/favicon.ico" && \
    cp /app/clawdeez-control-ui-icons/favicon-32.png "$UI/favicon-32.png" && \
    cp /app/clawdeez-control-ui-icons/apple-touch-icon.png "$UI/apple-touch-icon.png" && \
    cp /app/clawdeez-control-ui-icons/clawdeez-brand-logo.png "$UI/clawdeez-brand-logo.png" && \
    cp /app/clawdeez-favicon.svg "$UI/favicon.svg" && \
    sed -i 's|type="image/svg+xml" href="./favicon.svg"|type="image/x-icon" href="./favicon.ico"|' "$UI/index.html"

COPY openclaw-control-ui-brand.css /app/openclaw-control-ui-brand.css
COPY clawdeez-gateway-bootstrap.js /app/clawdeez-gateway-bootstrap.js
COPY clawdeez-control-ui-brand.js /app/clawdeez-control-ui-brand.js
COPY inject-clawdeez-gateway-bootstrap.py /app/inject-clawdeez-gateway-bootstrap.py
RUN chmod +x /app/inject-clawdeez-gateway-bootstrap.py && \
    python3 /app/inject-clawdeez-gateway-bootstrap.py && \
    cp /app/clawdeez-control-ui-brand.js "$(npm root -g)/openclaw/dist/control-ui/clawdeez-control-ui-brand.js" && \
    cp /app/openclaw-control-ui-brand.css "$(npm root -g)/openclaw/dist/control-ui/openclaw-control-ui-brand.css"

# Set standard environment variables for persistence
ENV OPENCLAW_STATE_DIR=/data/.openclaw
ENV OPENCLAW_WORKSPACE_DIR=/data/workspace
# Force logs to ERROR to prevent prompt leakage in Railway dashboard
ENV LOG_LEVEL=error 

COPY workspace-fragments/ /app/workspace-fragments/

COPY entrypoint.sh /app/entrypoint.sh
COPY patch-openclaw-origins.py /app/patch-openclaw-origins.py
COPY patch-openclaw-branding.py /app/patch-openclaw-branding.py
RUN chmod +x /app/entrypoint.sh /app/patch-openclaw-origins.py /app/patch-openclaw-branding.py

ENTRYPOINT ["/app/entrypoint.sh"]