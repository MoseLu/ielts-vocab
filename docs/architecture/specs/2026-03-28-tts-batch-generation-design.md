# TTS Batch Generation Design

## Background

Dictation mode currently relies on just-in-time example-audio generation. That keeps the implementation simple, but it means the first playback of an uncached sentence pays the full external TTS latency cost.

Large books can contain thousands of example sentences, so admins need a way to warm the cache in advance.

## Design Goals

- Allow admins to batch-generate example audio by book.
- Keep generation off the request thread.
- Reuse the existing cache format and playback path.
- Expose progress in a way the admin dashboard can poll safely.

## Existing System

### Data Sources

- Vocabulary books are defined in `routes/books.py`.
- Example sentences are stored alongside word data and example data sources.
- Example-audio cache files live under `backend/tts_cache/`.

### Existing Runtime Path

- Dictation mode calls the example-audio endpoint.
- The backend checks local cache first.
- Missing audio falls back to the MiniMax TTS API.

## Proposed Design

### Progress Model

For each book:

- `total` = number of words with at least one example sentence
- `cached` = number of example sentences with at least one cached voice variant
- `generating` = whether a background worker is actively processing that book

This keeps the admin UI simple and avoids over-reporting partial voice coverage as zero progress.

### Backend Behavior

#### Summary Endpoint

Return progress for all books so the admin UI can render the whole dashboard with one request.

#### Start Endpoint

- Validate admin access.
- Validate the target book.
- Reject duplicate concurrent work for the same book.
- Spawn an asynchronous worker for the selected book.

#### Status Endpoint

Return the live state for one book so the frontend can poll until completion.

### Background Worker

For each example sentence in the selected book:

1. Compute the expected cache path for each supported voice.
2. Skip any voice that is already cached.
3. Call the MiniMax TTS API for missing audio.
4. Persist the returned audio file into the existing cache directory.
5. Sleep briefly between requests to avoid burst pressure on the upstream API.

## Frontend Behavior

The admin dashboard gets a dedicated TTS tab that:

- loads summary data on entry
- renders one card per book
- lets the admin trigger generation
- polls status for in-flight books until they finish

## Files Affected

### Backend

- `backend/routes/tts.py`
- `backend/routes/admin.py` or equivalent registration layer
- `backend/app.py` if blueprint registration belongs there

### Frontend

- `src/components/AdminDashboard.tsx`
- `src/styles/pages/admin.scss`

## Non-Goals

- No change to dictation-mode playback flow.
- No change to cache-key format.
- No migration away from the existing TTS provider in this task.
