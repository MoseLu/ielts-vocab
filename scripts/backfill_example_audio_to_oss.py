from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
TTS_MEDIA_SERVICE_PATH = REPO_ROOT / 'services' / 'tts-media-service'
for candidate in (BACKEND_PATH, SDK_PATH, TTS_MEDIA_SERVICE_PATH):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from platform_sdk.runtime_env import load_split_service_env

load_split_service_env(service_name='tts-media-service')

import runtime_helpers as runtime
from services.books_catalog_service import load_book_vocabulary
from services.books_registry_service import VOCAB_BOOKS
from services.tts_batch_generation_service import get_book_examples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Backfill locally cached example-audio MP3 files into Aliyun OSS.',
    )
    parser.add_argument(
        '--book-id',
        action='append',
        dest='book_ids',
        help='Limit the backfill to one or more vocabulary books.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only report what would be uploaded.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Stop after processing N distinct example-audio objects. 0 means no limit.',
    )
    return parser.parse_args()


def resolve_book_ids(selected: list[str] | None) -> list[str]:
    available = {book['id'] for book in VOCAB_BOOKS}
    if not selected:
        return [book['id'] for book in VOCAB_BOOKS]
    missing = [book_id for book_id in selected if book_id not in available]
    if missing:
        raise ValueError(f'Unknown book ids: {missing}')
    return selected


def iter_example_audio_records(book_ids: list[str]):
    seen_object_keys: set[str] = set()
    processed = 0
    for book_id in book_ids:
        examples = get_book_examples(book_id, load_book_vocabulary=load_book_vocabulary)
        for example in examples:
            sentence = str(example.get('sentence') or '').strip()
            if not sentence:
                continue
            model, voice = runtime.example_tts_identity(sentence)
            cache_file = runtime.example_cache_file(sentence, model, voice)
            object_key = runtime.example_audio_object_key(sentence, model, voice)
            if object_key in seen_object_keys:
                continue
            seen_object_keys.add(object_key)
            processed += 1
            yield {
                'index': processed,
                'book_id': book_id,
                'sentence': sentence,
                'model': model,
                'voice': voice,
                'cache_file': cache_file,
                'object_key': object_key,
            }


def main() -> int:
    args = parse_args()
    if not runtime.bucket_is_configured():
        raise RuntimeError('Aliyun OSS is not configured for tts-media-service.')

    book_ids = resolve_book_ids(args.book_ids)
    stats = {
        'already_in_oss': 0,
        'uploaded': 0,
        'would_upload': 0,
        'missing_local': 0,
        'invalid_local': 0,
        'upload_failed': 0,
    }

    for record in iter_example_audio_records(book_ids):
        if args.limit > 0 and record['index'] > args.limit:
            break

        sentence = record['sentence']
        model = record['model']
        voice = record['voice']
        cache_file = record['cache_file']
        object_key = record['object_key']

        if runtime.resolve_example_audio_oss_metadata(sentence, model, voice) is not None:
            stats['already_in_oss'] += 1
            continue

        if not cache_file.exists():
            stats['missing_local'] += 1
            continue

        if not runtime.is_probably_valid_mp3_file(cache_file):
            runtime.remove_invalid_cached_audio(cache_file)
            stats['invalid_local'] += 1
            continue

        if args.dry_run:
            print(f'[dry-run] upload {object_key} from {cache_file}')
            stats['would_upload'] += 1
            continue

        metadata = runtime.put_example_audio_oss_bytes(
            sentence,
            model,
            voice,
            cache_file.read_bytes(),
        )
        if metadata is None:
            print(f'[failed] {object_key} from {cache_file}')
            stats['upload_failed'] += 1
            continue

        print(f'[uploaded] {metadata.object_key} ({metadata.byte_length} bytes)')
        stats['uploaded'] += 1

    print('Summary:')
    for key, value in stats.items():
        print(f'  {key}: {value}')
    return 1 if stats['upload_failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
