# Gym Diary

> A product-ready workout intelligence platform built with Flask, SQLite, and a modern multi-page frontend.
>
> **Gym Diary helps users plan smarter, train consistently, and track progression with confidence** — while staying lightweight enough for rapid iteration and founder-led shipping.

---

## Table of Contents

- [Vision](#vision)
- [Why This Product Matters](#why-this-product-matters)
- [Who This Is For](#who-this-is-for)
- [Product Highlights](#product-highlights)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Tech Stack](#tech-stack)
- [Core Domain Model](#core-domain-model)
- [Feature Walkthrough](#feature-walkthrough)
- [API Reference](#api-reference)
- [Frontend Pages](#frontend-pages)
- [Project Structure](#project-structure)
- [Local Development Setup](#local-development-setup)
- [Environment Variables](#environment-variables)
- [Security & Reliability Notes](#security--reliability-notes)
- [Deployment Notes](#deployment-notes)
- [Product & Engineering Roadmap Ideas](#product--engineering-roadmap-ideas)
- [Contributing](#contributing)
- [License](#license)

---

## Vision

Gym Diary is designed as a **performance-focused training companion** that bridges the gap between:

- beginner-friendly workout apps (easy onboarding), and
- serious progression tooling (structured splits + granular set tracking).

The product is intentionally opinionated around **consistency, progression, and clarity**:

- Users don’t just log workouts — they follow a structured plan.
- Training days adapt to real activity history, not just weekday labels.
- The experience is optimized for practical gym usage: fast logging, quick edits, and immediate feedback.

---

## Why This Product Matters

Most fitness users fall off because of one of three issues:

1. no clear training structure,
2. friction while logging,
3. no trustworthy view of progression.

Gym Diary addresses all three with:

- **preset split templates** for instant guidance,
- **custom split creation** for advanced users,
- **set-level workout logging** for true progression analysis,
- **session continuity logic** that keeps users anchored to the right training day.

From an investor or founder perspective, this architecture supports multiple growth paths:

- freemium personalization,
- coach/client dashboards,
- analytics subscriptions,
- AI-assisted programming.

---

## Who This Is For

### End Users
- Lifters who want a clean training log with structure.
- Busy professionals who need a fast gym workflow.
- Intermediate athletes progressing through split-based programs.

### Hiring Managers / Teams
- Demonstrates full-stack delivery across auth, API design, relational modeling, and UI integration.
- Shows practical product thinking (retention-oriented flows, robust data ownership checks).

### Founders / Operators
- Lean architecture with clear extension points.
- Low operational overhead baseline (Flask + SQLite).
- Straightforward migration path to production-grade managed DBs and services.

---

## Product Highlights

- **JWT Authentication** with account creation, login, profile read/update.
- **Split System** with both preset templates and custom plans.
- **Single Active Split** model to simplify “today’s workout” decisions.
- **Exercise Management** per split day (add/delete).
- **Workout Logging** at set granularity (reps, weight, notes, set number).
- **Adaptive “Today” Engine** that advances by training progression.
- **History Endpoints** by date and by exercise.
- **Theme & UI Preferences** persisted client-side (accent color, radius, compact mode, theme).

---

## Architecture at a Glance

```text
Frontend (HTML templates + /static/api.js)
        |
        | HTTPS / JSON
        v
Flask App (app.py)
  ├── /api/auth    (routes/auth.py)
  ├── /api/splits  (routes/splits.py)
  └── /api/logs    (routes/logs.py)
        |
        v
SQLAlchemy Models (models.py)
        |
        v
SQLite (default) or DATABASE_URL target
```

Design principles:

- **Clear bounded route modules** (auth/splits/logs).
- **Ownership checks** on protected resources (user can only mutate their own data).
- **Incremental schema resilience** via lightweight update helper for SQLite.

---

## Tech Stack

### Backend
- Flask
- Flask-JWT-Extended
- Flask-SQLAlchemy
- Flask-Bcrypt
- Flask-CORS
- python-dotenv

### Database
- SQLite by default (`sqlite:///app.db`)
- Configurable via `DATABASE_URL`

### Frontend
- Server-rendered template pages
- Vanilla JavaScript API client (`statics/api.js`)
- LocalStorage-backed preference management

### Runtime / Deploy
- Gunicorn-ready app factory pattern
- `Procfile` and `runtime.txt` included for PaaS-style deployments

---

## Core Domain Model

Gym Diary uses a normalized relational model centered around program structure and logged performance:

- **User** → owns many workout splits.
- **WorkoutSplit** → contains multiple split days; exactly one may be active per user.
- **SplitDay** → defines a day label (e.g., Push/Pull/Legs/Rest).
- **Exercise** → template exercise under a split day.
- **WorkoutLog** → real-world set entry (date, reps, weight, notes).

This separation between **template entities** (split/day/exercise) and **event entities** (workout logs) enables future analytics and coaching features without redesigning core schema.

---

## Feature Walkthrough

### 1) Authentication & Profile
- Username availability checks.
- Signup + immediate JWT issuance.
- Login via username (email fallback supported).
- `/me` profile retrieval.
- `/me` profile updates: username, email, password, avatar URL, motivation note.

### 2) Training Split Management
- Browse preset libraries (Push Pull Legs, Upper/Lower, Bro Split).
- Clone a preset into the user account.
- Create fully custom splits via API payload.
- Activate one split (auto-deactivate others).
- Delete splits safely by owner.

### 3) Exercise Management
- Add custom exercise to a split day.
- Preserve display order through `order_index` sequencing.
- Delete exercises with ownership validation.

### 4) Workout Logging
- Log one or multiple sets in one request.
- Optional custom workout date (`YYYY-MM-DD`).
- Edit and delete individual log entries.

### 5) Smart “Today” Session Logic
- Returns the current training day from the active split.
- If user already logged today, keeps that same day open for continuity.
- Otherwise rotates to the next training day based on last logged training day.
- Excludes rest-only days from the training progression loop.

### 6) Historical Insights Surface
- Retrieve full logs for a given date.
- Retrieve full history for a specific exercise grouped by date.

---

## API Reference

> Base URL: `/api`

### Auth
- `GET /auth/check-username?username=...`
- `POST /auth/signup`
- `POST /auth/login`
- `GET /auth/me` *(JWT required)*
- `PATCH /auth/me` *(JWT required)*

### Splits
- `GET /splits/presets`
- `POST /splits/presets/<preset_key>` *(JWT required)*
- `POST /splits/` *(JWT required)*
- `GET /splits/` *(JWT required)*
- `GET /splits/<split_id>` *(JWT required)*
- `PATCH /splits/<split_id>/activate` *(JWT required)*
- `DELETE /splits/<split_id>` *(JWT required)*
- `POST /splits/days/<day_id>/exercises` *(JWT required)*
- `DELETE /splits/exercises/<exercise_id>` *(JWT required)*

### Logs
- `POST /logs/` *(JWT required)*
- `GET /logs/today` *(JWT required)*
- `GET /logs/date/<YYYY-MM-DD>` *(JWT required)*
- `GET /logs/exercise/<exercise_id>` *(JWT required)*
- `PATCH /logs/<log_id>` *(JWT required)*
- `DELETE /logs/<log_id>` *(JWT required)*

---

## Frontend Pages

- `/` or `/index` — Authentication entry page.
- `/dashboard` — Primary logged-in training surface.
- `/splits` — Split selection and management.
- `/analytics` — Historical workout analytics view.
- `/profile` — User profile customization.
- `/settings` — Theme and UI preferences.
- `/about`, `/terms`, `/privacy` — informational/legal pages.

---

## Project Structure

```text
Gym_diary/
├── app.py
├── models.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── routes/
│   ├── auth.py
│   ├── splits.py
│   └── logs.py
├── statics/
│   └── api.js
└── templates/
    ├── index.html
    ├── dashboard.html
    ├── splits.html
    ├── analytics.html
    ├── profile.html
    ├── settings.html
    ├── about.html
    ├── terms.html
    └── privacy.html
```

---

## Local Development Setup

### 1) Clone and enter project
```bash
git clone <your-repo-url>
cd Gym_diary
```

### 2) Create virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

### 4) Configure environment
Create a `.env` file:

```env
JWT_SECRET_KEY=replace_with_a_long_random_secret
DATABASE_URL=sqlite:///app.db
CORS_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
FLASK_ENV=development
```

### 5) Run the app
```bash
python app.py
```

Then open: `http://127.0.0.1:5000/`

---

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | ✅ Yes | JWT signing secret; app refuses to start without it. |
| `DATABASE_URL` | Optional | SQLAlchemy database connection (defaults to SQLite). |
| `CORS_ORIGINS` | Optional | Comma-separated allowlist for `/api/*` requests. |
| `FLASK_ENV` | Optional | Enables debug mode when set to `development`. |

---

## Security & Reliability Notes

- Passwords are hashed with Bcrypt before storage.
- Protected endpoints require JWT bearer tokens.
- Resource ownership checks prevent cross-account data access.
- CORS is scoped to `/api/*` with explicit allowed headers/methods.
- SQLite schema compatibility helper applies safe column additions for local evolution.
- App initializes tables at startup for reduced setup friction.

> Production recommendation: rotate secrets, enforce HTTPS, and pin strict CORS origins.

---

## Deployment Notes

This repository is aligned with straightforward PaaS deployment workflows:

- `Procfile` for process declaration.
- `runtime.txt` for runtime pinning.
- `DATABASE_URL` support for managed databases.
- App factory pattern compatibility with WSGI servers.

Suggested production upgrades:

- Move from SQLite to PostgreSQL.
- Add migration tooling (Alembic/Flask-Migrate).
- Add rate limiting and observability.
- Add refresh token lifecycle and token revocation strategy.

---

## Product & Engineering Roadmap Ideas

### Product
- Coach mode (multi-user dashboards).
- Goal systems (strength, hypertrophy, consistency KPIs).
- Habit nudges and missed-session recovery plans.
- Social accountability circles.

### Engineering
- Test suite (unit + integration + API contract tests).
- OpenAPI specification and SDK generation.
- Event-based analytics pipeline.
- Fine-grained role/permission model.
- Progressive Web App support.

---

## Contributing

Contributions are welcome from developers, designers, and product-minded collaborators.

Recommended contribution flow:

1. Fork repository.
2. Create a focused feature branch.
3. Keep commits atomic and well-described.
4. Open a PR with architecture notes and screenshots (if UI changes).

---

## License

No license file is currently defined in this repository.
If this project is intended for open collaboration, add an explicit license (MIT, Apache-2.0, etc.).

---

### Closing Note

Gym Diary is intentionally built as a **practical, extensible foundation**:

- lean enough for rapid founder iteration,
- strong enough for serious training workflows,
- clear enough for teams to onboard quickly.

If you're an investor, founder, engineer, or hiring team evaluating this project: this codebase demonstrates both **product intuition** and **execution discipline**.
