import re
from datetime import datetime


_MEMORY_TOPIC_STOPWORDS = {
    'please', 'about', 'with', 'what', 'when', 'where', 'which', 'could', 'would',
    'should', 'again', 'still', 'there', 'their', 'your', 'have',
}


def _extract_tokens(text: str | None) -> set[str]:
    english = {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z'-]{1,}", text or '')
        if token.lower() not in _MEMORY_TOPIC_STOPWORDS
    }
    chinese = {
        chunk
        for chunk in re.findall(r'[\u4e00-\u9fff]{2,}', text or '')
        if len(chunk.strip()) >= 2
    }
    return english | chinese


def _topic_key(note) -> str:
    word_key = (note.word_context or '').strip().lower()
    if word_key:
        return f'word:{word_key}'

    tokens = sorted(_extract_tokens(note.question))
    return '|'.join(tokens[:5]) or f'note:{note.id}'


def _follow_up_hint(*, word_context: str, count: int, title: str) -> str | None:
    if count < 2:
        return None

    if word_context:
        return f"这个问题已经重复出现，AI 应主动追问是否还需要继续辨析 {word_context} 的差异、例句或反例。"

    if title:
        return "这个主题已经反复出现，AI 应主动追问用户是概念没吃透，还是需要更多例句、反向辨析或小测。"

    return None


def build_memory_topics(
    notes,
    *,
    limit: int = 8,
    include_singletons: bool = True,
    related_note_limit: int = 4,
) -> list[dict]:
    topic_map: dict[str, dict] = {}

    for note in notes:
        topic_key = _topic_key(note)
        bucket = topic_map.setdefault(topic_key, {
            'title': note.question or '',
            'count': 0,
            'word_context': note.word_context or '',
            'latest_answer': note.answer or '',
            'latest_at': note.created_at,
            'note_ids': [],
            'related_notes': [],
        })
        bucket['count'] += 1
        bucket['note_ids'].append(note.id)
        bucket['related_notes'].append({
            'id': note.id,
            'question': note.question or '',
            'answer': note.answer or '',
            'word_context': note.word_context or '',
            'created_at': note.created_at,
        })
        if len(note.question or '') >= len(bucket['title'] or ''):
            bucket['title'] = note.question or ''
        if note.created_at and (bucket['latest_at'] is None or note.created_at >= bucket['latest_at']):
            bucket['latest_at'] = note.created_at
            bucket['latest_answer'] = note.answer or ''

    topics = []
    for key, bucket in topic_map.items():
        if not include_singletons and bucket['count'] < 2:
            continue

        related_notes = sorted(
            bucket['related_notes'],
            key=lambda item: item['created_at'] or datetime.min,
            reverse=True,
        )
        topics.append({
            'key': key,
            'title': str(bucket['title'])[:120],
            'count': bucket['count'],
            'word_context': bucket['word_context'],
            'latest_answer': str(bucket['latest_answer'])[:180],
            'latest_at': bucket['latest_at'].isoformat() if bucket['latest_at'] else None,
            'note_ids': bucket['note_ids'],
            'related_notes': [
                {
                    **item,
                    'created_at': item['created_at'].isoformat() if item['created_at'] else None,
                }
                for item in related_notes[:related_note_limit]
            ],
            'follow_up_hint': _follow_up_hint(
                word_context=bucket['word_context'],
                count=bucket['count'],
                title=bucket['title'],
            ),
            'is_repeated': bucket['count'] >= 2,
        })

    topics.sort(key=lambda item: (item['count'], item['latest_at'] or ''), reverse=True)
    return topics[:limit]
