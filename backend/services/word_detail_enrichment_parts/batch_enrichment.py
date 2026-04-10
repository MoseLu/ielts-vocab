def _persist_llm_item(word_seed: dict, raw_item: dict) -> None:
    root_payload = _sanitize_root_payload(word_seed['display_word'], raw_item.get('root'))
    english_entries = _sanitize_english_entries(raw_item.get('english'))
    derivative_entries = _sanitize_derivatives(word_seed['display_word'], raw_item.get('derivatives'))
    example_entries = _sanitize_examples(raw_item.get('examples'), word_seed['examples'])

    upsert_word_catalog_entry(
        word_seed,
        root_payload=root_payload,
        english_entries=english_entries,
        derivative_entries=derivative_entries,
        example_entries=example_entries,
        source=LLM_SOURCE,
    )


def _enrich_batch(
    word_seeds: list[dict],
    *,
    stats: dict,
    provider: str,
    model: str | None,
    fallback_provider: str | None,
    fallback_model: str | None,
) -> None:
    for attempt in range(4):
        try:
            raw_items = request_llm_batch(
                word_seeds,
                provider=provider,
                model=model,
                fallback_provider=fallback_provider,
                fallback_model=fallback_model,
                normalize_word=_normalize_word,
            )
            for word_seed in word_seeds:
                _persist_llm_item(word_seed, raw_items[word_seed['normalized_word']])
            word_catalog_repository.commit()
            stats['enriched'] += len(word_seeds)
            return
        except Exception as exc:
            word_catalog_repository.rollback()
            if 'database is locked' in str(exc).lower() and attempt < 3:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise


def enrich_word_seeds(
    word_seeds: list[dict],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    overwrite: bool = False,
    sleep_seconds: float = 0.0,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
) -> dict:
    pending = collect_pending_word_seeds(word_seeds, overwrite=overwrite)
    stats = {
        'requested': len(word_seeds),
        'pending': len(pending),
        'enriched': 0,
        'failed': 0,
        'failed_words': [],
        'failure_details': [],
        'quota_exhausted': False,
        'stop_reason': '',
    }
    total_batches = (len(pending) + batch_size - 1) // batch_size if pending else 0

    def process(batch: list[dict], batch_index: int) -> None:
        if not batch:
            return
        try:
            _enrich_batch(
                batch,
                stats=stats,
                provider=provider,
                model=model,
                fallback_provider=fallback_provider,
                fallback_model=fallback_model,
            )
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        except Exception as exc:
            word_catalog_repository.rollback()
            if is_quota_exhausted_error(exc):
                stats['failed'] += len(batch)
                stats['failed_words'].extend(
                    seed['normalized_word']
                    for seed in batch
                )
                stats['failure_details'].append({
                    'word': batch[0]['normalized_word'],
                    'reason': str(exc),
                    'batch_size': len(batch),
                })
                stats['quota_exhausted'] = True
                stats['stop_reason'] = str(exc)
                print(
                    f'[Word Detail Enrichment] quota exhausted size={len(batch)} reason={exc}',
                    file=sys.stderr,
                    flush=True,
                )
                return
            print(
                f'[Word Detail Enrichment] split batch size={len(batch)} reason={exc}',
                file=sys.stderr,
                flush=True,
            )
            if len(batch) == 1:
                stats['failed'] += 1
                stats['failed_words'].append(batch[0]['normalized_word'])
                stats['failure_details'].append({
                    'word': batch[0]['normalized_word'],
                    'reason': str(exc),
                })
                return
            midpoint = max(1, len(batch) // 2)
            process(batch[:midpoint], batch_index)
            process(batch[midpoint:], batch_index + 1)

    for batch_index, start in enumerate(range(0, len(pending), batch_size), start=1):
        process(pending[start:start + batch_size], batch_index)
        print(
            f'[Word Detail Enrichment] batch {batch_index}/{total_batches} '
            f'enriched={stats["enriched"]} failed={stats["failed"]}'
        )
        if stats['quota_exhausted']:
            break

    return stats
