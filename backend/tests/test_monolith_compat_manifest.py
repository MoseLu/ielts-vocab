from monolith_compat_manifest import (
    MONOLITH_COMPAT_SURFACE_KIND_ALL,
    MONOLITH_COMPAT_SURFACE_KIND_BROWSER,
    MONOLITH_COMPAT_SURFACE_KIND_ROLLBACK,
    MONOLITH_COMPAT_ROUTE_GROUPS,
    MONOLITH_COMPAT_ROUTE_GROUPS_ENV,
    describe_monolith_compat_route_groups,
    monolith_compat_route_group_names,
    monolith_compat_surface_names,
    resolve_monolith_compat_probe_path,
    resolve_enabled_monolith_compat_route_groups,
    resolve_monolith_compat_route_groups_for_surface,
)


def test_monolith_compat_route_groups_are_explicit_and_stable():
    assert [group.name for group in MONOLITH_COMPAT_ROUTE_GROUPS] == [
        'auth',
        'progress',
        'vocabulary',
        'speech',
        'books',
        'ai',
        'notes',
        'exams',
        'exam-attempts',
        'tts',
        'tts-admin',
        'admin',
        'ops',
    ]
    assert [group.url_prefix for group in MONOLITH_COMPAT_ROUTE_GROUPS] == [
        '/api/auth',
        '/api/progress',
        '/api/vocabulary',
        '/api/speech',
        '/api/books',
        '/api/ai',
        '/api/notes',
        '/api/exams',
        '/api/exam-attempts',
        '/api/tts',
        '/api/tts',
        '/api/admin',
        '/api/ops',
    ]


def test_monolith_compat_manifest_describes_blueprint_surface():
    descriptions = describe_monolith_compat_route_groups()

    assert len(descriptions) == len(MONOLITH_COMPAT_ROUTE_GROUPS)
    assert descriptions[0]['blueprint'] == 'auth'
    assert descriptions[0]['probe_path'] == '/api/auth/me'
    assert descriptions[0]['surface_kind'] == 'browser'
    rollback_description = next(item for item in descriptions if item['blueprint'] == 'tts_admin_legacy')
    assert rollback_description['probe_path'] == '/api/tts/books-summary'
    assert rollback_description['surface_kind'] == 'rollback'
    assert descriptions[-1]['blueprint'] == 'ops'
    assert descriptions[0]['has_init_hook'] == 'yes'
    assert descriptions[1]['has_init_hook'] == 'no'


def test_monolith_compat_route_group_resolver_defaults_to_all_groups():
    assert resolve_enabled_monolith_compat_route_groups() == MONOLITH_COMPAT_ROUTE_GROUPS
    assert monolith_compat_route_group_names() == [
        'auth',
        'progress',
        'vocabulary',
        'speech',
        'books',
        'ai',
        'notes',
        'exams',
        'exam-attempts',
        'tts',
        'tts-admin',
        'admin',
        'ops',
    ]
    assert monolith_compat_surface_names() == ['browser', 'rollback', 'all']
    assert resolve_monolith_compat_route_groups_for_surface(MONOLITH_COMPAT_SURFACE_KIND_ALL) == MONOLITH_COMPAT_ROUTE_GROUPS
    assert [group.name for group in resolve_monolith_compat_route_groups_for_surface(MONOLITH_COMPAT_SURFACE_KIND_BROWSER)] == [
        'auth',
        'progress',
        'vocabulary',
        'speech',
        'books',
        'ai',
        'notes',
        'exams',
        'exam-attempts',
        'tts',
        'admin',
        'ops',
    ]
    assert [group.name for group in resolve_monolith_compat_route_groups_for_surface(MONOLITH_COMPAT_SURFACE_KIND_ROLLBACK)] == [
        'tts-admin',
    ]
    assert resolve_monolith_compat_probe_path(
        resolve_monolith_compat_route_groups_for_surface(MONOLITH_COMPAT_SURFACE_KIND_BROWSER)
    ) == '/api/books/stats'
    assert resolve_monolith_compat_probe_path(
        resolve_monolith_compat_route_groups_for_surface(MONOLITH_COMPAT_SURFACE_KIND_ROLLBACK)
    ) == '/api/tts/books-summary'


def test_monolith_compat_route_group_resolver_supports_subset_and_none():
    subset = resolve_enabled_monolith_compat_route_groups('auth,books,tts-admin')
    assert [group.name for group in subset] == ['auth', 'books', 'tts-admin']
    assert resolve_enabled_monolith_compat_route_groups('none') == ()
    assert resolve_enabled_monolith_compat_route_groups('all') == MONOLITH_COMPAT_ROUTE_GROUPS


def test_monolith_compat_route_group_resolver_rejects_unknown_values():
    try:
        resolve_enabled_monolith_compat_route_groups('auth,unknown-group')
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError('Expected ValueError for unknown route group')

    assert MONOLITH_COMPAT_ROUTE_GROUPS_ENV in 'MONOLITH_COMPAT_ROUTE_GROUPS'
    assert 'unknown-group' in message
    assert 'auth, progress, vocabulary' in message


def test_monolith_compat_surface_resolver_rejects_unknown_surface():
    try:
        resolve_monolith_compat_route_groups_for_surface('unknown-surface')
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError('Expected ValueError for unknown surface')

    assert 'unknown-surface' in message
    assert 'browser, rollback, all' in message
