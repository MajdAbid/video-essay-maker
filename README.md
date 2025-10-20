# Video Essay Maker

Video Essay Maker is a lightweight workflow that turns a topic into a narrated video by combining an LLM-generated script, a transcript tailored for text-to-speech, Kokoro narration, and a simple static video render.

## Components
- **FastAPI backend** providing the REST API and task orchestration.
- **Celery workers** for async script/audio/video generation.
- **React dashboard** to submit topics, review artifacts, and trigger downstream stages.
- **Prometheus Pushgateway** (optional) for basic metrics.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
npm install --prefix frontend
```

Start the services (requires Redis running locally):
```bash
# terminal 1 - API
uvicorn backend.app.main:app --reload

# terminal 2 - Celery worker
CELERY_BROKER_URL=redis://localhost:6379/0 DATABASE_URL=sqlite+aiosqlite:///./jobs.db SYNC_DATABASE_URL=sqlite:///./jobs.db celery --app backend.app.tasks.celery_app worker --loglevel=INFO --pool=solo

# terminal 3 - frontend dashboard
npm run dev --prefix frontend
```

Visit the dashboard at http://localhost:3000 and set the backend token in `frontend/.env.local` if needed.

## Optional YouTube research
To ground the script with recent videos, enable the YouTube integration:
1. Copy `credentials.template.json` to `credentials.json` and fill in your OAuth client details.
2. Set `ENABLE_YOUTUBE_RESEARCH=true` in `.env`.
3. Restart the API and worker; successful authentication is logged once.

If credentials are missing, the pipeline falls back to LLM-only context automatically.

## Project layout
```
backend/    FastAPI app and Celery tasks
worker/     Worker Dockerfile and scripts
frontend/   React dashboard
prometheus/ Sample scrape config
prompts/    Prompt templates for the LLM stages
```

## Housekeeping
- Generated artifacts live under `data/jobs/<job_id>/`.
- Copy `credentials.template.json` rather than committing real credentials.
- Use the provided `.gitignore` to exclude virtual environments, node_modules, and job outputs.

## License
MIT
