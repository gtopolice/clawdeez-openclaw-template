# OpenClaw requires Node >= 22.14; on Node 20, bare `npm i -g openclaw` resolves to a
# name-squat placeholder (0.0.1) with no CLI — use Node 22+ and a pinned version.
FROM node:22-slim

ARG OPENCLAW_VERSION=2026.3.28

RUN apt-get update && apt-get install -y --no-install-recommends git python3 python3-pip && \
    rm -rf /var/lib/apt/lists/* && \
    npm install -g "openclaw@${OPENCLAW_VERSION}" && \
    openclaw --version

# Set standard environment variables for persistence
ENV OPENCLAW_STATE_DIR=/data/.openclaw
ENV OPENCLAW_WORKSPACE_DIR=/data/workspace
# Force logs to ERROR to prevent prompt leakage in Railway dashboard
ENV LOG_LEVEL=error 

COPY entrypoint.sh /app/entrypoint.sh
COPY patch-openclaw-origins.py /app/patch-openclaw-origins.py
RUN chmod +x /app/entrypoint.sh /app/patch-openclaw-origins.py

ENTRYPOINT ["/app/entrypoint.sh"]