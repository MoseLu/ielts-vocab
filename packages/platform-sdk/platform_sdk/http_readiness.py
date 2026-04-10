from __future__ import annotations

import httpx


def make_http_readiness_check(*, base_url: str, path: str = '/ready', timeout_seconds: float = 2.0):
    normalized_base = base_url.rstrip('/')
    normalized_path = path if path.startswith('/') else f'/{path}'

    def check() -> bool:
        try:
            response = httpx.get(
                f'{normalized_base}{normalized_path}',
                timeout=max(0.1, timeout_seconds),
            )
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    return check
