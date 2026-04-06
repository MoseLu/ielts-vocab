from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
THIS_FILE = Path(__file__).resolve()
TEXT_FILE_SUFFIXES = {'.py', '.ts', '.tsx', '.scss', '.md', '.json', '.yml', '.yaml', '.toml'}
SKIP_PARTS = {
    'node_modules',
    'dist',
    '.git',
    '__pycache__',
    '.pytest_cache',
    'test-results',
    'tts_cache',
    'word_tts_cache',
}
ASCII_ONLY_FILES = (
    REPO_ROOT / 'frontend' / 'vite.config.ts',
    REPO_ROOT / 'backend' / 'app.py',
)
MOJIBAKE_TOKENS = (
    '\u741b\u30e5\u5396\u93bb\u612e\u305a',
    '\u95c6\u546e',
    '\u59dd\uff45\u6e6a',
    '\u6748\u64b3\u53c6',
    '\u934f\u62bd\u68f4',
    '\u6769\u6a3a\u5e2b',
    '\u9366\u3127\u568e',
    '\u9354\u2542\u589c',
    '\u699b\u6a3f',
    '\u93c5\u6c2b\u7b02',
    '\u9422\u3126\u57db\u93b5\u64b3\u7d11',
    '\u6fb6\u5d85\u57d7',
    '\u951b',
    '\u9225',
    '\u9239',
    '\ufffd',
)


def iter_text_files():
    for path in REPO_ROOT.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in TEXT_FILE_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.resolve() == THIS_FILE:
            continue
        yield path


def test_repo_text_files_do_not_contain_mojibake_tokens():
    offenders: list[str] = []

    for path in iter_text_files():
        text = path.read_text(encoding='utf-8')
        for line_number, line in enumerate(text.splitlines(), 1):
            has_mojibake_token = any(token in line for token in MOJIBAKE_TOKENS)
            has_kana = any(0x3040 <= ord(ch) <= 0x30FF for ch in line)
            if has_mojibake_token or has_kana:
                offenders.append(f'{path.relative_to(REPO_ROOT)}:{line_number}: {line.strip()}')

    assert offenders == []


def test_infrastructure_files_use_ascii_only_text():
    offenders: list[str] = []

    for path in ASCII_ONLY_FILES:
        text = path.read_text(encoding='utf-8')
        for line_number, line in enumerate(text.splitlines(), 1):
            if any(ord(ch) > 127 for ch in line):
                offenders.append(f'{path.relative_to(REPO_ROOT)}:{line_number}: {line}')

    assert offenders == []
