# GRIT — Backend API

FastAPI backend for **GRIT**, a discipline / progress-tracking platform: habits, goals,
roadmaps, streaks, XP & levels, achievements, leaderboards, AI coaches (the ATLAS mentor +
4 alternate personas), and notifications.

Async FastAPI · PostgreSQL/SQLAlchemy 2.0 · Celery/Redis · fully typed (mypy strict) ·
layered `routers → services → repositories` · ~100 tests.

Frontend lives in [`../grit-web`](../grit-web).

---

## Requirements

- **Python 3.12** and **[uv](https://docs.astral.sh/uv/)** (dependency manager)
- For the full stack: **Docker** (Postgres + Redis), or run them yourself
- For a zero-services quick start: nothing else — uses **SQLite**

---

## First-time setup

```bash
cd grit-backend
uv sync                 # creates .venv and installs everything
cp .env.example .env    # tweak secrets/URLs if you like
```

Then pick **one** of the two ways to run it.

### Option A — Quick start (SQLite, no Docker)

Fastest way to get the API up with demo data. Run on **port 8010** (port 8000 is often
taken; the frontend defaults to 8010).

```bash
export GRIT_DATABASE_URL="sqlite+aiosqlite:///./grit.db"
export GRIT_SYNC_DATABASE_URL="sqlite:///./grit.db"
export GRIT_CORS_ORIGINS="http://localhost:5173"
export GRIT_SECRET_KEY="dev-secret"

uv run alembic upgrade head        # create the schema
uv run python -m scripts.seed      # demo user: jordan@grit.app / GritDemo123!
uv run uvicorn app.main:app --port 8010 --reload
```

Open **http://localhost:8010/docs**.

> Background jobs (Celery worker/beat) need Redis and are optional for API development —
> see Option B.

### Option B — Full stack (Docker: Postgres + Redis + worker + beat)

```bash
docker compose up --build                              # postgres, redis, api, worker, beat
docker compose exec api uv run python -m scripts.seed  # demo data (optional)
```

The `api` service runs `alembic upgrade head` on boot. API at **http://localhost:8010/docs**.

> **Published host ports are chosen to coexist with other services:** API `8010`, Postgres
> `5433`, Redis `6380` — so this stack runs happily alongside a Redis already on `6379` or
> another app on `8000`. (Containers talk to each other internally on the default ports.)
> If `docker compose up` still says *"port is already allocated"*, run the cleanup below.

---

## Subsequent runs

### SQLite (Option A)

```bash
# set the same env vars (or put them in .env), then:
uv run uvicorn app.main:app --port 8010 --reload
```

### Docker (Option B)

```bash
docker compose up            # start everything
docker compose down          # stop
```

### Celery worker + beat (only if you want scheduled jobs; needs Redis running)

```bash
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info
uv run celery -A app.workers.celery_app.celery_app beat   --loglevel=info
```

A single Beat entry runs a `sweep` every 15 minutes that fans out idempotent per-user tasks
(streak recompute at local midnight, streak-protection nudges at ~20:00, weekly/monthly
reviews).

---

## Stopping & cleaning up ports

If a port is "already in use", or you want a clean slate (stale dev servers, a stray Celery
worker, a half-started Docker stack):

```bash
# 1) Stop the Docker stack (if you used Option B)
docker compose down                 # add -v to also wipe the Postgres volume

# 2) Stop a stray Celery worker/beat started by hand
pkill -f 'celery -A app.workers'

# 3) Free the GRIT dev ports (backend 8010, frontend 5173/5174)
for p in 8010 5173 5174; do fuser -k ${p}/tcp 2>/dev/null; done
# (no `fuser`? use:  for p in 8010 5173 5174; do kill $(lsof -ti tcp:$p) 2>/dev/null; done )
```

> These only touch GRIT's own ports. They will **not** stop your existing Redis (`6379`) or
> anything on `8000` — those are intentionally left alone.

---

## Tests, lint, types

```bash
uv run pytest            # ~100 tests (unit + integration), no external services needed
uv run ruff check app    # lint
uv run ruff format app   # format
uv run mypy app          # strict type-check
```

Tests run against in-memory SQLite, so no Postgres/Redis required.

---

## Database migrations (Alembic)

```bash
uv run alembic upgrade head                          # apply latest
uv run alembic revision --autogenerate -m "message"  # create a new migration after model changes
uv run alembic downgrade -1                           # roll back one
```

---

## Configuration

All settings are environment variables prefixed `GRIT_` (see `.env.example`). Most useful:

| Variable | Purpose |
| --- | --- |
| `GRIT_DATABASE_URL` | Async DB URL (`postgresql+asyncpg://…` or `sqlite+aiosqlite:///…`) |
| `GRIT_SYNC_DATABASE_URL` | Sync URL for Alembic + Celery (`postgresql+psycopg://…` / `sqlite:///…`) |
| `GRIT_SECRET_KEY` | JWT signing key |
| `GRIT_CORS_ORIGINS` | Comma-separated allowed origins (e.g. `http://localhost:5173`) |
| `GRIT_REDIS_URL` / `GRIT_CELERY_*` | Redis / Celery broker + backend |
| `GRIT_DEFAULT_TIMEZONE` | Default user timezone (`Europe/Berlin`) |

---

## API surface (`/api/v1`, docs at `/docs`)

Auth (register/login/refresh/logout, `GET/PATCH /me`) · Onboarding (`POST /onboarding`) ·
Habits (CRUD + idempotent check-in/undo + archive/restore) · Goals (CRUD + milestones) ·
Roadmaps (CRUD + markdown `import` + topic toggle with DSA-habit credit) · Streaks
(`GET` + `freeze`) · Progress (`xp`, `level`, `heatmap`, enriched `analytics`) · Achievements ·
Community (leaderboard scopes, friends, challenges) · Notifications · Settings (theme, accent,
mentor tone, **coach persona**, quiet hours, per-type toggles).

## Demo user

`scripts/seed.py` creates **Jordan Reyes** matching the frontend sample: 7 habits (incl. a
DSA-linked one), the 9 learning roadmaps from `docs/`, 4 goals, a **47-day streak**, **level 5**.

```
Login: jordan@grit.app / GritDemo123!
```
