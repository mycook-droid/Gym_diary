# Gym Diary

Minimal workout tracking app (Flask + SQLite + HTML/CSS/JS).

## Current Structure (Safe for your existing paths)

- `app.py`, `models.py`, `routes/` -> backend API
- `index.html`, `dashboard.html`, `splits.html`, `analytics.html`, `profile.html`, `settings.html`, `about.html`, `terms.html`, `privacy.html` -> frontend pages
- `api.js` -> shared frontend API client + app settings

This flat structure is intentional right now so existing relative links and script paths keep working.

## Run Locally

```bash
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python app.py
```

Then open frontend using your local static server (for example VS Code Live Server).

### API base and CORS configuration

- Frontend defaults to same-origin API calls (`/api`) in production.
- Optional frontend override:
  - set `window.API_BASE` before loading `/static/api.js` (example: `http://127.0.0.1:5000/api` for local-only testing).
- Backend CORS origins are read from `CORS_ORIGINS` (comma-separated).
  - If not set, localhost development origins are used.
- Database tables are initialized at app startup (including Gunicorn/Render) via `db.create_all()`.

## Publish Readiness Checklist

1. Keep `.env` out of Git.
2. Keep `instance/`, `*.db`, and `__pycache__/` out of Git.
3. Set a strong `JWT_SECRET_KEY` in production.
4. Turn off Flask debug mode in production.
5. Add HTTPS and domain-specific CORS origins.

## Future Reorganization (Optional, after launch)

When you are ready, move to:

- `templates/` for HTML
- `static/js/` for `api.js`
- optional `static/css/` for shared styling

Do this only in one dedicated refactor pass, because it requires updating all relative links and serve paths.
