from __future__ import annotations

from functools import lru_cache
from math import ceil

from services.study_sessions import normalize_chapter_id
from services.word_mastery_support import load_scope_vocabulary, normalize_optional_text, normalize_word_text

SOURCE_BOOK_IDS = ('ielts_reading_premium', 'ielts_listening_premium')
GAME_THEME_PAGE_SIZE = 8
THEME_CHAPTER_WORD_COUNT = 64

GAME_THEME_DEFINITIONS = (
    {
        'id': 'study-campus',
        'title': '教育校园',
        'subtitle': 'Campus study routes',
        'description': '学校、课程、研究、图书馆、课堂讨论和学术训练相关高频词。',
        'keywords': ('school', 'study', 'student', 'course', 'campus', 'education', 'academic', 'research', 'language', 'subject', 'lecture', 'library', 'teacher', '学习', '课程', '教育', '学术', '研究', '语言'),
    },
    {
        'id': 'work-business',
        'title': '工作商业',
        'subtitle': 'Workplace and business routes',
        'description': '工作、求职、市场、企业、消费、行业、管理和经济活动相关词。',
        'keywords': ('work', 'job', 'business', 'market', 'company', 'industry', 'product', 'career', 'money', 'economic', 'employee', 'customer', 'trade', '工作', '商业', '市场', '公司', '行业', '经济', '产品'),
    },
    {
        'id': 'travel-transport',
        'title': '旅行交通住宿',
        'subtitle': 'Travel, transport and accommodation',
        'description': '旅行安排、交通、住宿、路线、票务和游客服务相关词。',
        'keywords': ('travel', 'transport', 'traffic', 'hotel', 'ticket', 'tour', 'journey', 'route', 'airport', 'train', 'bus', 'vehicle', 'accommodation', '旅行', '交通', '旅馆', '路线', '游客', '票'),
    },
    {
        'id': 'city-services',
        'title': '城市设施服务',
        'subtitle': 'Local facilities and public services',
        'description': '城市、社区、公共设施、住房、服务、基础建设和日常事务相关词。',
        'keywords': ('city', 'community', 'service', 'local', 'facility', 'housing', 'building', 'public', 'street', 'shop', 'centre', 'infrastructure', '城市', '社区', '服务', '设施', '住房', '公共', '基础设施'),
    },
    {
        'id': 'health-lifestyle',
        'title': '健康饮食休闲',
        'subtitle': 'Health, food and daily life',
        'description': '健康、饮食、运动、休闲、家庭和日常生活相关词。',
        'keywords': ('health', 'medical', 'doctor', 'food', 'diet', 'sport', 'exercise', 'family', 'home', 'activity', 'leisure', 'lifestyle', '健康', '医疗', '饮食', '运动', '家庭', '生活', '休闲'),
    },
    {
        'id': 'environment-nature',
        'title': '环境自然',
        'subtitle': 'Environment and nature',
        'description': '自然环境、动物、资源、气候、能源、污染和保护相关词。',
        'keywords': ('environment', 'nature', 'animal', 'plant', 'climate', 'energy', 'resource', 'pollution', 'water', 'weather', 'earth', 'species', '环境', '自然', '动物', '植物', '气候', '能源', '资源', '污染'),
    },
    {
        'id': 'science-tech',
        'title': '科技科学',
        'subtitle': 'Science and technology',
        'description': '科技、科学、设备、数据、实验、创新和数字生活相关词。',
        'keywords': ('science', 'technology', 'computer', 'digital', 'data', 'device', 'internet', 'system', 'research', 'experiment', 'test', 'engineer', '科技', '科学', '技术', '电脑', '数据', '实验', '系统'),
    },
    {
        'id': 'society-culture',
        'title': '社会文化媒体',
        'subtitle': 'Society, culture and media',
        'description': '社会关系、文化、媒体、法律、政府、历史和公共议题相关词。',
        'keywords': ('society', 'culture', 'media', 'law', 'government', 'history', 'art', 'people', 'social', 'report', 'rights', 'communication', '社会', '文化', '媒体', '法律', '政府', '历史', '艺术', '报道'),
    },
)


def _theme_assets(theme_id: str) -> dict:
    base = f'/game/campaign-v2/themes/{theme_id}'
    return {
        'desktopMap': f'{base}/desktop/map.png',
        'mobileMap': f'{base}/mobile/map.png',
        'selectCard': f'{base}/desktop/select-card.png',
        'emptyState': f'{base}/desktop/empty-state.png',
        'bossGate': f'{base}/desktop/boss-gate.png',
        'rewardNode': f'{base}/desktop/reward-node.png',
    }


def _stable_theme_index(word: str, order: int) -> int:
    return (sum(ord(char) for char in word.lower()) + order) % len(GAME_THEME_DEFINITIONS)


def _score_theme(item: dict, theme: dict) -> int:
    haystack = ' '.join(str(item.get(key) or '') for key in ('word', 'definition', 'pos', 'chapter_title')).lower()
    score = 0
    for keyword in theme['keywords']:
        if keyword.lower() in haystack:
            score += max(1, len(keyword) // 3)
    return score


def _classify_word(item: dict, order: int) -> str:
    scores = [(_score_theme(item, theme), index, theme['id']) for index, theme in enumerate(GAME_THEME_DEFINITIONS)]
    best_score, _, best_theme_id = max(scores, key=lambda value: (value[0], -value[1]))
    if best_score > 0:
        return best_theme_id
    return GAME_THEME_DEFINITIONS[_stable_theme_index(item.get('word') or '', order)]['id']


def _load_source_words() -> list[dict]:
    words: list[dict] = []
    for book_id in SOURCE_BOOK_IDS:
        for order, item in enumerate(load_scope_vocabulary(book_id=book_id, chapter_id=None, day=None)):
            word = normalize_word_text(item.get('word'))
            if not word:
                continue
            words.append({
                **item,
                'word': word,
                'book_id': book_id,
                'chapter_id': normalize_chapter_id(item.get('chapter_id')),
                'chapter_title': normalize_optional_text(item.get('chapter_title')) or '',
                'source_order': len(words) + order,
            })
    return words


def _chapter_summary(theme: dict, chapter_index: int, chapter_words: list[dict]) -> dict:
    chapter_number = chapter_index + 1
    book_ids = sorted({str(item.get('book_id')) for item in chapter_words if item.get('book_id')})
    source_chapters = {
        f"{item.get('book_id')}:{item.get('chapter_id')}"
        for item in chapter_words
        if item.get('book_id') and item.get('chapter_id')
    }
    return {
        'id': f"{theme['id']}-{chapter_number}",
        'themeId': theme['id'],
        'title': f"{theme['title']} {chapter_number:02d}",
        'subtitle': f'{len(chapter_words)} words · {", ".join(book_ids)}',
        'wordCount': len(chapter_words),
        'page': ceil(chapter_number / GAME_THEME_PAGE_SIZE),
        'bookIds': book_ids,
        'sourceChapterCount': len(source_chapters),
        'assets': {
            'node': f"/game/campaign-v2/themes/{theme['id']}/desktop/chapter-node.png",
            'lockedNode': f"/game/campaign-v2/themes/{theme['id']}/desktop/chapter-node-locked.png",
            'currentNode': f"/game/campaign-v2/themes/{theme['id']}/desktop/chapter-node-current.png",
            'completedNode': f"/game/campaign-v2/themes/{theme['id']}/desktop/chapter-node-completed.png",
        },
    }


@lru_cache(maxsize=1)
def _compiled_theme_data() -> dict:
    source_words = _load_source_words()
    buckets = {theme['id']: [] for theme in GAME_THEME_DEFINITIONS}
    for order, item in enumerate(source_words):
        theme_id = _classify_word(item, order)
        buckets[theme_id].append({**item, 'theme_id': theme_id})

    themes = []
    chapter_map = {}
    for theme in GAME_THEME_DEFINITIONS:
        theme_words = buckets[theme['id']]
        chapters = []
        for index in range(0, len(theme_words), THEME_CHAPTER_WORD_COUNT):
            chunk = theme_words[index:index + THEME_CHAPTER_WORD_COUNT]
            summary = _chapter_summary(theme, index // THEME_CHAPTER_WORD_COUNT, chunk)
            chapters.append({**summary, 'words': chunk})
            chapter_map[summary['id']] = chapters[-1]
        themes.append({**theme, 'wordCount': len(theme_words), 'chapters': chapters})
    return {'themes': themes, 'chapterMap': chapter_map, 'totalWords': len(source_words)}


def _public_chapter(chapter: dict) -> dict:
    return {key: value for key, value in chapter.items() if key != 'words'}


def _safe_page(value) -> int:
    try:
        return max(1, int(value or 1))
    except (TypeError, ValueError):
        return 1


def _public_theme(theme: dict, *, page: int = 1) -> dict:
    page_count = max(1, ceil(len(theme['chapters']) / GAME_THEME_PAGE_SIZE))
    safe_page = min(_safe_page(page), page_count)
    start = (safe_page - 1) * GAME_THEME_PAGE_SIZE
    chapters = theme['chapters'][start:start + GAME_THEME_PAGE_SIZE]
    return {
        'id': theme['id'],
        'title': theme['title'],
        'subtitle': theme['subtitle'],
        'description': theme['description'],
        'wordCount': theme['wordCount'],
        'totalChapters': len(theme['chapters']),
        'currentPage': safe_page,
        'totalPages': page_count,
        'chapters': [_public_chapter(chapter) for chapter in chapters],
        'assets': _theme_assets(theme['id']),
    }


def build_game_theme_catalog(*, theme_id: str | None = None, page: int | None = None) -> dict:
    compiled = _compiled_theme_data()
    selected_theme_id = normalize_optional_text(theme_id)
    selected_page = _safe_page(page)
    return {
        'sourceBooks': list(SOURCE_BOOK_IDS),
        'pageSize': GAME_THEME_PAGE_SIZE,
        'totalWords': compiled['totalWords'],
        'taxonomy': 'official-aligned-v1',
        'themes': [
            _public_theme(theme, page=selected_page if theme['id'] == selected_theme_id else 1)
            for theme in compiled['themes']
        ],
    }


def build_theme_state_context(*, theme_id: str | None = None, theme_chapter_id: str | None = None) -> dict | None:
    normalized_theme_id = normalize_optional_text(theme_id)
    normalized_chapter_id = normalize_optional_text(theme_chapter_id)
    if not normalized_theme_id and not normalized_chapter_id:
        return None

    compiled = _compiled_theme_data()
    theme = next((item for item in compiled['themes'] if item['id'] == normalized_theme_id), compiled['themes'][0])
    chapter = next(
        (item for item in theme['chapters'] if item['id'] == normalized_chapter_id),
        theme['chapters'][0] if theme['chapters'] else None,
    )
    if chapter is None:
        return None
    public_theme = _public_theme(theme, page=chapter['page'])
    public_chapter = _public_chapter(chapter)
    return {
        'theme': public_theme,
        'themeChapter': public_chapter,
        'themeProgress': {
            'pageSize': GAME_THEME_PAGE_SIZE,
            'currentPage': public_theme['currentPage'],
            'totalPages': public_theme['totalPages'],
            'currentChapterIndex': max(0, theme['chapters'].index(chapter)),
            'totalChapters': len(theme['chapters']),
        },
        'words': [
            {**word, 'theme_id': theme['id'], 'theme_chapter_id': chapter['id']}
            for word in chapter['words']
        ],
        'scopeBookId': f"game-theme:{theme['id']}",
        'scopeChapterId': chapter['id'],
        'scopeLabel': f"{theme['title']} · {public_chapter['title']}",
    }


def apply_theme_state_payload(payload: dict, theme_context: dict | None) -> dict:
    if not theme_context:
        return payload
    next_payload = {**payload}
    next_payload['scope'] = {
        **(payload.get('scope') or {}),
        'themeId': theme_context['theme']['id'],
        'themeChapterId': theme_context['themeChapter']['id'],
    }
    next_payload['theme'] = theme_context['theme']
    next_payload['themeChapter'] = theme_context['themeChapter']
    next_payload['themeProgress'] = theme_context['themeProgress']
    next_payload['campaign'] = {
        **(payload.get('campaign') or {}),
        'scopeLabel': theme_context['scopeLabel'],
    }
    return next_payload
