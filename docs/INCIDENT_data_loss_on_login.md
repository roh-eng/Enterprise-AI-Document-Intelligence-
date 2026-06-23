# Incident & Fix: "No data found" after logging in the next day

> Plain-English write-up of why a registered account disappeared overnight, the
> root cause, the fix we applied, and interview-style Q&A. Safe to share or paste
> into a portfolio.

---

## 1. What the user saw

- Created an account one day.
- Came back the next day, logged in.
- The app said **"no data was found"** — the account (and any uploaded
  documents) were gone, as if registration never happened.

## 2. Short version of the cause

The app saved everything in a **SQLite database file** that lived **inside the
running server container**. The cloud host (Render) **does not keep that
container's filesystem** between restarts. Every time the server restarted, it
came back with a **brand-new empty database**, so the old account was gone.

**This was a hosting/storage problem, not a bug in the login or registration
code.** The code did exactly what it was told — it just wrote data to a place
that does not survive a restart.

## 3. The cause in detail

### 3.1 Where the data was stored

The default database setting points at a local SQLite file:

```python
# backend/app/core/config.py
DATABASE_URL: str = "sqlite:///./data/app.db"
```

SQLite is a database that is just **one file on disk** (`app.db`). When you
register, a new row is written into that file (see
`backend/app/services/user_service.py` → `create_user`).

### 3.2 Why the file vanished — "ephemeral" container storage

The backend runs as a Docker container built from `Dockerfile.backend`. A
container's filesystem has two parts:

| Part | What it is | Survives a restart? |
|------|------------|---------------------|
| **Image layer** | The files baked in at build time (your code, libraries) | ✅ Yes — but read-only and fixed |
| **Writable layer** | Files created *while running* (like `app.db`) | ❌ **No** — wiped on restart/redeploy |

`app.db` is created **at runtime**, so it lives in the **writable layer**. It is
also **git-ignored**, so it was never part of the image. The result:

1. You register → `app.db` is created and your row is inserted **in the writable
   layer**.
2. The platform restarts the container. On a free tier this happens a lot:
   - the service **spins down when idle** and starts fresh on the next request,
   - it **redeploys on every `git push`**,
   - it **restarts after a crash** (our recent commits were fighting
     out-of-memory crashes from large ML wheels — each crash is a restart).
3. On restart the writable layer is **reset to the image**. The image has **no
   `app.db`**, so the app creates a new empty one (`init_db()` runs on startup
   and calls `Base.metadata.create_all`).
4. You log in → the lookup finds **no matching user** → **"no data found."**

### 3.3 Why it worked locally but not in the cloud

Locally with Docker Compose it *did* persist, because Compose mounts a **named
volume** that lives outside the container:

```yaml
# docker-compose.yml
volumes:
  - app-data:/data        # <- this is the durable storage
```

The cloud deployment was **not** using that volume. So the one thing that made
local data durable was missing in production. That mismatch is the whole story.

### 3.4 One-line root cause

> **A stateful app stored its only copy of the data on ephemeral (disposable)
> container storage, so every container restart silently reset the database.**

## 4. The fix we applied

**Switch from a file-based SQLite database to a managed PostgreSQL database**
that lives **outside** the container and persists across restarts. This is also
exactly what the project's own `docs/DEPLOYMENT.md` recommends for production.

### 4.1 Code changes (small — the app was already DB-agnostic)

The app talks to the database through SQLAlchemy and reads the connection string
from the `DATABASE_URL` environment variable, so most of the work is
configuration, not code. Two changes were needed:

**a) Enable the PostgreSQL driver** (`requirements.txt`):

```diff
- # psycopg2-binary>=2.9           # uncomment when migrating to PostgreSQL
+ psycopg2-binary>=2.9             # PostgreSQL driver (used when DATABASE_URL is postgres)
```

**b) Normalise the connection-string scheme** (`backend/app/core/config.py`).
Render (and Heroku) give a URL that starts with `postgres://`, but **SQLAlchemy
2.0 removed that alias** and only accepts `postgresql://`. Without this fix the
app would crash on boot with `Can't load plugin: sqlalchemy.dialects:postgres`:

```python
url = self.DATABASE_URL
if url.startswith("postgres://"):
    url = "postgresql+psycopg2://" + url[len("postgres://"):]
elif url.startswith("postgresql://"):
    url = "postgresql+psycopg2://" + url[len("postgresql://"):]
return url
```

No other code changed: `init_db()` auto-creates the tables on first startup
against whatever database `DATABASE_URL` points to.

### 4.2 Render configuration steps (do this in the dashboard)

1. **Create the database:** Render Dashboard → **New → PostgreSQL** (free plan is
   fine). Wait until it is "available".
2. **Copy the Internal Database URL** from the database's "Connections" page
   (looks like `postgres://user:pass@host/dbname`).
3. **Point the backend at it:** open your backend service → **Environment** → add
   `DATABASE_URL` = that internal URL.
4. Also confirm these are set on the backend service (so JWT tokens stay valid
   and the secret check passes):
   - `ENVIRONMENT=production`
   - `JWT_SECRET_KEY=<a strong random value>` — generate with
     `python -c "import secrets; print(secrets.token_hex(32))"`.
     > Bonus: a fixed secret also means tokens issued before a restart keep
     > working. With the old random/default secret, every restart could also
     > invalidate everyone's login tokens.
5. **Deploy.** On startup `init_db()` creates the tables in Postgres. Register
   again — this account now lives in Postgres and **survives every restart**.

### 4.3 Important follow-up: uploaded files and the search index

Postgres fixes the **accounts, document metadata, summaries, chunks, and chat
history** (all of those are rows in the database). But two things are still
written to the container's disk and will still be lost on restart:

- the **original uploaded files** (`UPLOAD_DIR`), and
- the **FAISS vector index** (`FAISS_INDEX_PATH`).

For a complete fix, do **one** of:

- **Attach a Render Disk** to the backend and set `UPLOAD_DIR` and
  `FAISS_INDEX_PATH` to a path on that disk (e.g. `/var/data/uploads`), **or**
- move uploads to **object storage** (S3 / Cloudflare R2) — the production-grade
  option noted in `docs/DEPLOYMENT.md`.

For login + dashboard data (the original bug), **Postgres alone is enough.**

## 4bis. Second issue found while fixing: the deploy crashed on boot

After the storage change, the Render deploy failed with **"Exited with status 1
while running your code"** during startup. This was a *separate* problem, and it
turned out to be a **safety feature working as designed**, not a bug.

**Cause.** The app has a guard that **refuses to start in production with the
default JWT secret** (so you can never ship forgeable login tokens):

```python
# backend/app/core/config.py
if self.ENVIRONMENT.lower() == "production" and self.JWT_SECRET_KEY == self._DEV_SECRET:
    raise ValueError("JWT_SECRET_KEY must be set to a strong value in production ...")
```

Settings are loaded **at import time**, so when `ENVIRONMENT=production` was set
on Render but `JWT_SECRET_KEY` was left at the default, the app raised this error
the instant uvicorn imported it → the container exited with status 1 → deploy
failed. The long traceback in the logs ended at this `ValueError`.

**Fix.** Set a real secret in the Render backend service's environment:

```
JWT_SECRET_KEY = <output of: python -c "import secrets; print(secrets.token_hex(32))">
```

> Related: the DB engine is also built at import time, so a `postgres://`
> `DATABASE_URL` **without** the `psycopg2` driver would crash the same way
> (`ModuleNotFoundError: No module named 'psycopg2'`). That's why we added
> `psycopg2-binary` to `requirements.txt`.

**Interview soundbite:** *"The deploy crash wasn't a bug — it was a fail-fast
security check refusing to boot without a production secret. The fix was to
provide the secret as an environment variable, not to weaken the check."*

## 5. How to verify the fix

1. Register a new account on the deployed app.
2. In Render, **manually trigger a redeploy** (or restart the service) — this
   simulates the overnight restart that used to wipe data.
3. Log back in. **The account is still there.** ✅

(Optional, technical check) Connect to the Postgres database and confirm the row
exists:

```sql
SELECT id, username, email, created_at FROM users;
```

## 6. How to prevent this class of bug in future

- **Never store the only copy of important data on a container's local disk.**
  Use a managed database or a mounted persistent volume.
- **Treat containers as disposable ("stateless").** Anything that must outlive a
  restart belongs in an external service (database, object storage).
- **Keep dev and prod storage consistent.** The local volume worked; production
  silently didn't. Matching them would have caught this earlier.
- **Use real migrations (Alembic)** instead of `create_all` once the schema
  starts changing, so schema updates are controlled and reversible.

---

## 7. Interview Q&A (simple English)

**Q1. What was the bug?**
A user registered, came back the next day, and the app said "no data found."
Their account had disappeared.

**Q2. What was the root cause?**
The app stored its data in a SQLite file inside the server container. Cloud
containers have disposable storage — when the container restarts, that file is
wiped. So every restart gave the app a fresh, empty database and the old account
was gone.

**Q3. Why did the container restart?**
Free-tier hosts restart often: they sleep when idle, redeploy on every code
push, and restart after crashes. Our service was also crashing due to memory
limits, which caused even more restarts.

**Q4. Was it a code bug?**
No. The registration and login code were correct. It was an **infrastructure /
data-persistence** problem — the data was written to a place that doesn't
survive restarts.

**Q5. Why did it work on your laptop but not in the cloud?**
Locally, Docker Compose mounted a persistent volume, so the database file lived
outside the container and survived restarts. The cloud deployment didn't have
that volume, so the file was ephemeral.

**Q6. How did you fix it?**
I switched the production database from a SQLite file to a **managed PostgreSQL**
database that lives outside the container. I enabled the Postgres driver
(`psycopg2-binary`) and set `DATABASE_URL` to the managed database. Now the data
lives in a durable service and survives any number of restarts.

**Q7. Did you have to rewrite the app for Postgres?**
Almost nothing. The app uses SQLAlchemy (an ORM) and reads `DATABASE_URL` from
the environment, so it's database-agnostic. The only code I touched was
converting Render's `postgres://` URL prefix to the `postgresql://` form that
SQLAlchemy 2.0 requires.

**Q8. What's the difference between SQLite and PostgreSQL here?**
SQLite is a single file on disk — great for local development, but tied to one
machine's filesystem. PostgreSQL is a separate database server — durable,
networked, and supports many users and connections at once. For a deployed
multi-user app, Postgres is the right choice.

**Q9. What does "ephemeral storage" mean?**
"Ephemeral" means temporary / disposable. A container's local disk is ephemeral:
files written while it runs are thrown away when it restarts. Durable data must
go somewhere that outlives the container, like a database or object storage.

**Q10. What's the general lesson?**
Treat servers/containers as stateless and disposable. Never keep the only copy
of important data on their local disk. Put persistent state in a managed
database or persistent volume, and keep development and production storage
consistent so problems show up early.

**Q11. Anything still left to do?**
Yes — uploaded files and the search index are still on the container's disk, so
those would be lost on restart too. The complete fix is to attach a persistent
disk or move uploads to object storage (S3 / R2). The login/account bug,
though, is fully solved by Postgres.
