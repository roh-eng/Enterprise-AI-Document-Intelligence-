# Interview & Resume Pack

A ready-to-use kit for talking about this project: a resume entry, STAR stories,
HR and technical talking points, and a future-work roadmap.

---

## 📄 Resume description

**AI Document Intelligence Platform** — *Python, FastAPI, Streamlit, SQLAlchemy,
scikit-learn, XGBoost, spaCy, NLTK, Sentence-Transformers, FAISS, LangChain,
Gemini, Docker, GitHub Actions*

- Built a full-stack, production-grade platform that ingests PDF/DOCX/TXT
  documents and applies **classical ML, NLP, and Generative AI (RAG)** behind a
  clean-architecture FastAPI backend and a Streamlit frontend.
- Implemented **JWT authentication** with bcrypt password hashing, role-based
  admin access, and per-user document ownership/isolation.
- Trained and compared **Logistic Regression, Random Forest, and XGBoost** for
  5-class document classification (TF-IDF features), selecting the best by
  macro-F1 and serving it with confidence scores.
- Engineered an NLP pipeline (tokenization, lemmatization, **spaCy NER**, TF-IDF
  keywords, **VADER sentiment**, sentence-embedding similarity) with graceful
  offline fallbacks.
- Built a **RAG system**: LangChain chunking → Sentence-Transformer embeddings →
  **FAISS** vector search → grounded, **citation-backed** answers via Gemini,
  with conversation history.
- Added prompt engineering (system/safety/user prompts), an LLM **response cache
  + cost controls**, an analytics/admin dashboard, **52 automated tests**,
  Dockerized services, and a **GitHub Actions CI/CD** pipeline.

One-liner: *"A document platform where you upload files and get classification,
NLP insights, AI summaries, and a cite-backed chat with your documents."*

---

## ⭐ STAR interview answers

### STAR 1 — Making ML results meaningful (judgment)
- **Situation:** My first training run of the document classifier scored a
  perfect 1.000 across all three models.
- **Task:** Produce an honest, comparable evaluation with a real confusion matrix.
- **Action:** I diagnosed that the synthetic classes were too separable, so I
  injected **15% label noise into the training set only** (test set kept clean)
  to simulate real annotation error, and compared models on macro-F1.
- **Result:** Realistic, differentiated scores (RandomForest 0.992 > LogReg 0.976
  > XGBoost 0.952) and a meaningful confusion matrix — and a great talking point
  about why bagging resists label noise better than boosting.

### STAR 2 — Resilience through graceful degradation (design)
- **Situation:** The app depends on heavy/optional pieces (spaCy models, a
  ~2 GB Sentence-Transformers/torch stack, FAISS, a paid Gemini key).
- **Task:** Keep the product (and CI) working even when those aren't available.
- **Action:** I designed every AI feature to **prefer the real library and fall
  back to a transparent offline implementation** (TF-IDF embeddings, regex NER,
  extractive summaries, brute-force retrieval), and each response reports which
  engine served it.
- **Result:** 52 tests pass with or without the heavy models; the demo runs with
  zero API keys, and upgrades automatically when dependencies/keys appear.

### STAR 3 — Preventing data leaks and hallucination (correctness)
- **Situation:** A multi-tenant doc platform must not leak data or fabricate answers.
- **Task:** Enforce isolation and ground AI output.
- **Action:** Scoped every query by `user_id` (404, not 403, to avoid resource
  enumeration), kept hashes out of response schemas, and built RAG so answers are
  drawn only from retrieved passages **with citations**, plus prompt-injection
  defences ("treat the document as data, not instructions").
- **Result:** Ownership is covered by tests; answers are traceable to source
  chunks; "not in the document" is an allowed, honest response.

### STAR 4 — Catching a real bug before it shipped (rigor)
- **Situation:** A GenAI test intermittently failed: a "first call" appeared cached.
- **Task:** Find the root cause rather than retry.
- **Action:** Identified the response cache was process-global and leaked across
  tests; added a fixture to clear it between tests, restoring isolation.
- **Result:** Deterministic suite; reinforced the principle that shared state
  needs explicit lifecycle management.

---

## 🧑‍💼 HR / behavioural explanation (non-technical)

> "I built an 'AI Document Intelligence Platform.' In plain terms: you upload a
> document — a resume, invoice, contract, medical note, or research paper — and
> the system automatically sorts it, pulls out the key people/dates/topics,
> writes a summary, and lets you *chat* with the document and get answers that
> cite the exact passages they came from. I built it in weekly milestones —
> login/security first, then upload, then the AI features, then a dashboard, then
> deployment — and I kept it reliable by writing automated tests and making every
> AI feature degrade gracefully if a heavy model or API key isn't available. It
> taught me to balance ambition with pragmatism and to ship something that always
> works."

Strengths it demonstrates: ownership end-to-end, structured delivery, pragmatic
trade-offs, communication, and quality discipline.

---

## 🛠️ Technical interview explanation (deep dive)

- **Architecture:** Clean/layered — `api → services → engines/db → core`. Routes
  only do HTTP; business rules live in services; ML/NLP/GenAI/RAG live in their
  own engine packages; config/logging/security are cross-cutting. This keeps the
  framework swappable and the logic unit-testable.
- **Auth:** Stateless JWT (HS256) with bcrypt hashing; a `get_current_user`
  dependency validates the bearer token; `get_current_admin` adds RBAC. First
  registered user is bootstrapped as admin (no hard-coded secrets).
- **ML:** TF-IDF (1–2 grams) → LogReg/RF/XGBoost compared by macro-F1; the whole
  scikit-learn **Pipeline** is persisted with joblib so inference uses the exact
  same feature transform (no train/serve skew).
- **NLP:** spaCy (tokenize/lemmatize/NER), NLTK VADER (sentiment), and
  Sentence-Transformers embeddings for cosine/document similarity — all with
  offline fallbacks.
- **GenAI:** `google-genai` SDK (the maintained one) with system/safety/user
  prompts, output-token caps, low temperature, and a hash-keyed response cache
  for cost control; extractive fallbacks when no key.
- **RAG:** LangChain chunking → embeddings → **FAISS `IndexFlatIP`** (cosine on
  normalised vectors) → top-k retrieval → grounded answer with citations; chunk
  text is the DB source of truth, vectors live in FAISS.
- **Quality/Ops:** 52 pytest tests (unit + API integration with an in-memory DB),
  rotating logs, Dockerized backend/frontend, Compose, and GitHub Actions CI.

Likely follow-ups: *Fine-tuning vs. RAG*, *why cosine for text*, *bagging vs.
boosting*, *how to prevent prompt injection*, *SQLite → Postgres migration path*
(answers throughout the weekly READMEs).

---

## 🔮 Future improvements
- **Database:** PostgreSQL + **Alembic** migrations (replace dev `create_all`).
- **Auth:** refresh tokens + revocation; rate-limiting on `/auth/login`.
- **RAG:** ANN index (IVF/HNSW), cross-encoder re-ranking, multi-document chat,
  streaming responses, and conversational memory.
- **ML:** probability calibration, cross-validation/hyperparameter search, a real
  labelled corpus, and **MLflow** experiment tracking.
- **GenAI:** persistent (Redis) cache with TTL, per-user token budgeting/metering,
  and structured (JSON-schema) output.
- **Ops:** object storage (S3) for files, observability (structured logs +
  tracing + metrics), image push + deploy stage in CI, and HTTPS/Nginx ingress.
- **Product:** background processing for large uploads, OCR for scanned PDFs,
  and citation highlighting linked back to the source document.
