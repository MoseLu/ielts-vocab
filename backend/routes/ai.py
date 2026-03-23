import json
import uuid
from flask import Blueprint, jsonify, request
from models import db, User, UserBookProgress, UserChapterProgress, CustomBook, CustomBookChapter, CustomBookWord, UserWrongWord, UserStudySession
from routes.middleware import token_required
from services.llm import chat, web_search, TOOLS, TOOL_HANDLERS

ai_bp = Blueprint('ai', __name__)


# ── GET /api/ai/context ───────────────────────────────────────────────────────

@ai_bp.route('/context', methods=['GET'])
@token_required
def get_context(current_user: User):
    """Return structured learning summary for AI context."""
    user_id = current_user.id

    # Book progress
    book_progress = UserBookProgress.query.filter_by(user_id=user_id).all()
    chapter_progress = UserChapterProgress.query.filter_by(user_id=user_id).all()
    wrong_words = UserWrongWord.query.filter_by(user_id=user_id).order_by(
        UserWrongWord.wrong_count.desc()
    ).limit(50).all()

    # Aggregate per-book stats
    books = []
    total_learned = 0
    total_correct = 0
    total_wrong = 0

    book_map = {}
    for bp in book_progress:
        total = bp.correct_count + bp.wrong_count
        accuracy = round(bp.correct_count / total * 100) if total > 0 else 0
        book_map[bp.book_id] = {
            'id': bp.book_id,
            'progress': round(bp.current_index / 100 * 100) if bp.current_index else 0,  # placeholder ratio
            'accuracy': accuracy,
            'wrongCount': bp.wrong_count,
            'correctCount': bp.correct_count,
        }
        total_learned += bp.current_index
        total_correct += bp.correct_count
        total_wrong += bp.wrong_count

    # Enrich with chapter accuracy
    for cp in chapter_progress:
        if cp.book_id in book_map:
            book_map[cp.book_id]['wrongCount'] = (
                book_map[cp.book_id].get('wrongCount', 0) + cp.wrong_count
            )
            book_map[cp.book_id]['correctCount'] = (
                book_map[cp.book_id].get('correctCount', 0) + cp.correct_count
            )
        total_learned += cp.words_learned
        total_correct += cp.correct_count
        total_wrong += cp.wrong_count

    total_attempted = total_correct + total_wrong
    accuracy_rate = round(total_correct / total_attempted * 100) if total_attempted > 0 else 0

    # Book titles (static lookup)
    from routes.books import VOCAB_BOOKS
    book_title_map = {b['id']: b['title'] for b in VOCAB_BOOKS}
    book_word_count_map = {b['id']: b.get('word_count', 0) for b in VOCAB_BOOKS}

    for book_id, stats in book_map.items():
        stats['title'] = book_title_map.get(book_id, book_id)
        stats['wordCount'] = book_word_count_map.get(book_id, 0)
        stats['progress'] = round(stats['correctCount'] / (stats['correctCount'] + stats.get('wrongCount', 0)) * 100) if (stats['correctCount'] + stats.get('wrongCount', 0)) > 0 else 0

    # Recent trend: check last 5 chapter sessions
    recent = UserChapterProgress.query.filter_by(user_id=user_id).order_by(
        UserChapterProgress.updated_at.desc()
    ).limit(5).all()
    if len(recent) >= 2:
        first_half = sum(r.correct_count / max(r.correct_count + r.wrong_count, 1) for r in recent[len(recent)//2:])
        second_half = sum(r.correct_count / max(r.correct_count + r.wrong_count, 1) for r in recent[:len(recent)//2])
        trend = "improving" if second_half > first_half else "declining" if second_half < first_half else "stable"
    else:
        trend = "new"

    return jsonify({
        'totalBooks': len(book_map),
        'totalLearned': total_learned,
        'totalCorrect': total_correct,
        'totalWrong': total_wrong,
        'accuracyRate': accuracy_rate,
        'books': list(book_map.values()),
        'wrongWords': [
            {
                'word': w.word,
                'phonetic': w.phonetic,
                'pos': w.pos,
                'definition': w.definition,
                'wrongCount': w.wrong_count
            }
            for w in wrong_words
        ],
        'recentTrend': trend
    })


# ── POST /api/ai/ask ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习规划助手，名叫"雅思小助手"。请用中文回复用户。

你具备以下能力：
1. 分析用户的学习数据（进度、准确率、错词分布、当前学习状态）
2. 给出学习计划建议（每日学习量、复习节奏），提供可操作的选项让用户选择
3. 激励用户保持学习习惯
4. 解释英文单词的用法，通过网络搜索获取权威例句

## 最重要的原则：优先使用用户的真实数据
- 如果用户提供了当前学习状态（[当前学习状态]），回复必须基于这些真实数据
- 如果用户问你记住了哪些单词，要明确说出具体单词名称，而不是泛泛而谈
- 如果用户在学习过程中问你当前单词的例句，先用 web_search 搜索真实例句
- 绝对不要在用户询问个人学习情况时给出通用词汇表

## 当用户没有历史数据时（totalLearned=0 或 [当前学习状态] 为空）
- 说明用户刚开始，先询问他们的目标：每天多少时间、目标分数等
- 不要给通用词汇表，而是制定第一阶段学习计划，提供选项让用户选择

## 回复格式规范

### 普通回复
直接用中文回复，内容清晰有条理。

### 建议型回复（需要用户确认）
在回复末尾用以下格式提供选项：
[options]
A. 选项A描述
B. 选项B描述
[/options]

示例（用户问今日计划）：
"根据你的数据，你今日可以学习50个新词，重点复习听力场景词汇。你想："
[options]
A. 好的，开始学习
B. 调整一下数量
C. 换个复习方向
[/options]

### 选项处理规则
- 用户可能只回复 "A" 或 "B" 等，识别并继续执行
- 回复选项时选项要有实际意义，每个选项要有明确的差异化

## 重要原则
- 不要编造例句，尽量通过网络搜索获取真实、地道的例句
- 建议要具体可执行（具体词数、时间安排）
- 语言要友好鼓励，不要过于严肃
- 如果用户还没有学习数据，鼓励他们开始学习
"""


def _build_context_msg(ctx: dict) -> str:
    """Build a readable context string from learning context dict."""
    parts = []

    # Book / chapter info
    if ctx.get('currentChapterTitle'):
        parts.append(f"当前章节：{ctx['currentChapterTitle']}")
    elif ctx.get('currentChapter'):
        parts.append(f"当前章节 ID：{ctx['currentChapter']}")
    if ctx.get('currentBook'):
        parts.append(f"当前词书 ID：{ctx['currentBook']}")

    if ctx.get('practiceMode'):
        parts.append(f"练习模式：{ctx['practiceMode']}")
    if ctx.get('mode'):
        parts.append(f"学习类型：{ctx['mode']}")

    # Session progress
    session_progress = ctx.get('sessionProgress')
    total_words = ctx.get('totalWords')
    words_completed = ctx.get('wordsCompleted')
    session_completed = ctx.get('sessionCompleted')

    if session_completed:
        parts.append(f"本轮练习：已完成全部 {total_words} 个单词")
        if words_completed is not None:
            parts.append(f"本轮答题数：{words_completed} 个")
    elif session_progress is not None:
        if total_words:
            parts.append(f"本次进度：{session_progress} / {total_words} 个词")
        else:
            parts.append(f"本次进度：{session_progress} 个词")
        if words_completed is not None:
            parts.append(f"本次已答题：{words_completed} 个")

    if ctx.get('sessionAccuracy') is not None:
        parts.append(f"本次准确率：{ctx['sessionAccuracy']}%")

    # Current word being studied (only when mid-session)
    if ctx.get('currentWord') and not session_completed:
        parts.append(f"当前单词：{ctx['currentWord']}")
        if ctx.get('currentPhonetic'):
            parts.append(f"  音标：{ctx['currentPhonetic']}")
        if ctx.get('currentPos'):
            parts.append(f"  词性：{ctx['currentPos']}")
        if ctx.get('currentDefinition'):
            parts.append(f"  释义：{ctx['currentDefinition']}")

    # Local historical summary (from localStorage)
    local = ctx.get('localHistory')
    if local and isinstance(local, dict):
        completed = local.get('chaptersCompleted', 0)
        attempted = local.get('chaptersAttempted', 0)
        accuracy = local.get('overallAccuracy', 0)
        correct = local.get('totalCorrect', 0)
        wrong = local.get('totalWrong', 0)
        if attempted > 0:
            parts.append(
                f"历史记录（本地）：已尝试 {attempted} 个章节，完成 {completed} 个，"
                f"累计答题 {correct + wrong} 次，准确率 {accuracy}%"
            )

    return '\n'.join(parts) if parts else '暂无'


def _strip_options(text: str) -> str:
    """Remove [options]...[/options] blocks from text."""
    import re
    return re.sub(r'\[options\][\s\S]*?\[/options\]\s*', '', text).strip()


def _parse_options(text: str) -> list[str] | None:
    """Extract [options] blocks from text. Returns list of options or None."""
    import re
    pattern = r'\[options\]\s*([\s\S]*?)\s*\[/options\]'
    matches = re.findall(pattern, text)
    if not matches:
        return None
    # Extract individual lines
    options = []
    for block in matches:
        for line in block.strip().split('\n'):
            line = line.strip()
            if line and re.match(r'^[A-Z]\.', line):
                options.append(line)
    return options if options else None


def _chat_with_tools(messages: list[dict], tools: list | None = None, max_iterations: int = 5) -> dict:
    """
    Chat with MiniMax, automatically handling tool_use blocks.
    Appends assistant responses and tool results to messages in-place.
    Returns the final text response.
    """
    for i in range(max_iterations):
        response = chat(messages, tools=tools, max_tokens=4096)

        if response.get("type") == "tool_call":
            tool_name = response.get("tool")
            tool_input = response.get("input", {})
            tool_call_id = response.get("tool_call_id", f"call_{i}")
            handler = TOOL_HANDLERS.get(tool_name)

            if handler:
                try:
                    result = handler(**tool_input)
                except Exception as e:
                    result = f"Tool error: {e}"

                # Append assistant message with tool_use reference
                messages.append({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": tool_call_id,
                        "name": tool_name,
                        "input": tool_input
                    }]
                })
                # Append tool result
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": result
                    }]
                })
            else:
                messages.append({
                    "role": "assistant",
                    "content": f"[Tool '{tool_name}' not available]"
                })
        else:
            return response

    # Max iterations reached
    return {"type": "text", "text": "[对话轮次过多，已停止]"}


@ai_bp.route('/ask', methods=['POST'])
@token_required
def ask(current_user: User):
    """
    Chat endpoint — accepts user message + optional learning context.
    Handles tool calls (web search) and returns structured response with options.
    """
    body = request.get_json() or {}
    user_message = body.get('message', '').strip()
    frontend_context = body.get('context', {})  # {currentWord, practiceMode, sessionProgress, ...}

    import logging
    logging.warning(f"[AI] ask from user={current_user.id}: msg='{user_message[:50]}' ctx={frontend_context}")

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    # Build messages for LLM
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject persistent user data (learning summary)
    try:
        ctx_resp = get_context(current_user)
        ctx_data = ctx_resp.get_json()
        context_msg = (
            f"【用户学习数据摘要】\n"
            f"总学习词数：{ctx_data.get('totalLearned', 0)}\n"
            f"总正确数：{ctx_data.get('totalCorrect', 0)}  总错误数：{ctx_data.get('totalWrong', 0)}\n"
            f"整体准确率：{ctx_data.get('accuracyRate', 0)}%\n"
            f"学习趋势：{ctx_data.get('recentTrend', 'new')}\n"
            f"正在学习的词书：{len(ctx_data.get('books', []))} 本\n"
        )
        for b in ctx_data.get('books', []):
            context_msg += (
                f"  - {b.get('title', b.get('id'))} "
                f"(准确率 {b.get('accuracy', 0)}%，错词数 {b.get('wrongCount', 0)})\n"
            )
        wrong_words = ctx_data.get('wrongWords', [])
        if wrong_words:
            words_list = '、'.join([w['word'] for w in wrong_words[:20]])
            context_msg += f"错词列表（最近50条）：{words_list}\n"
        else:
            context_msg += "错词列表：暂无\n"

        messages.append({"role": "user", "content": f"[学习数据]\n{context_msg}"})
    except Exception as e:
        import logging
        logging.warning(f"[AI] Failed to fetch user context: {e}")
        messages.append({"role": "user", "content": "[学习数据]\n数据加载失败，请根据用户当前状态回复。"})

    # Inject frontend learning context (current word, mode, etc.)
    if frontend_context:
        ctx_str = _build_context_msg(frontend_context)
        messages.append({"role": "user", "content": f"[当前学习状态]\n{ctx_str}"})

    # Proactive search: if user asks about examples/definitions, search first
    search_trigger_keywords = ['例句', '例 子', 'example', '怎么 用', '用法', '这个词', '这个词的', '这个单词']
    needs_search = any(kw in user_message for kw in search_trigger_keywords)

    if needs_search and frontend_context.get('currentWord'):
        word = frontend_context['currentWord']
        search_query = f"{word} example sentences IELTS context"
        try:
            from services.llm import web_search
            search_results = web_search(search_query)
            messages.append({"role": "user", "content": (
                f"[网页搜索结果 for '{word}']\n{search_results}\n\n"
                "请根据搜索结果，为用户解释这个单词的用法并给出例句。"
            )})
        except Exception:
            messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": user_message})

    # Run chat with tool calling support
    try:
        response = _chat_with_tools(messages, tools=TOOLS)

        final_text = response.get("text", str(response))
        options = _parse_options(final_text)
        # Strip [options] blocks from the visible reply text
        clean_reply = _strip_options(final_text)

        return jsonify({
            'reply': clean_reply,
            'options': options,
        })

    except Exception as e:
        return jsonify({'error': f'AI service error: {str(e)}'}), 500


# ── POST /api/ai/generate-book ───────────────────────────────────────────────

GENERATE_BOOK_PROMPT = """你是一个 IELTS 词汇专家。用户希望生成一份自定义词汇书，请根据以下信息生成词表。

要求：
1. 返回 JSON 格式，包含 title、description、chapters（数组）、words（数组）
2. 每个 word 必须包含：word（单词）、phonetic（音标，如 /əˈbdev/）、pos（词性，如 n.、v.、adj.）、definition（中文释义）
3. 章节数建议 3-5 章，每章 15-30 个词
4. 词汇要真实存在，是 IELTS 考试常见词汇
5. 不要与用户已掌握的词重复
6. 如果用户指定了 focusAreas（focusAreas），优先选择对应领域的词汇
7. 如果用户指定了 userLevel，按对应难度选词：
   - beginner：大学英语四级水平词汇为主
   - intermediate：六级到雅思核心词汇
   - advanced：雅思高分段学术词汇

输出格式（只需要 JSON，不要其他文字）：
{{
  "title": "词书标题",
  "description": "词书描述（20字内）",
  "chapters": [
    {{ "id": "ch1", "title": "第一章标题", "wordCount": 25 }}
  ],
  "words": [
    {{ "chapterId": "ch1", "word": "abdicate", "phonetic": "/ˈæbdɪkeɪt/", "pos": "v.", "definition": "退位；放弃（职位）" }}
  ]
}}
"""


@ai_bp.route('/generate-book', methods=['POST'])
@token_required
def generate_book(current_user: User):
    """Generate a custom vocabulary book based on user's learning profile."""
    body = request.get_json() or {}
    target_words = body.get('targetWords', 100)
    user_level = body.get('userLevel', 'intermediate')
    focus_areas = body.get('focusAreas', [])
    exclude_words = body.get('excludeWords', [])

    # Build context
    try:
        ctx_resp = get_context(current_user)
        ctx = ctx_resp.get_json()
        wrong_words = ctx.get('wrongWords', [])
        wrong_word_list = [w['word'] for w in wrong_words[:30]]
        all_exclude = list(set(exclude_words + wrong_word_list))
    except Exception:
        all_exclude = exclude_words

    user_message = (
        f"请生成一份约 {target_words} 词的自定义词书。\n"
        f"用户水平：{user_level}\n"
        f"重点领域：{', '.join(focus_areas) if focus_areas else '综合'}"
    )
    if all_exclude:
        user_message += f"\n以下词汇已掌握，请排除：{', '.join(all_exclude[:50])}"

    messages = [
        {"role": "system", "content": GENERATE_BOOK_PROMPT},
        {"role": "user", "content": user_message}
    ]

    try:
        raw = chat(messages, max_tokens=8192)

        # Parse JSON from response (may be wrapped in markdown code blocks)
        import re
        json_str = re.search(r'\{[\s\S]*\}', raw)
        if not json_str:
            return jsonify({'error': 'Failed to parse generated book data'}), 500

        data = json.loads(json_str.group())

        # Persist to DB
        book_id = f"custom_{uuid.uuid4().hex[:12]}"
        book = CustomBook(
            id=book_id,
            user_id=current_user.id,
            title=data.get('title', '自定义词书'),
            description=data.get('description', ''),
            word_count=len(data.get('words', []))
        )
        db.session.add(book)

        chapter_map = {}
        for ch in data.get('chapters', []):
            chapter = CustomBookChapter(
                id=ch.get('id', f"ch_{uuid.uuid4().hex[:6]}"),
                book_id=book_id,
                title=ch.get('title', '未命名章节'),
                word_count=ch.get('wordCount', 0),
                sort_order=data.get('chapters', []).index(ch)
            )
            db.session.add(chapter)
            chapter_map[chapter.id] = chapter

        for w in data.get('words', []):
            word = CustomBookWord(
                chapter_id=w.get('chapterId', list(chapter_map.keys())[0] if chapter_map else 'ch1'),
                word=w.get('word', ''),
                phonetic=w.get('phonetic', ''),
                pos=w.get('pos', ''),
                definition=w.get('definition', '')
            )
            db.session.add(word)

        db.session.commit()

        return jsonify({
            'bookId': book_id,
            'title': book.title,
            'description': book.description,
            'chapters': [c.to_dict() for c in book.chapters],
            'words': [w.to_dict() for w in CustomBookWord.query.filter(
                CustomBookWord.chapter_id.in_([c.id for c in book.chapters])
            ).all()]
        })

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Failed to parse generated book: {str(e)}'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Book generation failed: {str(e)}'}), 500


# ── GET /api/ai/custom-books ────────────────────────────────────────────────

@ai_bp.route('/custom-books', methods=['GET'])
@token_required
def list_custom_books(current_user: User):
    """List all AI-generated custom books for the current user."""
    books = CustomBook.query.filter_by(user_id=current_user.id).order_by(
        CustomBook.created_at.desc()
    ).all()
    return jsonify({'books': [b.to_dict() for b in books]})


# ── GET /api/ai/custom-books/<book_id> ───────────────────────────────────────

@ai_bp.route('/custom-books/<book_id>', methods=['GET'])
@token_required
def get_custom_book(current_user: User, book_id: str):
    """Get a single custom book with its chapters and words."""
    book = CustomBook.query.filter_by(id=book_id, user_id=current_user.id).first()
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    return jsonify(book.to_dict())


# ── GET /api/wrong-words ─────────────────────────────────────────────────────

@ai_bp.route('/wrong-words', methods=['GET'])
@token_required
def get_wrong_words(current_user: User):
    """Get all wrong words for the current user from the backend."""
    words = UserWrongWord.query.filter_by(user_id=current_user.id)\
        .order_by(UserWrongWord.wrong_count.desc()).all()
    return jsonify({'words': [w.to_dict() for w in words]}), 200


# ── POST /api/wrong-words/sync ──────────────────────────────────────────────

@ai_bp.route('/wrong-words/sync', methods=['POST'])
@token_required
def sync_wrong_words(current_user: User):
    """Sync wrong words from client localStorage to backend DB."""
    body = request.get_json() or {}
    words = body.get('words', [])

    if not isinstance(words, list):
        return jsonify({'error': 'words must be an array'}), 400

    updated = 0
    for w in words:
        if not w.get('word'):
            continue
        existing = UserWrongWord.query.filter_by(
            user_id=current_user.id,
            word=w['word']
        ).first()
        if existing:
            existing.phonetic = w.get('phonetic') or existing.phonetic
            existing.pos = w.get('pos') or existing.pos
            existing.definition = w.get('definition') or existing.definition
            existing.wrong_count = w.get('wrongCount', existing.wrong_count + 1)
        else:
            new_w = UserWrongWord(
                user_id=current_user.id,
                word=w['word'],
                phonetic=w.get('phonetic'),
                pos=w.get('pos'),
                definition=w.get('definition'),
                wrong_count=w.get('wrongCount', 1)
            )
            db.session.add(new_w)
        updated += 1

    db.session.commit()
    return jsonify({'updated': updated})


@ai_bp.route('/wrong-words/<word>', methods=['DELETE'])
@token_required
def delete_wrong_word(current_user: User, word: str):
    """Delete a wrong word by word string."""
    record = UserWrongWord.query.filter_by(user_id=current_user.id, word=word).first()
    if record:
        db.session.delete(record)
        db.session.commit()
    return jsonify({'message': '已移除'}), 200


@ai_bp.route('/wrong-words', methods=['DELETE'])
@token_required
def clear_wrong_words(current_user: User):
    """Clear all wrong words for the current user."""
    UserWrongWord.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'message': '已清空'}), 200


# ── POST /api/ai/log-session ─────────────────────────────────────────────────

@ai_bp.route('/learning-stats', methods=['GET'])
@token_required
def get_learning_stats(current_user: User):
    """Return daily aggregated learning stats from study sessions, with optional filters."""
    from datetime import datetime, timedelta
    from collections import defaultdict

    days = min(int(request.args.get('days', 30)), 90)
    book_id_filter = request.args.get('book_id') or None
    mode_filter = request.args.get('mode') or None

    since = datetime.utcnow() - timedelta(days=days)

    query = UserStudySession.query.filter(
        UserStudySession.user_id == current_user.id,
        UserStudySession.started_at >= since
    )
    if book_id_filter:
        query = query.filter(UserStudySession.book_id == book_id_filter)
    if mode_filter:
        query = query.filter(UserStudySession.mode == mode_filter)

    sessions = query.all()

    # Aggregate by calendar date
    daily = defaultdict(lambda: {
        'words_studied': 0, 'correct_count': 0,
        'wrong_count': 0, 'duration_seconds': 0, 'sessions': 0
    })
    for s in sessions:
        date_key = s.started_at.strftime('%Y-%m-%d')
        daily[date_key]['words_studied'] += s.words_studied or 0
        daily[date_key]['correct_count'] += s.correct_count or 0
        daily[date_key]['wrong_count'] += s.wrong_count or 0
        daily[date_key]['duration_seconds'] += s.duration_seconds or 0
        daily[date_key]['sessions'] += 1

    # Build full date range (oldest → newest)
    result = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime('%Y-%m-%d')
        day_data = dict(daily.get(d, {
            'words_studied': 0, 'correct_count': 0,
            'wrong_count': 0, 'duration_seconds': 0, 'sessions': 0
        }))
        total = day_data['correct_count'] + day_data['wrong_count']
        day_data['accuracy'] = round(day_data['correct_count'] / total * 100) if total > 0 else None
        result.append({'date': d, **day_data})

    # ── Chapter-progress fallback (when UserStudySession is sparse/empty) ──────
    # Group UserChapterProgress by updated_at date; use words_learned as proxy
    # for words studied that day. Not perfect for multi-day chapters, but much
    # better than showing zeros when the user has real learning history.
    chapter_q = UserChapterProgress.query.filter(
        UserChapterProgress.user_id == current_user.id,
        UserChapterProgress.updated_at >= since,
    )
    if book_id_filter:
        chapter_q = chapter_q.filter(UserChapterProgress.book_id == book_id_filter)
    chapter_rows = chapter_q.all()

    ch_daily: dict = defaultdict(lambda: {'words_studied': 0, 'correct_count': 0, 'wrong_count': 0})
    for cp in chapter_rows:
        dk = cp.updated_at.strftime('%Y-%m-%d')
        ch_daily[dk]['words_studied'] += cp.words_learned or 0
        ch_daily[dk]['correct_count'] += cp.correct_count or 0
        ch_daily[dk]['wrong_count'] += cp.wrong_count or 0

    fallback_result = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime('%Y-%m-%d')
        fd = dict(ch_daily.get(d, {'words_studied': 0, 'correct_count': 0, 'wrong_count': 0}))
        t = fd['correct_count'] + fd['wrong_count']
        fd['accuracy'] = round(fd['correct_count'] / t * 100) if t > 0 else None
        fd['duration_seconds'] = 0
        fd['sessions'] = 0
        fallback_result.append({'date': d, **fd})

    # Decide which daily series to return (sessions preferred)
    has_session_data = any(d['sessions'] > 0 for d in result)
    active_daily = result if has_session_data else fallback_result
    use_fallback = not has_session_data

    # Books and modes the user has ever studied (for filter dropdowns)
    all_sessions = UserStudySession.query.filter_by(user_id=current_user.id).all()
    book_ids_from_sessions = {s.book_id for s in all_sessions if s.book_id}
    # Also include books from chapter progress (covers users with no sessions yet)
    all_chapters = UserChapterProgress.query.filter_by(user_id=current_user.id).all()
    book_ids_from_chapters = {cp.book_id for cp in all_chapters if cp.book_id}
    book_ids = list(book_ids_from_sessions | book_ids_from_chapters)
    modes_used = sorted({s.mode for s in all_sessions if s.mode})

    try:
        from routes.books import VOCAB_BOOKS
        book_title_map = {b['id']: b['title'] for b in VOCAB_BOOKS}
    except Exception:
        book_title_map = {}

    books = [{'id': bid, 'title': book_title_map.get(bid, bid)} for bid in book_ids]

    # Overall summary for the period (use fallback totals when no sessions)
    total_words = sum(d['words_studied'] for d in active_daily)
    total_duration = sum(d['duration_seconds'] for d in active_daily)
    total_correct = sum(d['correct_count'] for d in active_daily)
    total_wrong = sum(d['wrong_count'] for d in active_daily)
    total_sessions = sum(d['sessions'] for d in active_daily)
    total_attempted = total_correct + total_wrong
    period_accuracy = round(total_correct / total_attempted * 100) if total_attempted > 0 else None

    # All-time totals from chapter progress (words_learned is the correct "words studied" count)
    all_chapter_progress = UserChapterProgress.query.filter_by(user_id=current_user.id).all()
    alltime_words = sum(cp.words_learned or 0 for cp in all_chapter_progress)
    alltime_correct = sum(cp.correct_count or 0 for cp in all_chapter_progress)
    alltime_wrong = sum(cp.wrong_count or 0 for cp in all_chapter_progress)
    alltime_attempted = alltime_correct + alltime_wrong
    alltime_accuracy = round(alltime_correct / alltime_attempted * 100) if alltime_attempted > 0 else None

    # Today's accuracy from chapter progress updated today
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    today_chapters = [cp for cp in all_chapter_progress
                      if cp.updated_at and cp.updated_at.strftime('%Y-%m-%d') == today_str]
    today_correct = sum(cp.correct_count or 0 for cp in today_chapters)
    today_wrong = sum(cp.wrong_count or 0 for cp in today_chapters)
    today_attempted = today_correct + today_wrong
    today_accuracy = round(today_correct / today_attempted * 100) if today_attempted > 0 else None

    # Session-based duration (only meaningful when sessions exist)
    all_user_sessions = UserStudySession.query.filter_by(user_id=current_user.id).all()
    alltime_duration = sum(s.duration_seconds or 0 for s in all_user_sessions)
    today_sessions = [s for s in all_user_sessions
                      if s.started_at and s.started_at.strftime('%Y-%m-%d') == today_str]
    today_duration = sum(s.duration_seconds or 0 for s in today_sessions)

    # ── Per-mode breakdown (all-time, from UserStudySession) ──────────────────
    mode_stats: dict = {}
    for s in all_user_sessions:
        m = s.mode or 'unknown'
        if m not in mode_stats:
            mode_stats[m] = {
                'mode': m,
                'words_studied': 0, 'correct_count': 0,
                'wrong_count': 0, 'duration_seconds': 0, 'sessions': 0,
            }
        mode_stats[m]['words_studied'] += s.words_studied or 0
        mode_stats[m]['correct_count'] += s.correct_count or 0
        mode_stats[m]['wrong_count'] += s.wrong_count or 0
        mode_stats[m]['duration_seconds'] += s.duration_seconds or 0
        mode_stats[m]['sessions'] += 1

    for md in mode_stats.values():
        attempted = md['correct_count'] + md['wrong_count']
        md['accuracy'] = round(md['correct_count'] / attempted * 100) if attempted > 0 else None

    mode_breakdown = sorted(mode_stats.values(), key=lambda x: x['words_studied'], reverse=True)

    return jsonify({
        'daily': active_daily,
        'books': books,
        'modes': modes_used,
        'use_fallback': use_fallback,
        'summary': {
            'total_words': total_words,
            'total_duration_seconds': total_duration,
            'total_sessions': total_sessions,
            'accuracy': period_accuracy,
        },
        'alltime': {
            'total_words': alltime_words,
            'accuracy': alltime_accuracy,
            'duration_seconds': alltime_duration,
            'today_accuracy': today_accuracy,
            'today_duration_seconds': today_duration,
        },
        'mode_breakdown': mode_breakdown,
    })


@ai_bp.route('/log-session', methods=['POST'])
@token_required
def log_session(current_user: User):
    """Persist a study session record to the database."""
    body = request.get_json() or {}
    try:
        # Use client-provided startedAt (epoch ms) if valid, else server time
        started_at = None
        client_start = body.get('startedAt')
        if client_start:
            try:
                from datetime import timezone
                started_at = datetime.fromtimestamp(int(client_start) / 1000, tz=timezone.utc).replace(tzinfo=None)
            except Exception:
                pass

        session = UserStudySession(
            user_id=current_user.id,
            mode=body.get('mode'),
            book_id=body.get('bookId'),
            chapter_id=body.get('chapterId'),
            words_studied=body.get('wordsStudied', 0),
            correct_count=body.get('correctCount', 0),
            wrong_count=body.get('wrongCount', 0),
            duration_seconds=body.get('durationSeconds', 0),
        )
        if started_at:
            session.started_at = started_at
        db.session.add(session)
        db.session.commit()
        return jsonify({'id': session.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
