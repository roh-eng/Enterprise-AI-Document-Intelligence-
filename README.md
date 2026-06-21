# 🧠 AI Document Intelligence Platform

A production-quality platform that combines **classical Machine Learning**,
**NLP**, **deep-learning embeddings**, and **Generative AI (RAG)** behind a
clean FastAPI backend and a professional Streamlit frontend.

> Built step-by-step following clean architecture and software-engineering best
> practices (type hints, logging, error handling, env-driven config, tests,
> Docker).

---

## 🏛️ Architecture

```
┌────────────────────┐        HTTP/JSON        ┌──────────────────────────┐
│  Streamlit Frontend│  ───────────────────▶   │     FastAPI Backend      │
│  (presentation)    │  ◀───────────────────   │  (API + business logic)  │
└────────────────────┘                         └────────────┬─────────────┘
                                                            │
                        ┌───────────────────────────────────┼───────────────────────────┐
                        │                                   │                           │
                  ┌─────▼─────┐                      ┌──────▼──────┐             ┌───────▼───────┐
                  │  ML / NLP │                      │  RAG / GenAI│             │  SQLAlchemy   │
                  │ services  │                      │  services   │             │  + SQLite/PG  │
                  └───────────┘                      └─────────────┘             └───────────────┘
```

### Layered (clean) architecture
| Layer | Responsibility | Location |
|-------|----------------|----------|
| **Presentation** | UI, user input/output | `frontend/` |
| **API** | HTTP routing, request/response validation | `backend/app/api/` |
| **Service** | Business logic (ML, NLP, RAG) | `backend/app/services/` |
| **Data** | ORM models, persistence | `backend/app/db/` |
| **Core** | Config, logging, cross-cutting concerns | `backend/app/core/` |

---

## 📂 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── core/          # config (env vars) + logging
│   │   ├── db/            # SQLAlchemy base, session, ORM models
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── api/routes/    # FastAPI routers (per feature)
│   │   ├── services/      # ML / NLP / RAG business logic
│   │   ├── ml/            # model training + artifacts
│   │   └── main.py        # FastAPI app entrypoint
│   └── tests/             # pytest suite
├── frontend/              # Streamlit app
├── data/                  # SQLite DB + FAISS index (git-ignored)
├── logs/                  # rotating log files (git-ignored)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quickstart

```bash
# 1. Create & activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # (needed from Step 3 onward)

# 3. Configure environment
cp .env.example .env            # then edit .env (add GEMINI_API_KEY)

# 4. Run the backend (from the backend/ directory)
cd backend
uvicorn app.main:app --reload

# 5. Open the API docs
#    http://localhost:8000/docs
```

---

## 🧩 Build Roadmap
- [x] **Week 1 — Foundation & Auth**: structure, config, logging, SQLite + SQLAlchemy
  models, JWT auth (register/login), password hashing, Streamlit login + dashboard +
  upload page, tests.
- [x] **Week 2 — Document Upload System**: PDF/DOCX/TXT upload, on-disk file storage,
  text extraction + cleaning, upload history, document detail, delete, ownership
  enforcement, exception handling, 15 tests.
- [x] **Week 3 — ML Module**: document classification (Resume/Invoice/Legal/Medical/
  Research), TF-IDF, LogReg + RandomForest + XGBoost comparison, full metrics +
  confusion matrix, save/load best model (joblib), predict uploaded docs with
  confidence, 23 tests.
- [x] **Week 4 — NLP Module**: tokenization, stopword removal, lemmatization,
  spaCy NER, TF-IDF keyword extraction, sentence embeddings, cosine + document
  similarity, NLTK-VADER sentiment, NLP dashboard, 29 tests.
- [x] **Week 5 — Generative AI**: Gemini integration (maintained `google-genai`
  SDK), summary / explain / FAQ / interview-questions / action-items / deadlines,
  system+safety+user prompt engineering, response caching, cost controls,
  offline fallbacks, 39 tests.
- [x] **Week 6 — RAG System**: LangChain chunking, sentence-transformers
  embeddings, FAISS vector index, semantic retrieval, grounded chat with source
  citations, conversation history, Gemini answer generation with offline
  fallback, 46 tests.
- [x] **Week 7 — Professional Dashboard**: analytics service (upload /
  classification / sentiment / search stats), charted Streamlit dashboard,
  document management page, admin dashboard (first-user-admin + role-gated),
  dark theme, premium CSS, responsive layout, 52 tests.
- [x] **Week 8 — Production Deployment**: Dockerized backend + frontend, Docker
  Compose, GitHub Actions CI/CD, unit + API tests (63 total), deployment guide,
  Mermaid diagrams (architecture/flow/sequence/ER), and the interview/resume pack.

✅ **All 8 weeks complete** — 63 passing tests, 9 commits.

## 🚢 Deploy (Docker Compose)
```bash
cp .env.example .env          # set JWT_SECRET_KEY (+ optional GEMINI_API_KEY)
docker compose up --build
# Frontend → http://localhost:8501   ·   API docs → http://localhost:8000/docs
```
Full instructions, PostgreSQL switch, and production hardening:
**[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

## 📚 Documentation
- **[docs/DIAGRAMS.md](docs/DIAGRAMS.md)** — architecture, data-flow, sequence (RAG), and ER diagrams.
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — deploy + production hardening guide.
- **[docs/INTERVIEW.md](docs/INTERVIEW.md)** — resume bullet, STAR stories, HR + technical talking points, future work.
- **[docs/SCREENSHOTS.md](docs/SCREENSHOTS.md)** — screenshot capture guide.

## 🧪 Tests & CI
```bash
cd backend && pytest          # 63 tests: unit + API integration (in-memory DB)
```
GitHub Actions (`.github/workflows/ci.yml`) runs the suite and builds both Docker
images on every push/PR to `main`/`master`.

## 📊 Analytics & Admin (Week 7)
- `GET /analytics/me` — per-user KPIs + distributions (uploads-by-date, file
  types, categories, sentiment) + recent search/upload history. Sentiment is
  computed on the fly (VADER) so no extra column/migration is needed.
- `GET /analytics/admin` — platform-wide stats (users, documents, docs-per-user,
  category/file-type mix). **Role-gated**: the *first registered user* becomes
  admin (no hard-coded credentials); others get 403.

**UI**: dark theme via `.streamlit/config.toml` (users can switch in Settings),
gradient hero + elevated metric cards via injected CSS, responsive `st.columns`
chart grid, and a sidebar that only shows the 🛡️ Admin page to admins.

## 💬 RAG System (Week 6)
```
document → chunk (LangChain) → embed (sentence-transformers) → FAISS index
question → embed → FAISS search (top-k) → build cited context → Gemini → grounded answer
```
Chunk text lives in the DB (source of truth); FAISS (`IndexFlatIP` on normalised
vectors = cosine) holds the vectors, persisted per document. Retrieval degrades
to in-memory cosine if FAISS/sentence-transformers are absent.

**Endpoints** (auth + ownership enforced):
`POST /documents/{id}/index`, `POST /documents/{id}/chat` (answer + citations),
`GET /documents/{id}/chat/history`, `DELETE /documents/{id}/chat/history`.

> Every answer cites the passages it used. When `GEMINI_API_KEY` is unset, an
> extractive fallback still answers *and cites its source* — RAG's core promise.

## ✨ Generative AI Module (Week 5)
One endpoint, six tasks, two input sources (text or stored document):

`POST /genai/generate { task, text | document_id }` where task ∈
`summary · explain · faq · interview_questions · action_items · deadlines`.
`GET /genai/status` reports whether live Gemini is configured.

**Prompt engineering** ([prompts.py](backend/app/genai/prompts.py)): a **system**
prompt (persona), a **safety** prompt (grounding + injection defence), and
per-task **user** prompts with explicit output formats for reliable parsing.

**Cost optimization**: input trimming (`GENAI_MAX_INPUT_CHARS`), per-task
output-token caps, a low-temperature cheap model (`gemini-2.0-flash`), and a
hash-keyed **response cache** so identical requests never pay twice.

**Resilience**: when no `GEMINI_API_KEY` is set (or the API fails), every task
falls back to an offline NLP implementation (extractive summary, regex
deadlines, heuristic action items, etc.) so the feature always returns output.

## 🧬 NLP Module (Week 4)
Every technique prefers the real library and **degrades gracefully** to an
offline implementation, so the app always runs:

| Technique | Primary | Fallback |
|-----------|---------|----------|
| Tokenization | spaCy | regex |
| Lemmatization | spaCy / NLTK WordNet | suffix rules |
| NER | spaCy (`en_core_web_sm`) | regex heuristics |
| Keyword extraction | TF-IDF (sklearn) | frequency |
| Sentence embeddings | sentence-transformers | TF-IDF vectors |
| Sentiment | NLTK VADER | lexicon + negation |

**Endpoints** (auth required): `POST /nlp/analyze` (text), `POST /nlp/similarity`
(two texts), `POST /documents/{id}/analyze`, `GET /documents/{id}/similar`.

> Setup for full models: `python -m spacy download en_core_web_sm` and
> `python -c "import nltk; [nltk.download(p) for p in ['wordnet','omw-1.4','vader_lexicon','punkt']]"`.
> Embeddings use sentence-transformers if installed, else a TF-IDF fallback.

## 🤖 ML Classification (Week 3)
Pipeline: `text → preprocess → TF-IDF (1–2 grams) → classifier`. Three models are
trained and compared; the best (by macro-F1) is persisted and served.

| Model | Accuracy | Precision | Recall | F1 |
|-------|---------:|----------:|-------:|----:|
| LogisticRegression | 0.976 | 0.977 | 0.976 | 0.976 |
| **RandomForest (best)** | **0.992** | **0.992** | **0.992** | **0.992** |
| XGBoost | 0.952 | 0.953 | 0.952 | 0.952 |

> 15% label noise is injected into the **training** set only (test stays clean),
> so the task is non-trivial — RandomForest wins because bagging is most robust
> to noisy labels. Retrain anytime with `python -m app.ml.train`.

**ML endpoints** (all require auth): `POST /ml/classify` (text),
`POST /documents/{id}/classify` (stored doc → persists category + confidence),
`GET /ml/model-info`.

## 📑 Document API (Week 2)
| Method | Path | Purpose | Codes |
|--------|------|---------|-------|
| POST | `/documents/upload` | Upload PDF/DOCX/TXT → extract, clean, store | 201, 400, 413, 415, 422 |
| GET | `/documents` | Upload history (newest first) | 200 |
| GET | `/documents/{id}` | Document metadata + cleaned text | 200, 404 |
| DELETE | `/documents/{id}` | Delete document (DB row + stored file) | 204, 404 |

All require `Authorization: Bearer <token>`. Files are stored at
`data/uploads/<user_id>/<uuid>__<filename>` and are deleted alongside their DB row.

## 🔑 Authentication flow (Week 1)
```
register ─POST /auth/register─▶ user stored (bcrypt hash)
login    ─POST /auth/login────▶ JWT access token (HS256, 60 min)
request  ─Authorization: Bearer <token>─▶ get_current_user ─▶ protected route
```

## 🧪 Running tests
```bash
cd backend
pytest                 # 7 tests: auth + upload, in-memory SQLite
```

## 🖥️ Running the frontend
```bash
# terminal 1 — backend
cd backend && uvicorn app.main:app --reload
# terminal 2 — frontend
streamlit run frontend/app.py        # opens http://localhost:8501
```

---

## ⚙️ Tech Stack
Python · FastAPI · Streamlit · SQLAlchemy · SQLite/PostgreSQL · scikit-learn ·
XGBoost · NLTK · spaCy · Sentence-Transformers · LangChain · FAISS · Gemini ·
Docker · Git.
