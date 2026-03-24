# Backend Development Guide

## Build & Deployment Process

### 1. SQLite WAL Mode (Enabled by Default)

WAL mode is automatically enabled for better concurrency:

```python
@event.listeners_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
```

This runs on every new database connection automatically.

---

### 2. Database Migrations with Flask-Migrate

**Dependency**: `Flask-Migrate==4.0.5` (in `requirements.txt`)

**Initialization** (one-time setup):

```bash
cd backend
pip install Flask-Migrate==4.0.5
flask db stamp head  # Mark current state as baseline (no data change)
```

**Standard Workflow** (for future schema changes):

```bash
# 1. Modify models.py
# 2. Generate migration file
flask db migrate -m "add xxx column to yyy"
# 3. Apply to database
flask db upgrade
```

**Migrations Directory**: `backend/migrations/`
- Contains all migration scripts
- Initial migration creates all 20 tables

---

### Quick Reference

| Command | Description |
|---------|-------------|
| `pip install Flask-Migrate==4.0.5` | Install migration tool |
| `flask db stamp head` | Mark current schema as baseline |
| `flask db migrate -m "message"` | Generate new migration |
| `flask db upgrade` | Apply pending migrations |
| `flask db downgrade` | Rollback one migration |
