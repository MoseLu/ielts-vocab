from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from models import (
    ExamAnswerKey,
    ExamAsset,
    ExamChoice,
    ExamIngestionJob,
    ExamPaper,
    ExamPassage,
    ExamQuestion,
    ExamReviewItem,
    ExamSection,
    ExamSource,
    db,
)
from services.exam_import_github_support import (
    GitHubLocation,
    collection_title_from_series,
    discover_audio_files,
    discover_pdf_files,
    parse_github_location,
    parse_series_number,
)
from services.exam_import_parsing import parse_exam_pdf
from services.exam_llm_support import exam_page_model, exam_stitch_model


def _normalize_answer(value: str | None) -> str:
    return ''.join(char.lower() for char in str(value or '').strip() if char.isalnum())


def _paper_external_key(source: ExamSource, series_number: int | None, test_number: int | None) -> str:
    series_part = f's{series_number}' if series_number is not None else 's0'
    test_part = f't{test_number}' if test_number is not None else 't0'
    return f'github:{source.owner}/{source.repo}:{series_part}:{test_part}'


def _section_audio_inventory(audio_files: list[dict]) -> dict[tuple[int, int], list[dict]]:
    inventory: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for item in audio_files:
        series_number = item.get('series_number')
        test_number = item.get('test_number')
        if not isinstance(series_number, int) or not isinstance(test_number, int):
            continue
        inventory[(series_number, test_number)].append(item)
    for items in inventory.values():
        items.sort(key=lambda item: item.get('part_number') or 0)
    return inventory


def _clear_existing_paper_children(paper: ExamPaper) -> None:
    for review_item in list(paper.review_items):
        db.session.delete(review_item)
    for attempt in list(paper.attempts):
        db.session.delete(attempt)
    for section in list(paper.sections):
        section.audio_asset_id = None
    db.session.flush()
    for asset in list(paper.assets):
        db.session.delete(asset)
    for section in list(paper.sections):
        db.session.delete(section)
    db.session.flush()


def _attach_listening_audio(*, source: ExamSource, paper: ExamPaper, section: ExamSection, audio_files: list[dict]) -> bool:
    if section.section_type != 'listening' or not audio_files:
        return False
    tracks = []
    primary_asset_id = None
    for index, audio_file in enumerate(audio_files, start=1):
        part_number = audio_file.get('part_number')
        asset = ExamAsset(
            source_id=source.id,
            paper_id=paper.id,
            section_id=section.id,
            asset_key=f'{paper.external_key}:listening:part-{part_number or index}',
            asset_kind='audio',
            title=audio_file.get('name') or f'Part {part_number or index}',
            source_url=audio_file.get('download_url') or audio_file.get('html_url') or '',
            content_type='audio/mpeg',
        )
        asset.set_metadata({
            'seriesNumber': paper.series_number,
            'testNumber': paper.test_number,
            'partNumber': part_number or index,
            'htmlUrl': audio_file.get('html_url'),
            'sourcePath': audio_file.get('path'),
        })
        db.session.add(asset)
        db.session.flush()
        primary_asset_id = primary_asset_id or asset.id
        tracks.append({
            'assetId': asset.id,
            'partNumber': part_number or index,
            'title': asset.title,
            'sourceUrl': asset.source_url,
        })
    section.audio_asset_id = primary_asset_id
    metadata = section.metadata_dict()
    metadata['audioTracks'] = tracks
    section.set_metadata(metadata)
    return True


def _insert_review_item(*, paper: ExamPaper, section: ExamSection | None, question: ExamQuestion | None, item_type: str, severity: str, message: str, metadata: dict | None = None) -> None:
    review_item = ExamReviewItem(
        paper_id=paper.id,
        section_id=section.id if section else None,
        question_id=question.id if question else None,
        item_type=item_type,
        severity=severity,
        message=message,
    )
    review_item.set_metadata(metadata)
    db.session.add(review_item)


def _persist_paper_structure(*, source: ExamSource, paper_payload: dict, pdf_item: dict, audio_inventory: dict[tuple[int, int], list[dict]]) -> ExamPaper:
    series_number = paper_payload.get('seriesNumber')
    test_number = paper_payload.get('testNumber')
    normalized_series_number = int(series_number) if isinstance(series_number, int) else parse_series_number(pdf_item.get('name'))
    normalized_test_number = int(test_number) if isinstance(test_number, int) else None
    collection_title = str(paper_payload.get('collectionTitle') or collection_title_from_series(normalized_series_number))
    title = str(paper_payload.get('title') or f'Test {normalized_test_number or "?"}')
    exam_kind = str(paper_payload.get('examKind') or 'academic')
    import_confidence = float(paper_payload.get('importConfidence') or 0)
    answer_key_confidence = float(paper_payload.get('answerKeyConfidence') or 0)
    external_key = _paper_external_key(source, normalized_series_number, normalized_test_number)
    paper = ExamPaper.query.filter_by(
        external_key=external_key,
    ).first()
    if paper is None:
        paper = ExamPaper(
            source_id=source.id,
            external_key=external_key,
            collection_key=f'cambridge-{normalized_series_number or "unknown"}',
            collection_title=collection_title,
            title=title,
            exam_kind=exam_kind,
            series_number=normalized_series_number,
            test_number=normalized_test_number,
            parser_strategy='multimodal',
            rights_status=source.rights_status,
            import_confidence=import_confidence,
            answer_key_confidence=answer_key_confidence,
            publish_status='draft',
        )
        db.session.add(paper)
        db.session.flush()
    else:
        _clear_existing_paper_children(paper)
    paper.collection_key = f'cambridge-{normalized_series_number or "unknown"}'
    paper.collection_title = collection_title
    paper.title = title
    paper.exam_kind = exam_kind
    paper.series_number = normalized_series_number
    paper.test_number = normalized_test_number
    paper.parser_strategy = 'multimodal'
    paper.rights_status = source.rights_status
    paper.import_confidence = import_confidence
    paper.answer_key_confidence = answer_key_confidence
    paper.publish_status = 'draft'
    paper.set_metadata({
        'sourcePdfName': pdf_item.get('name'),
        'sourcePdfUrl': pdf_item.get('download_url'),
        'sourcePdfPath': pdf_item.get('path'),
    })
    db.session.flush()

    pdf_asset = ExamAsset(
        source_id=source.id,
        paper_id=paper.id,
        asset_key=f'{paper.external_key}:pdf',
        asset_kind='pdf',
        title=pdf_item.get('name'),
        source_url=pdf_item.get('download_url') or '',
        content_type='application/pdf',
        byte_length=int(pdf_item.get('size') or 0),
    )
    pdf_asset.set_metadata({'htmlUrl': pdf_item.get('html_url'), 'sourcePath': pdf_item.get('path')})
    db.session.add(pdf_asset)
    db.session.flush()

    matched_audio = audio_inventory.get((paper.series_number or 0, paper.test_number or 0), [])
    has_listening_audio = False

    for section_payload in paper_payload.get('sections') or []:
        section = ExamSection(
            paper_id=paper.id,
            section_type=str(section_payload.get('sectionType') or 'unknown'),
            sort_order=int(section_payload.get('sortOrder') or 0),
            title=str(section_payload.get('title') or str(section_payload.get('sectionType') or 'Section').title()),
            instructions_html=str(section_payload.get('instructionsHtml') or '').strip() or None,
            html_content=str(section_payload.get('htmlContent') or '').strip() or None,
            confidence=float(section_payload.get('confidence') or 0),
        )
        section.set_metadata(section_payload.get('metadata') or {})
        db.session.add(section)
        db.session.flush()

        if _attach_listening_audio(source=source, paper=paper, section=section, audio_files=matched_audio):
            has_listening_audio = True

        for passage_index, passage_payload in enumerate(section_payload.get('passages') or [], start=1):
            passage = ExamPassage(
                section_id=section.id,
                sort_order=passage_index,
                title=str(passage_payload.get('title') or '').strip() or None,
                html_content=str(passage_payload.get('htmlContent') or '').strip(),
                source_page_from=passage_payload.get('sourcePageFrom'),
                source_page_to=passage_payload.get('sourcePageTo'),
                confidence=float(passage_payload.get('confidence') or section.confidence or 0),
            )
            passage.set_metadata(passage_payload.get('metadata') or {})
            db.session.add(passage)

        db.session.flush()

        for question_index, question_payload in enumerate(section_payload.get('questions') or [], start=1):
            passage_id = None
            question_metadata = question_payload.get('metadata') or {}
            source_page = question_metadata.get('sourcePage')
            if source_page is not None:
                linked_passage = next(
                    (item for item in section.passages if item.source_page_from == source_page or item.source_page_to == source_page),
                    None,
                )
                passage_id = linked_passage.id if linked_passage else None
            question = ExamQuestion(
                section_id=section.id,
                passage_id=passage_id,
                group_key=str(question_payload.get('groupKey') or f'{section.section_type}-{question_index}'),
                question_number=question_payload.get('questionNumber'),
                sort_order=question_index,
                question_type=str(question_payload.get('questionType') or 'short_answer'),
                prompt_html=str(question_payload.get('promptHtml') or '').strip() or f'<p>Question {question_payload.get("questionNumber") or question_index}</p>',
                confidence=float(question_payload.get('confidence') or section.confidence or 0),
            )
            question.set_metadata(question_metadata)
            db.session.add(question)
            db.session.flush()

            seen_choice_keys: set[str] = set()
            for choice_index, choice_payload in enumerate(question_payload.get('choices') or [], start=1):
                choice_key = str(choice_payload.get('key') or f'choice-{choice_index}')
                if choice_key in seen_choice_keys:
                    continue
                seen_choice_keys.add(choice_key)
                choice = ExamChoice(
                    question_id=question.id,
                    choice_key=choice_key,
                    sort_order=choice_index,
                    label=choice_payload.get('label'),
                    content_html=str(choice_payload.get('contentHtml') or '').strip(),
                )
                choice.set_metadata(choice_payload.get('metadata') or {})
                db.session.add(choice)

            answers = [
                str(answer).strip()
                for answer in question_payload.get('answers') or []
                if str(answer).strip()
            ]
            for answer_index, answer in enumerate(answers, start=1):
                answer_key = ExamAnswerKey(
                    question_id=question.id,
                    sort_order=answer_index,
                    answer_kind='accepted_answer',
                    answer_text=answer,
                    normalized_text=_normalize_answer(answer),
                )
                db.session.add(answer_key)

            if question.question_type in {'single_choice', 'multiple_choice', 'matching', 'fill_blank', 'short_answer'} and not answers:
                _insert_review_item(
                    paper=paper,
                    section=section,
                    question=question,
                    item_type='missing_answer_key',
                    severity='warning',
                    message=f'Question {question.question_number or question.sort_order} is missing answer keys.',
                )
            if question.confidence < 0.65:
                _insert_review_item(
                    paper=paper,
                    section=section,
                    question=question,
                    item_type='low_confidence_question',
                    severity='warning',
                    message=f'Question {question.question_number or question.sort_order} needs review because parse confidence is low.',
                    metadata={'confidence': question.confidence},
                )

        if section.confidence < 0.7:
            _insert_review_item(
                paper=paper,
                section=section,
                question=None,
                item_type='low_confidence_section',
                severity='warning',
                message=f'{section.title} needs review because parse confidence is low.',
                metadata={'confidence': section.confidence},
            )
        if section.section_type == 'listening' and not matched_audio:
            _insert_review_item(
                paper=paper,
                section=section,
                question=None,
                item_type='missing_audio',
                severity='error',
                message=f'{section.title} has no matched listening audio in the GitHub audio library.',
            )

    paper.has_listening_audio = has_listening_audio
    if not paper.sections:
        _insert_review_item(
            paper=paper,
            section=None,
            question=None,
            item_type='parse_failed',
            severity='error',
            message='No exam sections were produced from the source PDF.',
        )
    if paper.import_confidence < 0.7:
        _insert_review_item(
            paper=paper,
            section=None,
            question=None,
            item_type='low_confidence_paper',
            severity='warning',
            message='This paper needs review because the aggregate parse confidence is low.',
            metadata={'confidence': paper.import_confidence},
        )
    db.session.flush()
    if paper.review_items:
        paper.publish_status = 'in_review'
    return paper


def run_exam_import_job(body: dict | None) -> dict:
    body = body or {}
    repo_url = str(body.get('repo_url') or body.get('repoUrl') or '').strip()
    audio_repo_url = str(body.get('audio_repo_url') or body.get('audioRepoUrl') or '').strip()
    if not repo_url:
        raise ValueError('repo_url is required')

    repo_location = parse_github_location(repo_url)
    audio_location = (
        parse_github_location(audio_repo_url)
        if audio_repo_url
        else GitHubLocation(
            owner=repo_location.owner,
            repo=repo_location.repo,
            ref=repo_location.ref,
            path='',
            url=f'https://github.com/{repo_location.owner}/{repo_location.repo}/tree/{repo_location.ref}',
        )
    )

    source = ExamSource.query.filter_by(source_url=repo_url).first()
    if source is None:
        source = ExamSource(
            source_type='github',
            source_url=repo_url,
            owner=repo_location.owner,
            repo=repo_location.repo,
            ref=repo_location.ref,
            root_path=repo_location.path,
            audio_root_path=audio_location.path or None,
            rights_status='restricted_internal',
        )
        db.session.add(source)
        db.session.flush()
    else:
        source.owner = repo_location.owner
        source.repo = repo_location.repo
        source.ref = repo_location.ref
        source.root_path = repo_location.path
        source.audio_root_path = audio_location.path or source.audio_root_path

    job = ExamIngestionJob(
        source_id=source.id,
        status='running',
        repo_url=repo_url,
        audio_repo_url=audio_repo_url or None,
        parser_model=exam_page_model(),
        stitch_model=exam_stitch_model(),
        started_at=datetime.utcnow(),
    )
    db.session.add(job)
    db.session.commit()

    imported_papers: list[ExamPaper] = []
    try:
        pdf_files = discover_pdf_files(repo_location)
        audio_files = discover_audio_files(audio_location)
        audio_inventory = _section_audio_inventory(audio_files)
        for pdf_item in pdf_files:
            parsed = parse_exam_pdf(
                pdf_url=pdf_item['download_url'],
                filename=pdf_item['name'],
            )
            for paper_payload in parsed.get('papers') or []:
                paper = _persist_paper_structure(
                    source=source,
                    paper_payload=paper_payload,
                    pdf_item=pdf_item,
                    audio_inventory=audio_inventory,
                )
                imported_papers.append(paper)
            db.session.commit()

        summary = {
            'pdfCount': len(pdf_files),
            'audioCount': len(audio_files),
            'paperCount': len(imported_papers),
            'reviewCount': sum(len(paper.review_items) for paper in imported_papers),
        }
        job.status = 'completed'
        job.finished_at = datetime.utcnow()
        job.set_summary(summary)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        job.status = 'failed'
        job.finished_at = datetime.utcnow()
        job.error_message = str(exc)
        db.session.add(job)
        db.session.commit()
        raise

    return {'job_id': job.id, 'summary': job.summary_dict()}
