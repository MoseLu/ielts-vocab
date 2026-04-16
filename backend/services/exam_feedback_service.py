from __future__ import annotations

import re

from services.exam_llm_support import ExamLLMError, exam_llm_available, exam_writing_model, request_text_json


TAG_RE = re.compile(r'<[^>]+>')


def _strip_html(value: str | None) -> str:
    return TAG_RE.sub(' ', str(value or '')).replace('\xa0', ' ').strip()


def build_writing_feedback(*, prompt_html: str | None, answer_text: str | None) -> dict | None:
    cleaned_answer = _strip_html(answer_text)
    if not cleaned_answer or not exam_llm_available():
        return None
    cleaned_prompt = _strip_html(prompt_html)
    prompt = (
        'You are reviewing an IELTS writing practice response. '
        'Return only JSON with keys summary, strengths, priorities, estimatedBand. '
        'summary must be a short paragraph. strengths and priorities must be arrays of short strings. '
        f'Prompt: {cleaned_prompt}\n'
        f'Candidate response: {cleaned_answer}'
    )
    try:
        payload = request_text_json(model=exam_writing_model(), prompt=prompt)
    except (ExamLLMError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    return {
        'summary': str(payload.get('summary') or '').strip(),
        'strengths': [str(item).strip() for item in payload.get('strengths') or [] if str(item).strip()],
        'priorities': [str(item).strip() for item in payload.get('priorities') or [] if str(item).strip()],
        'estimatedBand': payload.get('estimatedBand'),
    }
