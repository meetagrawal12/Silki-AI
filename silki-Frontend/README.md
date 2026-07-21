# Silki AI — Frontend (Phase 3)

A full rewrite against the new backend (see `../silki-backend`). No build
step — plain HTML/CSS/JS, same as the original, but now talking to real
auth and server-side sessions instead of `localStorage`.

## What changed from the previous version

| Problem | Fix |
|---|---|
| Sessions lived in `localStorage`, disconnected from the backend's own store | Sessions are fetched from `GET /sessions` and opened via `GET /sessions/{id}` — one source of truth |
| "Auth" was a username textbox, no password | Real register/login forms hitting `/auth/register` and `/auth/login`, JWT stored and auto-refreshed on 401 |
| Chat waited for the full response before showing anything | `POST /chat/stream` (SSE) — tokens render as they arrive |
| Hand-rolled regex markdown renderer | `marked` + `highlight.js` + `DOMPurify` (sanitized before insertion) |
| Voice button called an endpoint that didn't exist | Wired to the now-implemented `/voice/transcribe` |
| Hardcoded `http://127.0.0.1:8000` | Single `config.js` — set `window.SILKI_API_BASE` before deploying |

## Running it

1. Get the backend running first (see `../silki-backend/README.md`).
2. Edit `config.js` if your backend isn't on `http://127.0.0.1:8000`.
3. Serve this folder with any static server, e.g.:
   ```bash
   python3 -m http.server 8080
   ```
4. Open `http://localhost:8080`. Make sure that origin is in the backend's
   `CORS_ORIGINS`.

## Design

The visual identity is built around the app's name: a single animated
**thread** line is the signature element — it's the typing/loading
indicator, the active-thread marker in the sidebar, and the landing page's
background motif. Palette is ink indigo with a muted gold thread accent
(deliberately not the default AI-generated cream+terracotta or
black+neon look); type is Fraunces (display) over Manrope (UI).

## Files

- `index.html` — landing, auth, and app shell markup
- `style.css` — design system (see the token comment block at the top)
- `config.js` — one place to point at your backend
- `api.js` — all backend calls, JWT storage/refresh, SSE stream parsing
- `app.js` — UI state and DOM logic only

## Known gaps for the next phase

- No code editor (Monaco) yet — that's the "Cursor features" phase.
- No document/RAG upload yet.
- Access tokens are stored in `localStorage` for simplicity; a stricter
  production setup would keep the access token in memory and rely on an
  httpOnly cookie for refresh.
