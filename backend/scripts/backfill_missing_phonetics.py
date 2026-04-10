from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app
from services import phonetic_lookup_service
from services.word_catalog_service_parts.seed_index import build_word_seed_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Backfill missing word phonetics into phonetic_overrides.json')
    parser.add_argument('--limit', type=int, default=0, help='Only process the first N unresolved words')
    parser.add_argument('--workers', type=int, default=16, help='Concurrent remote lookups')
    return parser.parse_args()


def build_pending_words(limit: int) -> list[str]:
    seeds = build_word_seed_index()
    display_words = [
        seed['display_word'] or seed['word']
        for seed in seeds.values()
        if not phonetic_lookup_service.normalize_phonetic_text(seed.get('phonetic'))
    ]
    local_hits = phonetic_lookup_service.lookup_local_phonetics(display_words)
    pending_words = [
        word
        for word in display_words
        if phonetic_lookup_service.normalize_word_key(word) not in local_hits
    ]
    if limit > 0:
        return pending_words[:limit]
    return pending_words


def main() -> int:
    args = parse_args()
    with app.app_context():
        pending_words = build_pending_words(args.limit)
        if not pending_words:
            print('No unresolved missing phonetics found.')
            return 0

        print(f'Pending remote phonetic lookups: {len(pending_words)}')
        updates: dict[str, str] = {}
        completed = 0

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {
                executor.submit(phonetic_lookup_service.fetch_remote_phonetic, word): word
                for word in pending_words
            }
            for future in as_completed(futures):
                word = futures[future]
                completed += 1
                phonetic = future.result() or ''
                normalized_word = phonetic_lookup_service.normalize_word_key(word)
                if phonetic and normalized_word:
                    updates[normalized_word] = phonetic

                if completed % 100 == 0 or completed == len(pending_words):
                    print(
                        f'Processed {completed}/{len(pending_words)} words; '
                        f'new phonetics: {len(updates)}'
                    )

        if not updates:
            print('No remote phonetics resolved.')
            return 0

        overrides = phonetic_lookup_service.load_phonetic_overrides().copy()
        overrides.update(updates)
        phonetic_lookup_service.save_phonetic_overrides(overrides)
        print(
            f'Saved {len(updates)} new phonetics to '
            f'{phonetic_lookup_service.get_phonetic_overrides_path()}'
        )
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
