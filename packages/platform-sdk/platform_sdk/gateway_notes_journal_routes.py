from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request, Response


NotesProxy = Callable[[Request, str], Awaitable[Response]]


def register_notes_journal_routes(router: APIRouter, proxy_notes_request: NotesProxy) -> None:
    @router.get('/api/notes/journal')
    async def notes_journal_list_proxy(request: Request):
        return await proxy_notes_request(request, '/api/notes/journal')

    @router.get('/api/notes/journal/today')
    async def notes_journal_today_proxy(request: Request):
        return await proxy_notes_request(request, '/api/notes/journal/today')

    @router.post('/api/notes/journal')
    async def notes_journal_upsert_proxy(request: Request):
        return await proxy_notes_request(request, '/api/notes/journal')

    @router.post('/api/notes/journal/polish')
    async def notes_journal_polish_proxy(request: Request):
        return await proxy_notes_request(request, '/api/notes/journal/polish')
