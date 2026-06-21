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
- [x] **Step 1 — Foundation**: structure, config, logging, DB layer, FastAPI skeleton.
- [ ] **Step 2 — Document ingestion**: upload, parse, persist (API + schemas).
- [ ] **Step 3 — NLP service**: spaCy/NLTK preprocessing, entities, keywords.
- [ ] **Step 4 — ML service**: XGBoost churn/classification model + training script.
- [ ] **Step 5 — RAG pipeline**: Sentence-Transformers + FAISS + LangChain + Gemini.
- [ ] **Step 6 — Streamlit frontend**: professional multi-page UI.
- [ ] **Step 7 — Tests, Docker, CI**.

---

## ⚙️ Tech Stack
Python · FastAPI · Streamlit · SQLAlchemy · SQLite/PostgreSQL · scikit-learn ·
XGBoost · NLTK · spaCy · Sentence-Transformers · LangChain · FAISS · Gemini ·
Docker · Git.
