from __future__ import annotations

import hashlib
import json
from datetime import datetime


def get_book_examples(book_id: str, *, load_book_vocabulary) -> list[dict]:
    words = load_book_vocabulary(book_id)
    examples = []
    for word in words:
        if word.get('examples'):
            examples.append({
                'word': word['word'],
                'sentence': word['examples'][0]['en'],
            })
    return examples


def cache_file_path(cache_dir_resolver, sentence: str, voice_id: str):
    key = hashlib.md5(f'ex:{sentence}:{voice_id}'.encode()).hexdigest()[:16]
    return cache_dir_resolver() / f'{key}.mp3'


def count_cached(
    examples: list,
    *,
    alternating_voices: list[str],
    cache_file_path_resolver,
) -> int:
    cached = 0
    for example in examples:
        sentence = example['sentence']
        for voice_id in alternating_voices:
            if cache_file_path_resolver(sentence, voice_id).exists():
                cached += 1
                break
    return cached


def progress_file(cache_dir_resolver, book_id: str):
    return cache_dir_resolver() / f'progress_{book_id}.json'


def read_progress(book_id: str, *, progress_file_resolver) -> dict | None:
    path = progress_file_resolver(book_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def write_progress(book_id: str, total: int, completed: int, status: str, *, progress_file_resolver):
    progress_file_resolver(book_id).write_text(json.dumps({
        'total': total,
        'completed': completed,
        'status': status,
        'updated_at': datetime.utcnow().isoformat(),
    }))


def generate_for_book(
    book_id: str,
    examples: list,
    *,
    count_cached_resolver,
    write_progress_resolver,
    alternating_voices: list[str],
    cache_file_path_resolver,
    call_tts_api,
    sleep_fn,
    generating_books: set,
):
    total = len(examples)
    completed = count_cached_resolver(book_id, examples)
    write_progress_resolver(book_id, total, completed, 'running')

    try:
        for example in examples:
            sentence = example['sentence']
            already_cached = any(
                cache_file_path_resolver(sentence, voice_id).exists()
                for voice_id in alternating_voices
            )
            if already_cached:
                continue

            for voice_id in alternating_voices:
                target_path = cache_file_path_resolver(sentence, voice_id)
                if target_path.exists():
                    continue
                try:
                    call_tts_api(sentence, voice_id, target_path)
                except Exception as exc:
                    print(f'[TTS Gen Error] {sentence[:40]}: {exc}')
                sleep_fn(1.5)

            completed += 1
            if completed % 5 == 0 or completed == total:
                write_progress_resolver(book_id, total, completed, 'running')

        write_progress_resolver(book_id, total, total, 'done')
    except Exception as exc:
        print(f'[TTS Gen Fatal] book={book_id}: {exc}')
        write_progress_resolver(book_id, total, completed, 'error')
        raise
    finally:
        generating_books.discard(book_id)
