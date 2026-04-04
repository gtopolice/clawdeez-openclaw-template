<!-- ClawDeez template branding: blue palette aligns with clawdeez.cloud -->

<div align="center">

[![ClawDeez](https://img.shields.io/badge/ClawDeez-agent%20hosting-2563eb?style=for-the-badge&labelColor=1e3a8a)](https://github.com/gtopolice/clawdeez-core)
[![OpenClaw](https://img.shields.io/badge/Powered%20by-OpenClaw-1d4ed8?style=for-the-badge&labelColor=172554)](https://docs.openclaw.ai/)
[![Railway](https://img.shields.io/badge/Deploy-Railway-0ea5e9?style=for-the-badge&labelColor=0c4a6e)](https://railway.app/)

### ClawDeez · OpenClaw gateway (Railway)

**Managed agent runtime template** for [ClawDeez](https://github.com/gtopolice/clawdeez-core): runs the upstream [OpenClaw](https://docs.openclaw.ai/) gateway on [Railway](https://railway.app/) with persistent `/data`, LAN binding for the public URL, and startup patches for Control UI origins (and optional device-auth bypass). OpenClaw is the engine; ClawDeez is the hosting and provisioning layer.

</div>

---

## Control UI and `allowedOrigins`

The Control UI connects to the gateway over WebSockets with browser origin checks. For non-loopback deployments you must allow the exact origin you use in the browser: scheme, host, and port (e.g. `https://your-service.up.railway.app` — **no trailing slash**).

This template sets `gateway.controlUi.allowedOrigins` in `openclaw.json` **on every startup** by merging values derived from the environment (see below). Prefer **explicit** origins in production; do **not** rely on `dangerouslyAllowHostHeaderOriginFallback` unless you have no other option.

### Environment variables

| Variable | Purpose |
| -------- | ------- |
| `RAILWAY_PUBLIC_DOMAIN` | Set automatically by Railway to the service hostname (e.g. `something.up.railway.app`). The entrypoint derives `https://<hostname>` and adds it to `allowedOrigins`. |
| `OPENCLAW_PUBLIC_ORIGIN` | Optional override: full origin for this deployment, e.g. `https://my-service.up.railway.app`. Takes precedence over `RAILWAY_PUBLIC_DOMAIN` when both apply. Use this if your public URL is not the default Railway domain (custom domain, or tooling that provisions a hostname). |
| `PUBLIC_APP_URL` | Alias for `OPENCLAW_PUBLIC_ORIGIN` (same normalization: scheme + host + port). |
| `OPENCLAW_ALLOWED_ORIGINS` | Comma-separated **extra** origins to merge (e.g. a second hostname or `http://localhost:5173` for local dev against a remote gateway). |
| `OPENCLAW_CONTROL_UI_DISABLE_DEVICE_AUTH` | Set to `1`, `true`, `yes`, or `on` to write `gateway.controlUi.dangerouslyDisableDeviceAuth: true` into `openclaw.json` on each start. **Skips Control UI device pairing** so end users only need the gateway token (no `openclaw devices approve` on the host). **Security tradeoff:** anyone with the token can use the Control UI from any browser; prefer manual pairing for high-assurance setups. Test against your OpenClaw image version — some releases had regressions around this flag. |
| `OPENCLAW_UI_ASSISTANT_NAME` | ClawDeez: merged into `ui.assistant.name` in `openclaw.json` on each start (Control UI title / identity). |
| `OPENCLAW_UI_ASSISTANT_AVATAR` | HTTPS URL, emoji, or short text for `ui.assistant.avatar` (e.g. hosted logo). |
| `OPENCLAW_UI_SEAM_COLOR` | Hex accent for `ui.seamColor` (e.g. ClawDeez `#2563eb`). |
| `OPENCLAW_UI_GATEWAY_SUBTITLE` | Replaces the connect screen string **Gateway Dashboard** (default when unset: `Panel del gateway`). Optional `PROVISION_OPENCLAW_GATEWAY_SUBTITLE` on the clawdeez-core backend passes through on provision. |
| `OPENCLAW_CONTROL_UI_BRAND_CSS_URL` | Optional HTTPS URL to a stylesheet; injected into bundled Control UI `index.html` on start when writable (best-effort). |

Startup runs `patch-openclaw-branding.py` after `patch-openclaw-origins.py` to merge `openclaw.json` `ui.*`, patch **Gateway Dashboard** / connect chrome (CSS variables + title + `clawdeez-control-ui-brand.js`), and add the optional extra stylesheet. [clawdeez-core](https://github.com/gtopolice/clawdeez-core) provisioning sets these from `PROVISION_CLAWDEEZ_PUBLIC_ORIGIN` and related `PROVISION_OPENCLAW_BRAND_*` backend env vars.

If none of the origin-related variables yield an origin, the patch step still runs when `OPENCLAW_CONTROL_UI_DISABLE_DEVICE_AUTH` is enabled (origins-only merge is skipped in that case).

### Control UI device pairing vs gateway token

OpenClaw uses two layers: **gateway token** (secret) and **device pairing** (first browser connect must be approved on the gateway host, e.g. `openclaw devices approve <id>`). If your users see **“pairing required”** after pasting the correct token, either approve the device once via Railway **Shell** on that service, or set **`OPENCLAW_CONTROL_UI_DISABLE_DEVICE_AUTH=1`** on the Railway service and **redeploy** so the startup patch applies.

### Gateway token (Control UI login)

- If the gateway has **no** token configured, the “Gateway token” field in the Control UI can be left empty.
- If **`OPENCLAW_GATEWAY_TOKEN`** is set in Railway (or `gateway.auth.token` is set in config), the gateway expects that token — **paste the same value** into the Control UI. Mismatch or omission will fail authentication.

#### ClawDeez: prefill from URL hash (strip-after-read)

This template ships a small script in the Control UI (`clawdeez-gateway-bootstrap.js`) that:

1. Reads the gateway token from the **URL fragment**: `#clawdeez-gw=<encodeURIComponent(token)>`
2. Waits until the token field exists (including inside Shadow DOM), then **prefills** it and dispatches `input` / `change` events.
3. Calls **`history.replaceState`** so the fragment disappears from the address bar after read (token is not kept in the visible URL).

**Example (open in a new tab from ClawDeez after revealing the token):**

`https://your-agent.example.com/#clawdeez-gw=ENCODED_TOKEN`

Prefer **fragments over query strings** so the token is not sent to the server on navigation.

**sessionStorage (same origin only):** if there is no hash, the script checks `sessionStorage.removeItem('clawdeez.openclawGatewayToken')` once — useful for manual testing on the agent origin. It does **not** cross from `clawdeez.cloud` to `*.clawdeez.cloud`.

**OpenClaw upgrades:** the inject step patches `openclaw`’s bundled `dist/control-ui/index.html` at **image build** time. If a future `openclaw` release changes that file layout, re-verify the Dockerfile `inject-clawdeez-gateway-bootstrap.py` step still runs cleanly.

### Verify

1. Open `https://<your-service>.up.railway.app` (or your custom domain) at the Control UI path (e.g. `/chat` if that is how you reach the UI for your build).
2. Confirm there is **no** `origin not allowed` message and the dashboard loads.
3. If you still see an origin error, check the URL bar: `http` vs `https` must match an entry in `allowedOrigins`, and the hostname must match exactly (including custom domain vs `*.up.railway.app`).

### ClawDeez / provisioned domains

If ClawDeez (or another tool) provisions a Railway public hostname automatically, pass that same hostname into this template as **`OPENCLAW_PUBLIC_ORIGIN`** (or ensure **`RAILWAY_PUBLIC_DOMAIN`** matches the URL users open) so the allowlist stays aligned with the browser URL.

When using [clawdeez-core](https://github.com/gtopolice/clawdeez-core) provisioning, new services get **`OPENCLAW_CONTROL_UI_DISABLE_DEVICE_AUTH=1`** by default (token-only Control UI). Set backend **`PROVISION_OPENCLAW_DISABLE_CONTROL_UI_DEVICE_AUTH=0`** to **skip** that injection and require device pairing instead.

### Assistant workspace context (`AGENTS.md`)

On each container start (after `openclaw onboard` and the origin patch), the entrypoint **idempotently appends** a short **ClawDeez / Railway** section to **`AGENTS.md`** in the workspace (`OPENCLAW_WORKSPACE_DIR`, default `/data/workspace`). OpenClaw loads workspace bootstrap files into the assistant system prompt ([system prompt docs](https://docs.openclaw.ai/concepts/system-prompt)), so the model can answer “where are you hosted?” accurately instead of generic refusals.

The block includes **`OPENCLAW_PUBLIC_ORIGIN`** or **`RAILWAY_PUBLIC_DOMAIN`** when set. To refresh wording after an image upgrade, remove the HTML comment markers `<!-- clawdeez-hosting-context -->` (both) from `AGENTS.md` on the volume and redeploy once.

### License and attribution

OpenClaw is a separate project; follow its license for the CLI/runtime you install in the image. This repository is the **ClawDeez** Railway wrapper (Dockerfile, entrypoint, and origin patch). Do not imply endorsement by the OpenClaw project unless you have it.
