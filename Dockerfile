FROM node:20-slim

# Install OpenClaw globally and required dependencies
RUN apt-get update && apt-get install -y git python3 pip && \
    npm install -g openclaw

# Set standard environment variables for persistence
ENV OPENCLAW_STATE_DIR=/data/.openclaw
ENV OPENCLAW_WORKSPACE_DIR=/data/workspace
# Force logs to ERROR to prevent prompt leakage in Railway dashboard
ENV LOG_LEVEL=error 

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]