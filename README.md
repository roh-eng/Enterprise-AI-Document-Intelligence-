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
- [ ] **Week 4 — NLP service**: spaCy/NLTK preprocessing, entities, keywords.
- [ ] **Week 5 — RAG pipeline**: Sentence-Transformers + FAISS + LangChain + Gemini.
- [ ] **Week 6 — Docker, CI**.

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
