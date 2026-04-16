from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from urllib.parse import quote

import fitz


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
for candidate in (BACKEND_PATH, SDK_PATH):
    candidate_text = str(candidate)
    if candidate_text not in sys.path:
        sys.path.insert(0, candidate_text)

from platform_sdk.runtime_env import load_split_service_env
from services.exam_import_github_support import parse_part_number, parse_series_number, parse_test_number
from services.exam_import_parsing import _build_deterministic_papers


DEFAULT_LOCAL_REPO = REPO_ROOT.parent / 'IELTS'
DEFAULT_AUDIO_DIR = '雅思真题音频'
PUBLIC_REPO_OWNER = 'vaakian'
PUBLIC_REPO_NAME = 'IELTS'
PUBLIC_REPO_REF = 'main'

QUESTION_BLOCK_RE = re.compile(
    r'Questions?\s+(\d{1,2})(?:\s*(?:-|to)\s*(\d{1,2})|\s*(?:and|&)\s*(\d{1,2}))?',
    re.IGNORECASE,
)
TEST_RE = re.compile(r'\bTest\s+([1-4])\b', re.IGNORECASE)
LETTER_CHOICE_RE = re.compile(r'^([A-H])\s{1,}(.*)$')
ANSWER_ENTRY_RE = re.compile(r'^\s*(\d{1,2})\s+(.+?)\s*$')

PDF_EXCLUDE_TOKENS = (
    '体验版',
    'general',
    'gt',
    '培训类',
    '移民',
    'g类',
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Preload local IELTS Academic PDFs into the exam tables.')
    parser.add_argument(
        '--repo-root',
        default=str(DEFAULT_LOCAL_REPO),
        help='Local checkout root that contains the Cambridge IELTS PDFs and audio directory.',
    )
    return parser.parse_args()


def is_academic_pdf(path: Path) -> bool:
    lowered = path.name.lower()
    return not any(token in lowered for token in PDF_EXCLUDE_TOKENS)


def normalize_text(text: str) -> str:
    return re.sub(r'\r\n?', '\n', str(text or '')).strip()


def text_to_html(text: str) -> str:
    blocks = [block.strip() for block in normalize_text(text).split('\n\n') if block.strip()]
    if not blocks:
        return ''
    return ''.join(
        f"<p>{html.escape(block).replace(chr(10), '<br/>')}</p>"
        for block in blocks
    )


def public_urls(root: Path, path: Path) -> tuple[str, str]:
    relative = path.relative_to(root).as_posix()
    encoded = '/'.join(quote(part) for part in relative.split('/'))
    return (
        f'https://raw.githubusercontent.com/{PUBLIC_REPO_OWNER}/{PUBLIC_REPO_NAME}/{PUBLIC_REPO_REF}/{encoded}',
        f'https://github.com/{PUBLIC_REPO_OWNER}/{PUBLIC_REPO_NAME}/blob/{PUBLIC_REPO_REF}/{encoded}',
    )


def detect_test_number(text: str, current_test_number: int | None) -> int | None:
    match = TEST_RE.search(text[:1200])
    if match:
        return int(match.group(1))
    return current_test_number


def detect_section_type(text: str, current_section_type: str | None) -> str:
    upper = text.upper()
    if 'ANSWER KEY' in upper or 'ANSWER KEYS' in upper or 'LISTENING ANSWERS' in upper or 'READING ANSWERS' in upper:
        return 'answer_key'
    if 'LISTENING' in upper:
        return 'listening'
    if 'READING' in upper:
        return 'reading'
    if 'WRITING' in upper:
        return 'writing'
    if 'SPEAKING' in upper:
        return 'speaking'
    return current_section_type or 'unknown'


def detect_question_type(block_text: str, section_type: str) -> str:
    upper = block_text.upper()
    if section_type == 'writing':
        return 'writing_prompt'
    if section_type == 'speaking':
        return 'speaking_prompt'
    if 'TRUE/FALSE/NOT GIVEN' in upper or 'YES/NO/NOT GIVEN' in upper:
        return 'single_choice'
    if 'CHOOSE TWO' in upper or 'CHOOSE THREE' in upper:
        return 'multiple_choice'
    if 'CHOOSE THE CORRECT LETTER' in upper or 'A, B OR C' in upper or 'A, B, C OR D' in upper:
        return 'single_choice'
    if 'MATCH' in upper or 'WHICH PARAGRAPH' in upper or 'WHICH SECTION' in upper or 'CHOOSE YOUR ANSWERS FROM THE BOX' in upper:
        return 'matching'
    if 'WRITE NO MORE THAN' in upper or 'COMPLETE THE' in upper or 'LABEL THE' in upper or 'WRITE ONE WORD' in upper:
        return 'fill_blank'
    return 'short_answer'


def fixed_choices(block_text: str, question_type: str) -> list[dict]:
    upper = block_text.upper()
    if 'TRUE/FALSE/NOT GIVEN' in upper:
        return [
            {'key': 'TRUE', 'label': 'A', 'contentHtml': '<p>TRUE</p>'},
            {'key': 'FALSE', 'label': 'B', 'contentHtml': '<p>FALSE</p>'},
            {'key': 'NOT_GIVEN', 'label': 'C', 'contentHtml': '<p>NOT GIVEN</p>'},
        ]
    if 'YES/NO/NOT GIVEN' in upper:
        return [
            {'key': 'YES', 'label': 'A', 'contentHtml': '<p>YES</p>'},
            {'key': 'NO', 'label': 'B', 'contentHtml': '<p>NO</p>'},
            {'key': 'NOT_GIVEN', 'label': 'C', 'contentHtml': '<p>NOT GIVEN</p>'},
        ]
    if question_type not in {'single_choice', 'multiple_choice', 'matching'}:
        return []

    choices: list[dict] = []
    for line in normalize_text(block_text).splitlines():
        match = LETTER_CHOICE_RE.match(line.strip())
        if not match:
            continue
        key = match.group(1).strip()
        content = match.group(2).strip()
        if not content:
            continue
        choices.append({
            'key': key,
            'label': key,
            'contentHtml': f'<p>{html.escape(content)}</p>',
        })
    return choices


def answer_entries_from_page(text: str) -> list[dict]:
    entries: list[dict] = []
    for line in normalize_text(text).splitlines():
        match = ANSWER_ENTRY_RE.match(line)
        if not match:
            continue
        question_number = int(match.group(1))
        if question_number < 1 or question_number > 40:
            continue
        answer = match.group(2).strip()
        if not answer or len(answer) > 120:
            continue
        entries.append({'questionNumber': question_number, 'answers': [answer]})
    return entries


def questions_from_page(text: str, section_type: str, page_number: int) -> list[dict]:
    matches = list(QUESTION_BLOCK_RE.finditer(text))
    if not matches and section_type in {'writing', 'speaking'}:
        return [{
            'questionNumber': page_number,
            'questionType': detect_question_type(text, section_type),
            'promptHtml': text_to_html(text),
            'choices': [],
            'answers': [],
            'groupKey': f'{section_type}-{page_number}',
            'confidence': 0.72,
            'metadata': {'sourcePage': page_number},
        }]

    questions: list[dict] = []
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block_text = normalize_text(text[match.start():next_start])
        if not block_text:
            continue
        range_end = match.group(2) or match.group(3) or match.group(1)
        start_number = int(match.group(1))
        end_number = int(range_end)
        prompt_html = text_to_html(block_text)
        question_type = detect_question_type(block_text, section_type)
        choices = fixed_choices(block_text, question_type)
        for question_number in range(start_number, end_number + 1):
            questions.append({
                'questionNumber': question_number,
                'questionType': question_type,
                'promptHtml': prompt_html,
                'choices': choices,
                'answers': [],
                'groupKey': f'{section_type}-{page_number}-{start_number}-{end_number}',
                'confidence': 0.72,
                'metadata': {'sourcePage': page_number},
            })
    return questions


def page_records_from_pdf(pdf_path: Path) -> list[dict]:
    current_test_number: int | None = None
    current_section_type: str | None = None
    page_records: list[dict] = []

    document = fitz.open(pdf_path)
    try:
        for page_index in range(document.page_count):
            page_number = page_index + 1
            text = normalize_text(document.load_page(page_index).get_text('text'))
            if not text:
                continue
            current_test_number = detect_test_number(text, current_test_number)
            current_section_type = detect_section_type(text, current_section_type)
            page_role = 'answer_key' if current_section_type == 'answer_key' else 'content'
            answer_entries = answer_entries_from_page(text) if page_role == 'answer_key' else []
            questions = [] if page_role == 'answer_key' else questions_from_page(text, current_section_type, page_number)
            page_records.append({
                'pageNumber': page_number,
                'testNumber': current_test_number,
                'sectionType': current_section_type,
                'pageRole': page_role,
                'heading': text.splitlines()[0].strip() if text.splitlines() else '',
                'html': text_to_html(text),
                'passages': [],
                'questions': questions,
                'answerEntries': answer_entries,
                'confidence': 0.72,
            })
    finally:
        document.close()
    return page_records


def audio_inventory_from_local_repo(root: Path, audio_root: Path) -> dict[tuple[int, int], list[dict]]:
    from services.exam_import_service import _section_audio_inventory

    items: list[dict] = []
    for audio_path in sorted(audio_root.rglob('*')):
        if not audio_path.is_file():
            continue
        if audio_path.suffix.lower() not in {'.mp3', '.m4a', '.wav', '.aac', '.ogg'}:
            continue
        download_url, html_url = public_urls(root, audio_path)
        relative = audio_path.relative_to(root).as_posix()
        items.append({
            'name': audio_path.name,
            'path': relative,
            'size': audio_path.stat().st_size,
            'download_url': download_url,
            'html_url': html_url,
            'series_number': parse_series_number(relative),
            'test_number': parse_test_number(relative),
            'part_number': parse_part_number(relative),
        })
    return _section_audio_inventory(items)


def pdf_item_from_local_repo(root: Path, pdf_path: Path) -> dict:
    download_url, html_url = public_urls(root, pdf_path)
    return {
        'name': pdf_path.name,
        'path': pdf_path.relative_to(root).as_posix(),
        'size': pdf_path.stat().st_size,
        'download_url': download_url,
        'html_url': html_url,
    }


def upsert_source(root: Path, audio_root: Path) -> ExamSource:
    from models import ExamSource
    from service_models.admin_ops_models import db

    source = ExamSource.query.filter_by(source_url=str(root.resolve())).first()
    if source is None:
        source = ExamSource(
            source_type='local_git_checkout',
            source_url=str(root.resolve()),
            owner=PUBLIC_REPO_OWNER,
            repo=PUBLIC_REPO_NAME,
            ref=PUBLIC_REPO_REF,
            rights_status='restricted_internal',
        )
        db.session.add(source)
        db.session.flush()
    source.root_path = str(root.resolve())
    source.audio_root_path = str(audio_root.resolve())
    source.rights_status = 'restricted_internal'
    source.set_metadata({
        'publicRepoUrl': f'https://github.com/{PUBLIC_REPO_OWNER}/{PUBLIC_REPO_NAME}',
    })
    db.session.flush()
    return source


def preload_academic_exams(root: Path) -> dict:
    from platform_sdk.admin_ops_runtime import create_admin_ops_flask_app
    from platform_sdk.service_schema import bootstrap_service_schema
    from service_models.admin_ops_models import db
    from services.exam_import_service import _persist_paper_structure, _section_audio_inventory
    from models import ExamSource

    audio_root = root / DEFAULT_AUDIO_DIR
    if not root.exists():
        raise FileNotFoundError(f'Local IELTS repo not found: {root}')
    if not audio_root.exists():
        raise FileNotFoundError(f'Audio directory not found: {audio_root}')

    app = create_admin_ops_flask_app()
    with app.app_context():
        bootstrap_service_schema('admin-ops-service')
        source = upsert_source(root, audio_root)
        audio_inventory = audio_inventory_from_local_repo(root, audio_root)
        pdf_paths = [path for path in sorted(root.glob('*.pdf')) if is_academic_pdf(path)]
        imported = []
        for pdf_path in pdf_paths:
            page_records = page_records_from_pdf(pdf_path)
            papers = _build_deterministic_papers(filename=pdf_path.name, page_records=page_records)
            pdf_item = pdf_item_from_local_repo(root, pdf_path)
            for paper_payload in papers:
                paper = _persist_paper_structure(
                    source=source,
                    paper_payload=paper_payload,
                    pdf_item=pdf_item,
                    audio_inventory=audio_inventory,
                )
                if paper.sections:
                    paper.publish_status = 'published_internal'
                imported.append({
                    'paper_id': paper.id,
                    'collection_title': paper.collection_title,
                    'title': paper.title,
                    'series_number': paper.series_number,
                    'test_number': paper.test_number,
                    'publish_status': paper.publish_status,
                    'question_count': sum(len(section.questions) for section in paper.sections),
                })
            db.session.commit()
        return {
            'pdf_count': len(pdf_paths),
            'paper_count': len(imported),
            'papers': imported,
        }


def main() -> int:
    args = parse_args()
    load_split_service_env(service_name='admin-ops-service')
    summary = preload_academic_exams(Path(args.repo_root))
    print(summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
