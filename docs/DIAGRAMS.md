# Diagrams

All diagrams use [Mermaid](https://mermaid.js.org/) and render natively on GitHub.

---

## 1. Architecture Diagram (component view)

```mermaid
flowchart TB
    subgraph Client
        UI["Streamlit Frontend<br/>(views + api_client)"]
    end

    subgraph API["FastAPI Backend"]
        R["API Routers<br/>auth · documents · ml · nlp · genai · rag · analytics"]
        DEP["Dependencies<br/>get_current_user / get_current_admin (JWT)"]
        subgraph SVC["Service Layer"]
            US["user_service"]
            DS["document_service"]
            CS["classification_service"]
            NS["nlp_service"]
            GS["genai_service"]
            RS["rag_service"]
            AS["analytics_service"]
        end
        subgraph ENG["Engines"]
            ML["ml/ — TF-IDF + RF/LogReg/XGBoost"]
            NLP["nlp/ — spaCy · NLTK · sentence-transformers"]
            GEN["genai/ — Gemini client + prompts + fallback"]
            RAG["rag/ — chunking · FAISS · pipeline"]
        end
        CORE["core/ — config · logging · security"]
    end

    subgraph Data
        DB[("SQLite / PostgreSQL<br/>SQLAlchemy ORM")]
        FS["File storage<br/>data/uploads"]
        VEC["FAISS indexes<br/>data/faiss"]
    end

    EXT["Google Gemini API<br/>(optional)"]

    UI -- "HTTP/JSON + Bearer JWT" --> R
    R --> DEP --> SVC
    SVC --> ENG
    SVC --> DB
    DS --> FS
    RAG --> VEC
    GEN -. "if GEMINI_API_KEY" .-> EXT
    ENG --> CORE
    SVC --> CORE
```

---

## 2. Data Flow Diagram (document → insight)

```mermaid
flowchart LR
    A["Upload<br/>PDF / DOCX / TXT"] --> B["Extract text<br/>pypdf / python-docx"]
    B --> C["Clean text<br/>normalise + dehyphenate"]
    C --> D[("Store Document<br/>+ raw file on disk")]
    D --> E["Classify<br/>TF-IDF + model → category"]
    D --> F["NLP analyse<br/>entities · keywords · sentiment"]
    D --> G["Chunk + embed<br/>→ FAISS index"]
    D --> H["GenAI<br/>summary · FAQ · action items"]
    G --> I["RAG chat<br/>retrieve → ground → answer + cite"]
    E --> J["📊 Analytics dashboard"]
    F --> J
    I --> J
```

---

## 3. Sequence Diagram (RAG chat request)

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Streamlit
    participant API as FastAPI /documents/{id}/chat
    participant RS as rag_service
    participant VS as FAISS vector store
    participant EMB as sentence-transformers
    participant LLM as Gemini (or fallback)
    participant DB as Database

    U->>FE: ask question
    FE->>API: POST /chat {question} + JWT
    API->>API: get_current_user (verify JWT)
    API->>RS: chat(user, doc_id, question)
    RS->>DB: load/ensure chunks (auto-index if needed)
    RS->>EMB: embed(question)
    EMB-->>RS: query vector
    RS->>VS: search(top-k)
    VS-->>RS: relevant chunks + scores
    RS->>LLM: prompt(system+safety, context, question)
    LLM-->>RS: grounded answer with [1][2] citations
    RS->>DB: persist user + assistant ChatMessages
    RS-->>API: answer + sources
    API-->>FE: ChatResponse
    FE-->>U: answer + expandable source passages
```

---

## 4. ER Diagram (database schema)

```mermaid
erDiagram
    USER ||--o{ DOCUMENT : owns
    USER ||--o{ CHAT_MESSAGE : writes
    DOCUMENT ||--o| SUMMARY : has
    DOCUMENT ||--o{ QUERY_LOG : has
    DOCUMENT ||--o{ DOCUMENT_CHUNK : split_into
    DOCUMENT ||--o{ CHAT_MESSAGE : about

    USER {
        int id PK
        string username UK
        string email UK
        string hashed_password
        bool is_active
        bool is_admin
        datetime created_at
    }
    DOCUMENT {
        int id PK
        int user_id FK
        string filename
        string content_type
        string file_ext
        int file_size
        string storage_path
        int num_chars
        int num_chunks
        string status
        string category
        float category_confidence
        text extracted_text
        datetime created_at
    }
    SUMMARY {
        int id PK
        int document_id FK
        text content
        string model_used
        datetime created_at
    }
    QUERY_LOG {
        int id PK
        int document_id FK
        text question
        text answer
        string model_used
        datetime created_at
    }
    DOCUMENT_CHUNK {
        int id PK
        int document_id FK
        int chunk_index
        text text
    }
    CHAT_MESSAGE {
        int id PK
        int document_id FK
        int user_id FK
        string role
        text content
        text sources
        datetime created_at
    }
```
