from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Callable

from flask import Blueprint, Flask

from routes.admin import admin_bp, init_admin
from routes.ai import ai_bp
from routes.auth import auth_bp, init_auth
from routes.books import books_bp, init_books
from routes.notes import notes_bp
from routes.progress import progress_bp
from routes.speech import speech_bp
from routes.tts import tts_admin_bp, tts_bp
from routes.vocabulary import vocabulary_bp


@dataclass(frozen=True)
class MonolithCompatRouteGroup:
    name: str
    url_prefix: str
    blueprint: Blueprint
    rationale: str
    probe_path: str
    surface_kind: str = 'browser'
    init_hook: Callable[[Flask], None] | None = None


MONOLITH_COMPAT_ROUTE_GROUPS: tuple[MonolithCompatRouteGroup, ...] = (
    MonolithCompatRouteGroup(
        name='auth',
        url_prefix='/api/auth',
        blueprint=auth_bp,
        rationale='legacy cookie-auth browser compatibility surface',
        probe_path='/api/auth/me',
        init_hook=init_auth,
    ),
    MonolithCompatRouteGroup(
        name='progress',
        url_prefix='/api/progress',
        blueprint=progress_bp,
        rationale='legacy day-progress compatibility surface',
        probe_path='/api/progress',
    ),
    MonolithCompatRouteGroup(
        name='vocabulary',
        url_prefix='/api/vocabulary',
        blueprint=vocabulary_bp,
        rationale='legacy vocabulary listing compatibility surface',
        probe_path='/api/vocabulary',
    ),
    MonolithCompatRouteGroup(
        name='speech',
        url_prefix='/api/speech',
        blueprint=speech_bp,
        rationale='legacy HTTP speech fallback compatibility surface',
        probe_path='/api/speech/transcribe',
    ),
    MonolithCompatRouteGroup(
        name='books',
        url_prefix='/api/books',
        blueprint=books_bp,
        rationale='legacy books/catalog compatibility surface',
        probe_path='/api/books/stats',
        init_hook=init_books,
    ),
    MonolithCompatRouteGroup(
        name='ai',
        url_prefix='/api/ai',
        blueprint=ai_bp,
        rationale='legacy AI browser compatibility surface',
        probe_path='/api/ai/learning-stats',
    ),
    MonolithCompatRouteGroup(
        name='notes',
        url_prefix='/api/notes',
        blueprint=notes_bp,
        rationale='legacy notes browser compatibility surface',
        probe_path='/api/notes',
    ),
    MonolithCompatRouteGroup(
        name='tts',
        url_prefix='/api/tts',
        blueprint=tts_bp,
        rationale='legacy TTS browser compatibility surface',
        probe_path='/api/tts/voices',
    ),
    MonolithCompatRouteGroup(
        name='tts-admin',
        url_prefix='/api/tts',
        blueprint=tts_admin_bp,
        rationale='legacy TTS admin batch rollback surface',
        probe_path='/api/tts/books-summary',
        surface_kind='rollback',
    ),
    MonolithCompatRouteGroup(
        name='admin',
        url_prefix='/api/admin',
        blueprint=admin_bp,
        rationale='legacy admin browser compatibility surface',
        probe_path='/api/admin/overview',
        init_hook=init_admin,
    ),
)


MONOLITH_COMPAT_ROUTE_GROUPS_ENV = 'MONOLITH_COMPAT_ROUTE_GROUPS'
MONOLITH_COMPAT_SURFACE_KIND_BROWSER = 'browser'
MONOLITH_COMPAT_SURFACE_KIND_ROLLBACK = 'rollback'
MONOLITH_COMPAT_SURFACE_KIND_ALL = 'all'


def monolith_compat_route_group_names() -> list[str]:
    return [group.name for group in MONOLITH_COMPAT_ROUTE_GROUPS]


def monolith_compat_surface_names() -> list[str]:
    return [
        MONOLITH_COMPAT_SURFACE_KIND_BROWSER,
        MONOLITH_COMPAT_SURFACE_KIND_ROLLBACK,
        MONOLITH_COMPAT_SURFACE_KIND_ALL,
    ]


def resolve_monolith_compat_route_groups_for_surface(surface_kind: str | None) -> tuple[MonolithCompatRouteGroup, ...]:
    normalized = (surface_kind or MONOLITH_COMPAT_SURFACE_KIND_ALL).strip().lower()
    if not normalized:
        normalized = MONOLITH_COMPAT_SURFACE_KIND_ALL
    if normalized == MONOLITH_COMPAT_SURFACE_KIND_ALL:
        return MONOLITH_COMPAT_ROUTE_GROUPS
    if normalized not in {
        MONOLITH_COMPAT_SURFACE_KIND_BROWSER,
        MONOLITH_COMPAT_SURFACE_KIND_ROLLBACK,
    }:
        raise ValueError(
            f'Unknown monolith compatibility surface: {surface_kind}. '
            f'Known surfaces: {", ".join(monolith_compat_surface_names())}'
        )
    return tuple(group for group in MONOLITH_COMPAT_ROUTE_GROUPS if group.surface_kind == normalized)


def resolve_monolith_compat_probe_path(route_groups: tuple[MonolithCompatRouteGroup, ...]) -> str:
    if not route_groups:
        raise ValueError('Cannot resolve a probe path without at least one monolith compatibility route group.')

    preferred_order = (
        'books',
        'tts',
        'auth',
        'notes',
        'ai',
        'progress',
        'vocabulary',
        'admin',
        'speech',
        'tts-admin',
    )
    group_by_name = {group.name: group for group in route_groups}
    for group_name in preferred_order:
        if group_name in group_by_name:
            return group_by_name[group_name].probe_path
    return route_groups[0].probe_path


def resolve_enabled_monolith_compat_route_groups(raw_value: str | None = None) -> tuple[MonolithCompatRouteGroup, ...]:
    selected_value = raw_value if raw_value is not None else os.environ.get(MONOLITH_COMPAT_ROUTE_GROUPS_ENV)
    if selected_value is None or not selected_value.strip():
        return MONOLITH_COMPAT_ROUTE_GROUPS

    selected_tokens = [token.strip() for token in selected_value.split(',') if token.strip()]
    normalized = {token.lower() for token in selected_tokens}
    if not normalized or normalized == {'all'}:
        return MONOLITH_COMPAT_ROUTE_GROUPS
    if normalized == {'none'}:
        return ()

    known_names = set(monolith_compat_route_group_names())
    unknown = sorted(normalized - known_names)
    if unknown:
        raise ValueError(
            f'Unknown monolith compatibility route groups: {", ".join(unknown)}. '
            f'Known groups: {", ".join(monolith_compat_route_group_names())}'
        )

    return tuple(group for group in MONOLITH_COMPAT_ROUTE_GROUPS if group.name in normalized)


def describe_monolith_compat_route_groups() -> list[dict[str, str]]:
    return [
        {
            'name': group.name,
            'url_prefix': group.url_prefix,
            'blueprint': group.blueprint.name,
            'rationale': group.rationale,
            'probe_path': group.probe_path,
            'surface_kind': group.surface_kind,
            'has_init_hook': 'yes' if group.init_hook is not None else 'no',
        }
        for group in MONOLITH_COMPAT_ROUTE_GROUPS
    ]
