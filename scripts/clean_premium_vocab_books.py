from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / 'backend'
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.premium_vocab_cleanup import (  # noqa: E402
    TARGET_PREMIUM_BOOK_FILES,
    VOCAB_ROOT,
    clean_premium_book_payload,
    clean_premium_book_file,
    load_curated_base_word_set,
)


def main() -> int:
    parser = argparse.ArgumentParser(description='Clean premium IELTS vocabulary books.')
    parser.add_argument('--check', action='store_true', help='Only report pending cleanup.')
    parser.add_argument(
        '--from-git-head',
        action='store_true',
        help='Rebuild premium books from the current git HEAD version before cleaning.',
    )
    args = parser.parse_args()

    curated_base_words = load_curated_base_word_set(VOCAB_ROOT)
    dirty_files: list[str] = []

    for filename in TARGET_PREMIUM_BOOK_FILES:
        path = VOCAB_ROOT / filename
        original_text = path.read_text(encoding='utf-8')
        if args.from_git_head:
            git_rel_path = f'vocabulary_data/{filename}'
            raw_text = subprocess.run(
                ['git', 'show', f'HEAD:{git_rel_path}'],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True,
            ).stdout
            source_payload = json.loads(raw_text)
            cleaned_payload, stats = clean_premium_book_payload(
                source_payload,
                curated_base_words=curated_base_words,
            )
        else:
            cleaned_payload, stats = clean_premium_book_file(
                filename,
                curated_base_words=curated_base_words,
                vocab_root=VOCAB_ROOT,
            )
        cleaned_text = json.dumps(cleaned_payload, ensure_ascii=False, indent=2) + '\n'
        changed = cleaned_text != original_text
        if changed:
            dirty_files.append(filename)
            if not args.check:
                path.write_text(cleaned_text, encoding='utf-8')
        print(
            f'{filename}: '
            f'chapters {stats.source_chapters}->{stats.kept_chapters}, '
            f'words {stats.source_words}->{stats.kept_words}, '
            f'changed={str(changed).lower()}'
        )
        if stats.removed_reason_counts:
            print(f'  removed_reasons={stats.removed_reason_counts}')

    if args.check and dirty_files:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
