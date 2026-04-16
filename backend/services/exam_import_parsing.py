from __future__ import annotations

import html
import statistics
import tempfile
from pathlib import Path
from urllib.parse import urlparse, unquote

import fitz
import requests

from services.exam_import_github_support import collection_title_from_series, parse_series_number, parse_test_number
from services.exam_llm_support import (
    ExamLLMError,
    exam_llm_available,
    exam_page_model,
    exam_stitch_model,
    request_multimodal_json,
    request_text_json,
)


PAGE_BATCH_SIZE = 4
PAGE_RENDER_SCALE = 1.6
TEXT_PAGE_CHAR_LIMIT = 6000


def _download_pdf(pdf_url: str) -> str:
    parsed = urlparse(str(pdf_url or '').strip())
    if parsed.scheme == 'file':
        local_path = Path(unquote(parsed.path)).resolve()
        if local_path.exists():
            return str(local_path)
    candidate = Path(str(pdf_url or '').strip())
    if candidate.exists():
        return str(candidate.resolve())
    response = requests.get(pdf_url, timeout=120)
    response.raise_for_status()
    handle = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    handle.write(response.content)
    handle.flush()
    handle.close()
    return handle.name


def _render_page_png(page, output_dir: Path, page_number: int) -> str:
    matrix = fitz.Matrix(PAGE_RENDER_SCALE, PAGE_RENDER_SCALE)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    output_path = output_dir / f'page-{page_number:03d}.png'
    pixmap.save(output_path)
    return str(output_path)


def _page_prompt(filename: str, page_numbers: list[int]) -> str:
    return (
        'You convert scanned IELTS exam pages into structured JSON. '
        'Return only a JSON array with the same length as the provided images. '
        'For each page return pageNumber, testNumber, sectionType, pageRole, heading, html, passages, questions, answerEntries, confidence. '
        'sectionType must be one of listening, reading, writing, speaking, answer_key, unknown. '
        'pageRole must be one of content, answer_key, cover, intro, blank, other. '
        'passages is an array of {title, html}. '
        'questions is an array of {questionNumber, questionType, promptHtml, choices, answers, groupKey}. '
        'questionType must be one of single_choice, multiple_choice, matching, fill_blank, short_answer, writing_prompt, speaking_prompt. '
        'choices is an array of {key, label, contentHtml}. '
        'answerEntries is an array of {questionNumber, answers}. '
        f'Source filename: {filename}. Absolute page numbers in this batch: {page_numbers}.'
    )


def _page_text_prompt(filename: str, page_payloads: list[tuple[int, str]]) -> str:
    joined_pages = '\n\n'.join(
        f'=== PAGE {page_number} START ===\n{text[:TEXT_PAGE_CHAR_LIMIT]}\n=== PAGE {page_number} END ==='
        for page_number, text in page_payloads
    )
    return (
        'You convert text-extracted IELTS exam pages into structured JSON. '
        'Return only a JSON array with the same length and order as the provided pages. '
        'For each page return pageNumber, testNumber, sectionType, pageRole, heading, html, passages, questions, answerEntries, confidence. '
        'sectionType must be one of listening, reading, writing, speaking, answer_key, unknown. '
        'pageRole must be one of content, answer_key, cover, intro, blank, other. '
        'passages is an array of {title, html}. '
        'questions is an array of {questionNumber, questionType, promptHtml, choices, answers, groupKey}. '
        'questionType must be one of single_choice, multiple_choice, matching, fill_blank, short_answer, writing_prompt, speaking_prompt. '
        'choices is an array of {key, label, contentHtml}. '
        'answerEntries is an array of {questionNumber, answers}. '
        f'Source filename: {filename}. '
        f'Input pages:\n{joined_pages}'
    )


def _stitch_prompt(filename: str, page_records: list[dict]) -> str:
    return (
        'You are stitching page-level IELTS parse records into paper-level structured JSON. '
        'Return only a JSON object with shape {"papers": [...]} . '
        'Each paper must contain seriesNumber, testNumber, collectionTitle, title, examKind, importConfidence, answerKeyConfidence, sections. '
        'Each section must contain sectionType, title, instructionsHtml, htmlContent, confidence, passages, questions. '
        'Each passage must contain title, htmlContent, sourcePageFrom, sourcePageTo, confidence. '
        'Each question must contain questionNumber, questionType, promptHtml, choices, answers, confidence, groupKey. '
        'Use the page records as the source of truth, dedupe duplicate question numbers, and attach answer keys from answer pages to matching questions when possible. '
        f'Source filename: {filename}. Page records JSON: {page_records}'
    )


def _normalize_question(raw_question: dict, *, page_number: int) -> dict:
    choices = raw_question.get('choices') if isinstance(raw_question.get('choices'), list) else []
    answers = raw_question.get('answers') if isinstance(raw_question.get('answers'), list) else []
    try:
        question_number = int(raw_question.get('questionNumber'))
    except (TypeError, ValueError):
        question_number = None
    return {
        'questionNumber': question_number,
        'questionType': str(raw_question.get('questionType') or 'short_answer').strip() or 'short_answer',
        'promptHtml': str(raw_question.get('promptHtml') or '').strip(),
        'choices': [
            {
                'key': str(choice.get('key') or '').strip(),
                'label': str(choice.get('label') or '').strip() or None,
                'contentHtml': str(choice.get('contentHtml') or '').strip(),
            }
            for choice in choices
            if isinstance(choice, dict)
        ],
        'answers': [str(answer).strip() for answer in answers if str(answer).strip()],
        'groupKey': str(raw_question.get('groupKey') or f'page-{page_number}').strip(),
        'confidence': float(raw_question.get('confidence') or 0),
        'metadata': {'sourcePage': page_number},
    }


def _normalize_page_record(raw_record, *, page_number: int) -> dict:
    if not isinstance(raw_record, dict):
        return {
            'pageNumber': page_number,
            'testNumber': None,
            'sectionType': 'unknown',
            'pageRole': 'other',
            'heading': '',
            'html': '',
            'passages': [],
            'questions': [],
            'answerEntries': [],
            'confidence': 0,
        }
    passages = raw_record.get('passages') if isinstance(raw_record.get('passages'), list) else []
    answer_entries = raw_record.get('answerEntries') if isinstance(raw_record.get('answerEntries'), list) else []
    return {
        'pageNumber': page_number,
        'testNumber': raw_record.get('testNumber'),
        'sectionType': str(raw_record.get('sectionType') or 'unknown').strip() or 'unknown',
        'pageRole': str(raw_record.get('pageRole') or 'other').strip() or 'other',
        'heading': str(raw_record.get('heading') or '').strip(),
        'html': str(raw_record.get('html') or '').strip(),
        'passages': [
            {
                'title': str(passage.get('title') or '').strip() or None,
                'html': str(passage.get('html') or '').strip(),
                'sourcePage': page_number,
            }
            for passage in passages
            if isinstance(passage, dict) and str(passage.get('html') or '').strip()
        ],
        'questions': [
            _normalize_question(question, page_number=page_number)
            for question in (raw_record.get('questions') if isinstance(raw_record.get('questions'), list) else [])
            if isinstance(question, dict)
        ],
        'answerEntries': [
            {
                'questionNumber': int(entry.get('questionNumber')),
                'answers': [str(answer).strip() for answer in (entry.get('answers') or []) if str(answer).strip()],
            }
            for entry in answer_entries
            if isinstance(entry, dict) and entry.get('questionNumber') is not None
        ],
        'confidence': float(raw_record.get('confidence') or 0),
    }


def _fallback_record(*, page_number: int, extracted_text: str) -> dict:
    cleaned = ' '.join(str(extracted_text or '').split())
    html_content = f'<p>{html.escape(cleaned[:1200])}</p>' if cleaned else ''
    return {
        'pageNumber': page_number,
        'testNumber': parse_test_number(cleaned),
        'sectionType': 'unknown',
        'pageRole': 'other',
        'heading': '',
        'html': html_content,
        'passages': [],
        'questions': [],
        'answerEntries': [],
        'confidence': 0.2 if html_content else 0,
    }


def _parse_page_batches(*, doc, filename: str, output_dir: Path) -> list[dict]:
    page_records: list[dict] = []
    for batch_start in range(0, doc.page_count, PAGE_BATCH_SIZE):
        pages = [
            doc.load_page(index)
            for index in range(batch_start, min(batch_start + PAGE_BATCH_SIZE, doc.page_count))
        ]
        page_numbers = [batch_start + offset + 1 for offset in range(len(pages))]
        extracted_text = [page.get_text('text') for page in pages]
        batch_records: list[dict] = []
        if exam_llm_available():
            try:
                page_payloads = [
                    (page_number, text)
                    for page_number, text in zip(page_numbers, extracted_text)
                    if str(text or '').strip()
                ]
                response = request_text_json(
                    model=exam_page_model(),
                    prompt=_page_text_prompt(filename, page_payloads or list(zip(page_numbers, extracted_text))),
                )
                if isinstance(response, list):
                    batch_records = [
                        _normalize_page_record(item, page_number=page_number)
                        for item, page_number in zip(response, page_numbers)
                    ]
            except (ExamLLMError, ValueError, TypeError):
                batch_records = []
        if len(batch_records) != len(page_numbers) and exam_llm_available():
            try:
                image_paths = [_render_page_png(page, output_dir, page_number) for page, page_number in zip(pages, page_numbers)]
                response = request_multimodal_json(
                    model=exam_page_model(),
                    image_paths=image_paths,
                    prompt=_page_prompt(filename, page_numbers),
                )
                if isinstance(response, list):
                    batch_records = [
                        _normalize_page_record(item, page_number=page_number)
                        for item, page_number in zip(response, page_numbers)
                    ]
            except (ExamLLMError, ValueError, TypeError):
                batch_records = []
        if len(batch_records) != len(page_numbers):
            batch_records = [
                _fallback_record(page_number=page_number, extracted_text=text)
                for page_number, text in zip(page_numbers, extracted_text)
            ]
        page_records.extend(batch_records)
    return page_records


def _merge_answer_entries(questions_by_number: dict[int, dict], answer_entries: list[dict]) -> None:
    for entry in answer_entries:
        question_number = entry.get('questionNumber')
        if not isinstance(question_number, int) or question_number not in questions_by_number:
            continue
        question = questions_by_number[question_number]
        answers = [answer for answer in entry.get('answers') or [] if answer]
        if answers and not question['answers']:
            question['answers'] = answers


def _build_deterministic_papers(*, filename: str, page_records: list[dict]) -> list[dict]:
    series_number = parse_series_number(filename)
    grouped: dict[int, dict] = {}
    for record in page_records:
        test_number = record.get('testNumber')
        if not isinstance(test_number, int):
            continue
        paper = grouped.setdefault(test_number, {
            'seriesNumber': series_number,
            'testNumber': test_number,
            'collectionTitle': collection_title_from_series(series_number),
            'title': f'Test {test_number}',
            'examKind': 'academic',
            'sectionsByType': {},
            'confidenceValues': [],
            'answerValues': [],
        })
        section_type = str(record.get('sectionType') or 'unknown').strip() or 'unknown'
        if section_type == 'answer_key':
            paper['answerValues'].append(float(record.get('confidence') or 0))
            for section in paper['sectionsByType'].values():
                _merge_answer_entries(section['questionsByNumber'], record.get('answerEntries') or [])
            continue
        section = paper['sectionsByType'].setdefault(section_type, {
            'sectionType': section_type,
            'title': section_type.title(),
            'instructionsHtml': '',
            'htmlParts': [],
            'confidenceValues': [],
            'passages': [],
            'questionsByNumber': {},
            'questionList': [],
            'sourcePages': [],
        })
        if not section['instructionsHtml'] and record.get('heading'):
            section['instructionsHtml'] = f"<p>{html.escape(record['heading'])}</p>"
        if record.get('html'):
            section['htmlParts'].append(record['html'])
        section['confidenceValues'].append(float(record.get('confidence') or 0))
        section['sourcePages'].append(int(record['pageNumber']))
        section['passages'].extend([
            {
                'title': passage.get('title'),
                'htmlContent': passage.get('html') or '',
                'sourcePageFrom': passage.get('sourcePage'),
                'sourcePageTo': passage.get('sourcePage'),
                'confidence': float(record.get('confidence') or 0),
            }
            for passage in record.get('passages') or []
            if passage.get('html')
        ])
        for question in record.get('questions') or []:
            question_number = question.get('questionNumber')
            if not isinstance(question_number, int):
                continue
            existing = section['questionsByNumber'].get(question_number)
            if existing is None:
                section['questionsByNumber'][question_number] = question
                section['questionList'].append(question)
                continue
            if not existing['promptHtml'] and question['promptHtml']:
                existing['promptHtml'] = question['promptHtml']
            if not existing['answers'] and question['answers']:
                existing['answers'] = question['answers']
            if not existing['choices'] and question['choices']:
                existing['choices'] = question['choices']
            existing['confidence'] = max(float(existing.get('confidence') or 0), float(question.get('confidence') or 0))
        paper['confidenceValues'].append(float(record.get('confidence') or 0))
    papers: list[dict] = []
    for test_number in sorted(grouped):
        paper = grouped[test_number]
        sections = []
        for sort_order, section_type in enumerate(('listening', 'reading', 'writing', 'speaking', 'unknown'), start=1):
            section = paper['sectionsByType'].get(section_type)
            if not section:
                continue
            questions = sorted(section['questionList'], key=lambda item: (item.get('questionNumber') or 0, item.get('groupKey') or ''))
            sections.append({
                'sectionType': section_type,
                'title': section['title'],
                'instructionsHtml': section['instructionsHtml'],
                'htmlContent': '\n'.join(section['htmlParts']).strip(),
                'confidence': round(statistics.fmean(section['confidenceValues']), 4) if section['confidenceValues'] else 0,
                'passages': section['passages'],
                'questions': questions,
                'metadata': {'sourcePages': sorted(set(section['sourcePages']))},
                'sortOrder': sort_order,
            })
        papers.append({
            'seriesNumber': paper['seriesNumber'],
            'testNumber': paper['testNumber'],
            'collectionTitle': paper['collectionTitle'],
            'title': paper['title'],
            'examKind': paper['examKind'],
            'importConfidence': round(statistics.fmean(paper['confidenceValues']), 4) if paper['confidenceValues'] else 0,
            'answerKeyConfidence': round(statistics.fmean(paper['answerValues']), 4) if paper['answerValues'] else 0,
            'sections': sections,
        })
    return papers


def _repair_with_stitch_model(*, filename: str, page_records: list[dict], papers: list[dict]) -> list[dict]:
    if not exam_llm_available() or not papers:
        return papers
    try:
        payload = request_text_json(
            model=exam_stitch_model(),
            prompt=_stitch_prompt(filename, page_records),
        )
    except (ExamLLMError, ValueError, TypeError):
        return papers
    candidate_papers = payload.get('papers') if isinstance(payload, dict) else None
    if not isinstance(candidate_papers, list) or not candidate_papers:
        return papers
    return candidate_papers


def parse_exam_pdf(*, pdf_url: str, filename: str) -> dict:
    pdf_path = _download_pdf(pdf_url)
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            doc = fitz.open(pdf_path)
            try:
                page_records = _parse_page_batches(doc=doc, filename=filename, output_dir=Path(temp_dir))
            finally:
                doc.close()
            papers = _build_deterministic_papers(filename=filename, page_records=page_records)
            papers = _repair_with_stitch_model(filename=filename, page_records=page_records, papers=papers)
            return {
                'pageRecords': page_records,
                'papers': papers,
            }
    finally:
        try:
            Path(pdf_path).unlink(missing_ok=True)
        except OSError:
            pass
