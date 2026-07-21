# Silki AI — Backend (Phase 2: Foundations)

A layered rewrite of the original single-file `main.py`. Same Groq +
HuggingFace free-tier stack, but with persistent storage, real auth, and a
structure that the rest of the roadmap (RAG, image studio, code workspace,
etc.) can be built on without another rewrite.

## What changed from the previous version

| Problem | Fix |
|---|---|
| Sessions lived in an in-memory `dict`, lost on every restart | SQLite (via async SQLAlchemy) — swap to Postgres later by changing one env var |
| No auth — `session_id` was a guessable string anyone could read/write | JWT-based auth; every session is scoped to `user_id`, verified on every request |
| `ACTIVE_MODEL` was a global variable mutated by every request (race condition) | Model selection is now request-scoped, returned as part of each result |
| Frontend called `/voice/transcribe`, which never existed | Implemented via HF's free ASR inference API |
| `CORS allow_origins=["*"]` with credentials enabled | Restricted to an explicit allow-list via `CORS_ORIGINS` |
| No streaming | Added `POST /chat/stream` (Server-Sent Events) alongside the original non-streaming `POST /chat` |
| Everything in one 300-line file | Split into `routers/ → services/ → repositories/ → models/`, each with one job |
| No rate limiting | `slowapi`, per-route limits configurable in `.env` |

## Project layout

```
app/
  core/        # config, JWT/password helpers, auth dependency
  db/          # async SQLAlchemy engine + session factory
  models/      # ORM tables: User, ChatSession, Message
  schemas/     # Pydantic request/response contracts
  repositories/# raw DB queries only, no business logic
  services/    # business logic: auth, LLM (Groq), image (HF), voice (HF)
  routers/     # HTTP endpoints — thin, delegate to services
  middleware/  # rate limiter
  main.py      # wires it all together
```

## Running it

```bash
cp .env.example .env        # then fill in GROQ_API_KEY, HF_TOKEN, SECRET_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive API docs.

## API summary

- `POST /auth/register`, `/auth/login`, `/auth/refresh`, `GET /auth/me`
- `POST /chat` — non-streaming, returns full reply
- `POST /chat/stream` — Server-Sent Events, one `token` event per chunk, ends with a `done` event
- `GET/PATCH/DELETE /sessions`, `/sessions/{id}` — all scoped to the authenticated user
- `POST /images/generate`, `/images/enhance-prompt`
- `POST /voice/transcribe` — multipart audio upload

All endpoints except `/auth/register`, `/auth/login`, `/auth/refresh`, and
`/health` require `Authorization: Bearer <access_token>`.

## Notes for the frontend rewrite (next phase)

- The old `localStorage`-based session store needs to go — sessions now live
  server-side per user. The frontend should call `GET /sessions` on load
  instead of reading local storage.
- `/chat/stream` uses SSE (`text/event-stream`), not WebSockets — a plain
  `fetch` + `ReadableStream` reader works, no extra library needed.
- The frontend's fake "type a username to log in" flow needs to become a
  real `/auth/register` + `/auth/login` form, storing the JWT (e.g. in
  memory + a secure httpOnly refresh flow, not raw `localStorage` for the
  access token if this becomes a production deployment).

## Tested

Registration, duplicate-username/email rejection, weak-password rejection,
login success/failure, JWT-protected routes (401 without/with-invalid
token), and cross-user session isolation (user B gets 404, not another
user's data, when requesting user A's session id) were all exercised
end-to-end against a real SQLite database as part of building this.
