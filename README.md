# OpenClaw (Railway template)

This template runs the [OpenClaw](https://docs.openclaw.ai/) gateway on [Railway](https://railway.app/) with persistent `/data` and binds the gateway on all interfaces so the public URL works.

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

If none of the origin-related variables yield an origin, the patch step still runs when `OPENCLAW_CONTROL_UI_DISABLE_DEVICE_AUTH` is enabled (origins-only merge is skipped in that case).

### Control UI device pairing vs gateway token

OpenClaw uses two layers: **gateway token** (secret) and **device pairing** (first browser connect must be approved on the gateway host, e.g. `openclaw devices approve <id>`). If your users see **“pairing required”** after pasting the correct token, either approve the device once via Railway **Shell** on that service, or set **`OPENCLAW_CONTROL_UI_DISABLE_DEVICE_AUTH=1`** on the Railway service and **redeploy** so the startup patch applies.

### Gateway token (Control UI login)

- If the gateway has **no** token configured, the “Gateway token” field in the Control UI can be left empty.
- If **`OPENCLAW_GATEWAY_TOKEN`** is set in Railway (or `gateway.auth.token` is set in config), the gateway expects that token — **paste the same value** into the Control UI. Mismatch or omission will fail authentication.

### Verify

1. Open `https://<your-service>.up.railway.app` (or your custom domain) at the Control UI path (e.g. `/chat` if that is how you reach the UI for your build).
2. Confirm there is **no** `origin not allowed` message and the dashboard loads.
3. If you still see an origin error, check the URL bar: `http` vs `https` must match an entry in `allowedOrigins`, and the hostname must match exactly (including custom domain vs `*.up.railway.app`).

### ClawDeez / provisioned domains

If ClawDeez (or another tool) provisions a Railway public hostname automatically, pass that same hostname into this template as **`OPENCLAW_PUBLIC_ORIGIN`** (or ensure **`RAILWAY_PUBLIC_DOMAIN`** matches the URL users open) so the allowlist stays aligned with the browser URL.

When using [clawdeez-core](https://github.com/gtopolice/clawdeez-core) provisioning, set backend **`PROVISION_OPENCLAW_DISABLE_CONTROL_UI_DEVICE_AUTH=1`** to inject **`OPENCLAW_CONTROL_UI_DISABLE_DEVICE_AUTH=1`** on every new agent service (optional).
