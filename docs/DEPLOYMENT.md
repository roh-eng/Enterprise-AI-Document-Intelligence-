# Deployment Guide

## 1. Prerequisites
- Docker + Docker Compose (recommended), **or** Python 3.12 for a local run.
- (Optional) A Google **Gemini API key** for live generation — without it the
  GenAI/RAG features use the offline fallback.

## 2. Configure environment
```bash
cp .env.example .env
```
Edit `.env` and set, at minimum for production:
```ini
JWT_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
ENVIRONMENT=production
DEBUG=false
GEMINI_API_KEY=<optional, enables live Gemini>
```
**Never commit `.env`** — it is git-ignored.

## 3. Run with Docker Compose (recommended)
```bash
docker compose up --build
```
- Frontend → http://localhost:8501
- API docs → http://localhost:8000/docs
- Data (SQLite DB, uploads, FAISS indexes) persists in the `app-data` volume.

Stop / reset:
```bash
docker compose down           # stop
docker compose down -v        # stop + wipe data volume
```

## 4. Run locally without Docker
```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -c "import nltk; [nltk.download(p) for p in ['wordnet','omw-1.4','vader_lexicon','punkt']]"

# Terminal 1 — backend
cd backend && uvicorn app.main:app --reload
# Terminal 2 — frontend
streamlit run frontend/app.py
```

## 5. First-run notes
- The **first user to register becomes the admin** (sees the 🛡️ Admin page).
- The ML classifier auto-trains on first use; to pre-train:
  `cd backend && python -m app.ml.train`.

## 6. Production hardening
| Area | Dev default | Production recommendation |
|------|-------------|---------------------------|
| Database | SQLite (file) | PostgreSQL (`DATABASE_URL=postgresql+psycopg2://…`, add `psycopg2-binary`) |
| Schema | `create_all` on startup | **Alembic** migrations |
| App server | 1 uvicorn worker | `gunicorn -k uvicorn.workers.UvicornWorker -w 4 app.main:app` behind Nginx/TLS |
| Secrets | `.env` file | Secret manager (AWS/GCP/Vault) |
| File storage | local disk volume | Object storage (S3 / GCS) |
| CORS | localhost | your real frontend origin(s) |
| Auth | access tokens | add refresh tokens + rotation/revocation |

### Switching to PostgreSQL
1. Uncomment the `db:` service in `docker-compose.yml`.
2. Add `psycopg2-binary` to `requirements.txt`.
3. Set the backend `DATABASE_URL=postgresql+psycopg2://app:app@db:5432/app`.
4. Introduce Alembic for migrations instead of `create_all`.

## 7. CI/CD
`.github/workflows/ci.yml` runs on every push/PR to `main`/`master`:
- **test** job — installs deps, downloads NLP data, runs the full `pytest` suite.
- **docker-build** job — builds both images to verify the Dockerfiles.

Extend the pipeline with a deploy job (push images to a registry, deploy to your
host/cluster) once a target environment is chosen.
