# TTS Batch Generation Plan

Last updated: 2026-03-28

## Goal

Allow admins to pre-generate example-sentence TTS audio for an entire vocabulary book from the admin console, run the generation asynchronously, and expose progress so dictation mode can hit local cache instead of generating on first play.

## Scope

### Backend

- Add admin-facing TTS batch routes under `backend/routes/tts.py`.
- Register the admin TTS blueprint from the backend app/router layer.
- Reuse the existing MiniMax TTS path and cache layout in `backend/tts_cache/`.
- Track generation progress per book and expose summary/status endpoints.

### Frontend

- Add a dedicated TTS tab in `src/components/AdminDashboard.tsx`.
- Show book-by-book generation status, progress, and action buttons.
- Poll generation state after an admin starts a batch.

## API Plan

### `GET /api/admin/tts/books-summary`

Return all vocabulary books with:

- `book_id`
- `title`
- `total`
- `cached`
- `generating`

### `POST /api/admin/tts/generate/<book_id>`

- Require admin auth.
- Reject unknown books.
- Reject duplicate in-flight generation for the same book.
- Start the asynchronous generation worker and return `202`.

### `GET /api/admin/tts/status/<book_id>`

Return the latest generation state for a single book.

## Backend Task Breakdown

1. Add helper functions for:
   - loading example sentences for one book
   - mapping sentences to cache keys and cache paths
   - counting cached examples
   - running the batch generation worker
2. Expose the three admin endpoints.
3. Register the blueprint and verify route wiring.

## Frontend Task Breakdown

1. Add a `tts` tab state in the admin dashboard.
2. Fetch the book summary when the tab opens.
3. Render one card per book with:
   - title
   - progress bar
   - cached/total status
   - generate button
4. Poll per-book status after generation starts.

## Verification

1. Start backend and frontend locally.
2. Open `/admin` as an admin user.
3. Switch to the TTS tab.
4. Confirm all books render with the right totals.
5. Start generation for one book.
6. Confirm status polling updates the card.
7. Confirm completion state turns the action into a done state.
