# GRIT — Backend API

Production-minded backend for **GRIT**, a discipline / progress-tracking platform:
habits, goals, roadmaps, streaks, XP & levels, achievements, leaderboards, an AI
mentor (**ATLAS**), and notifications.

Built with **FastAPI (async)** + **PostgreSQL/SQLAlchemy 2.0** + **Celery/Redis**,
fully typed (mypy strict), layered `routers → services → repositories`, and
test-covered (92 tests).

## Stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.12, type hints everywhere |
| API | FastAPI (async) + Uvicorn, OpenAPI at `/docs` |
| DB | PostgreSQL via SQLAlchemy 2.0 async + Alembic |
| Schemas | Pydantic v2 (separate from ORM models) |
| Auth | JWT access/refresh (python-jose) + argon2 (passlib) |
| Background | Redis + Celery worker + Celery Beat |
| Tests | pytest + pytest-asyncio + httpx.AsyncClient (run on in-memory SQLite) |
| Tooling | uv, ruff (lint+format), mypy (strict), Docker Compose |

## Architecture

```
app/
  core/        config, security (JWT/argon2), errors, time (zoneinfo), deps
  db/          async session (API) + a SEPARATE sync session (Celery/seed)
  models/      SQLAlchemy ORM (18 tables) — see app/models/
  schemas/     Pydantic v2 request/response models
  repositories/  thin SQLAlchemy data access
  services/    business logic. PURE, DB-free modules are unit-tested in isolation:
               gamification (level/XP math), streaks (recompute/freeze/evolution),
               perfect_day, roadmap_import (markdown parser), mentor (ATLAS copy),
               habit_schedule. DB orchestration: scoring, habits, goals, roadmaps,
               achievements, community, notifications.
  routers/     FastAPI routers — NO business logic
  workers/     celery_app (Beat schedule), schedules (pure sweep logic), tasks (sync)
scripts/seed.py  demo user "Jordan Reyes"
```

**Key design rules**

- All XP/score math is integer-only; `level` is **derived** from `xp_total`, never stored.
- All timestamps are timezone-aware UTC. A user's "day" is computed in their stored
  timezone (default `Europe/Berlin`) via `zoneinfo`.
- Streaks are a **cache**; the source of truth is always a recompute from check-in
  history (`services/streaks.py`).
- Check-ins are idempotent per local day (DB `UniqueConstraint(habit_id, local_date)`).
- Celery tasks run **sync** with their own sync session and call the **same pure
  service modules** as the API — no logic duplication.
- Consistent error shape: `{"error": {"code", "message", "details?"}}`.

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build          # postgres + redis + api + worker + beat
# the api service runs `alembic upgrade head` on boot
docker compose exec api uv run python -m scripts.seed   # demo data (optional)
open http://localhost:8000/docs
```

Services started by `docker-compose.yml`: `postgres`, `redis`, `api` (Uvicorn),
`worker` (Celery), `beat` (Celery Beat).

## Local development

```bash
uv sync                            # install deps into .venv

# Start Postgres + Redis however you like (or: docker compose up postgres redis)
export $(grep -v '^#' .env.example | xargs)   # or create your own .env

uv run alembic upgrade head        # apply migrations
uv run python -m scripts.seed      # seed demo data

uv run uvicorn app.main:app --reload          # API → http://localhost:8000/docs
```

### Start the Celery worker and beat (separate terminals)

```bash
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info
uv run celery -A app.workers.celery_app.celery_app beat   --loglevel=info
```

The Beat schedule has a **single** entry: `sweep` every 15 minutes. The sweep
converts the current UTC window to each user's local time and only **enqueues**
idempotent per-user tasks when a local boundary is crossed:

| Local trigger | Task |
| --- | --- |
| ~00:00 | `streak_recompute` (evaluate yesterday) |
| ~20:00 | `streak_protection_check` (if today still open) |
| Sun ~18:00 | `weekly_review` |
| 1st ~00:00 | `monthly_review` |

## Tests, lint, types

```bash
uv run pytest          # 92 tests (unit + integration), no external services needed
uv run ruff check .    # lint
uv run ruff format .   # format
uv run mypy app        # strict type-check
```

Tests run against an in-memory SQLite DB (see `tests/conftest.py`), so no Postgres
or Redis is required. Coverage includes: level/XP math, streak extend/break/freeze,
perfect-day bonus, the markdown roadmap importer, the DSA topic→habit credit flow,
the timezone sweep fan-out, and the auth + check-in-idempotency HTTP flows.

## API surface (`/api/v1`, docs at `/docs`)

- **Auth** — `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`; `GET /me`
- **Habits** — `GET/POST /habits`; `PATCH/DELETE /habits/{id}`;
  `POST /habits/{id}/checkin`, `DELETE /habits/{id}/checkin`;
  `POST /habits/{id}/archive` & `/restore`
- **Goals** — `GET/POST /goals`; `GET/PATCH/DELETE /goals/{id}`;
  `PATCH /goals/{id}/milestones/{mid}`
- **Roadmaps** — `GET/POST /roadmaps`; `GET /roadmaps/{id}`; `POST /roadmaps/import`
  (markdown); `PATCH /roadmaps/{id}/topics/{tid}` (DSA-linked topics credit the
  linked habit for today)
- **Streaks** — `GET /streaks`; `POST /streaks/freeze`
- **Progress** — `GET /xp`, `/level`, `/heatmap?range=weeks|year`,
  `/analytics?period=week|month|year`
- **Achievements** — `GET /achievements` (hidden ones masked until unlocked)
- **Community** — `GET /leaderboard?scope=league|friends|global`;
  `GET/POST /friends`, `POST /friends/{id}/respond`; `GET /challenges`
- **Notifications** — `GET /notifications`, `POST /notifications/{id}/read`,
  `POST /notifications/read-all`
- **Settings** — `GET/PATCH /settings`

## Gamification reference

- **Level thresholds (XP):** 0 / 500 / 1,500 / 4,000 / 9,000 / 18,000 / 35,000 →
  Beginner · Consistent · Focused · Disciplined · Relentless · Elite · Unstoppable.
- **XP:** habit check-in = `habit.xp_value`; goal milestone = 50; roadmap topic = 25;
  perfect-day bonus = 25; achievement unlock = tier bonus.
- **Streak freezes:** +1 per 14 consecutive days (cap 3); a missed day auto-consumes
  a freeze, else the streak breaks. Evolution stage by length: Spark 1–6, Ember 7–20,
  Flame 21–45, Blaze 46–99, Inferno 100–364, Eternal 365+.

## ATLAS mentor

`services/mentor.py` generates mentor copy from a curated, **original** message
library keyed by `(event, tone)` where tone ∈ {gentle, hard, relentless}. A clean
adapter seam (`set_mentor_provider`) lets an LLM provider be swapped in later. No
third-party quotes are used.

## Demo user

`scripts/seed.py` creates **Jordan Reyes** matching the frontend sample: 7 habits
(incl. a DSA-linked "Solve a DSA topic"), the 9 real learning roadmaps parsed from
`progress_tracker/docs`, 4 goals, a **47-day streak**, and **level 5** (9,420 XP).

```
Login: jordan@grit.app / GritDemo123!
```
