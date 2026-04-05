def main() -> int:
    parser = argparse.ArgumentParser(description='重生成短句例句')
    parser.add_argument('--workers', type=int, default=8, help='并发请求数')
    parser.add_argument('--batch-size', type=int, default=20, help='每次请求的单词数')
    parser.add_argument('--save-interval', type=int, default=10, help='每完成 N 个批次落盘一次')
    parser.add_argument('--limit', type=int, default=0, help='仅处理前 N 个词，用于 smoke test')
    parser.add_argument('--retry-missing', action='store_true', help='对失败词做一次单词级重试')
    args = parser.parse_args()

    if not API_KEY_PRIMARY and not API_KEY_SECONDARY:
        print('ERROR: missing MiniMax API key')
        return 1

    all_specs = _load_target_words()
    if args.limit > 0:
        all_specs = all_specs[:args.limit]

    existing = _load_existing_examples()
    preserved = dict(existing)
    seeded_results: dict[str, list[dict[str, str]]] = {}
    pending_specs: list[WordSpec] = []
    for spec in all_specs:
        short_example = _existing_short_example(spec, existing)
        if short_example is not None:
            seeded_results[spec.word.lower()] = short_example
            continue
        pending_specs.append(spec)

    batches = _build_batches(pending_specs, max(1, args.batch_size))
    total = len(all_specs)
    completed = len(seeded_results)
    errors = 0
    results: dict[str, list[dict[str, str]]] = dict(seeded_results)
    missing_specs: list[WordSpec] = []
    save_lock = threading.Lock()

    print('=' * 72)
    print('Short Example Generator')
    print(f'Model: {MODEL}')
    print(f'Words: {total} | Already short: {len(seeded_results)} | Pending: {len(pending_specs)}')
    print(f'Batches: {len(batches)} | Workers: {args.workers}')
    print(f'Target books: {", ".join(TARGET_BOOKS.keys())}')
    print('=' * 72)

    _write_progress(total=total, completed=completed, status='running', errors=0)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        pending = {
            executor.submit(_process_batch, index, batch): index
            for index, batch in enumerate(batches)
        }
        finished_batches = 0

        while pending:
            done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
            for future in done:
                batch_index = pending.pop(future)
                batch = batches[batch_index]
                try:
                    _, accepted, missing = future.result()
                except Exception as exc:
                    accepted = []
                    missing = [spec.word for spec in batch]
                    print(f'[batch {batch_index + 1}/{len(batches)}] ERROR {exc}', flush=True)

                for key, value in accepted:
                    results[key] = value
                completed += len(accepted)
                errors += len(missing)
                missing_specs.extend(spec for spec in batch if spec.word in missing)
                finished_batches += 1

                current_word = batch[-1].word if batch else None
                print(
                    f'[batch {finished_batches}/{len(batches)}] '
                    f'ok={len(accepted)}/{len(batch)} total_ok={completed}/{total} missing={len(missing)}',
                    flush=True,
                )

                if finished_batches % max(1, args.save_interval) == 0 or finished_batches == len(batches):
                    with save_lock:
                        _save_examples({**preserved, **results})
                        _write_progress(
                            total=total,
                            completed=completed,
                            status='running',
                            current_word=current_word,
                            errors=errors,
                        )

    if args.retry_missing and missing_specs:
        dedup_missing: dict[str, WordSpec] = {}
        for spec in missing_specs:
            dedup_missing[spec.word.lower()] = spec
        retry_list = list(dedup_missing.values())
        print(f'[retry] single-word retry count={len(retry_list)}', flush=True)
        for index, spec in enumerate(retry_list, start=1):
            try:
                _, accepted, missing = _process_batch(index - 1, [spec])
            except Exception as exc:
                accepted = []
                missing = [spec.word]
                print(f'[retry {index}/{len(retry_list)}] ERROR {spec.word}: {exc}', flush=True)
            for key, value in accepted:
                results[key] = value
            if not accepted and missing:
                print(f'[retry {index}/{len(retry_list)}] MISS {spec.word}', flush=True)
            elif accepted:
                completed += 1
                errors = max(0, errors - 1)
                print(f'[retry {index}/{len(retry_list)}] OK {spec.word}', flush=True)

    final_examples = {**preserved, **results}
    _save_examples(final_examples)
    status = 'done' if len(results) == total else 'done_with_gaps'
    _write_progress(
        total=total,
        completed=len(results),
        status=status,
        current_word=all_specs[-1].word if all_specs else None,
        errors=max(0, total - len(results)),
    )

    print('=' * 72)
    print(f'Finished: {len(results)}/{total} target words regenerated')
    print(f'Status: {status}')
    print('=' * 72)
    return 0 if len(results) == total else 2


if __name__ == '__main__':
    raise SystemExit(main())
