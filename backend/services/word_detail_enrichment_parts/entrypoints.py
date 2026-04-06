def enrich_catalog_words(
    *,
    book_ids: tuple[str, ...] | None = None,
    words: list[str] | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    limit: int | None = None,
    overwrite: bool = False,
    sleep_seconds: float = 0.0,
    start_at: int = 0,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
) -> dict:
    seeds = collect_word_seeds(book_ids)
    if words:
        wanted = {_normalize_word(word) for word in words}
        seeds = [seed for seed in seeds if seed['normalized_word'] in wanted]
    if start_at > 0:
        seeds = seeds[start_at:]
    if limit is not None:
        seeds = seeds[:limit]

    stats = enrich_word_seeds(
        seeds,
        batch_size=batch_size,
        overwrite=overwrite,
        sleep_seconds=sleep_seconds,
        provider=provider,
        model=model,
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
    )
    return {
        **stats,
        'book_ids': list(book_ids or []),
        'provider': normalize_provider(provider),
        'model': resolve_model(normalize_provider(provider), model),
        'word_count': len(seeds),
    }


def enrich_premium_books(
    *,
    book_ids: tuple[str, ...] = PREMIUM_BOOK_IDS,
    words: list[str] | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    limit: int | None = None,
    overwrite: bool = False,
    sleep_seconds: float = 0.0,
    start_at: int = 0,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
) -> dict:
    return enrich_catalog_words(
        book_ids=book_ids,
        words=words,
        batch_size=batch_size,
        limit=limit,
        overwrite=overwrite,
        sleep_seconds=sleep_seconds,
        start_at=start_at,
        provider=provider,
        model=model,
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
    )
