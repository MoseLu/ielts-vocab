import json
import re
import uuid
import jwt
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from models import db, User, UserBookProgress, UserChapterProgress, \
    UserWrongWord, CustomBook, CustomBookChapter, CustomBookWord, \
    UserConversationHistory, UserStudySession
from functools import wraps
from services.llm import chat, TOOLS, TOOL_HANDLERS

ai_bp = Blueprint('ai', __name__)


# ── Auth decorator ────────────────────────────────────────────────────────────

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            from config import Config
            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(current_user, *args, **kwargs)
    return decorated


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_options(text: str) -> str:
    return re.sub(r'\[options\][\s\S]*?\[/options\]\s*', '', text).strip()


def _parse_options(text: str) -> list[str] | None:
    matches = re.findall(r'\[options\]\s*([\s\S]*?)\s*\[/options\]', text)
    if not matches:
        return None
    options = []
    for block in matches:
        for line in block.strip().split('\n'):
            line = line.strip()
            if line and re.match(r'^[A-Z]\.', line):
                options.append(line)
    return options if options else None


def _chat_with_tools(messages: list[dict], tools: list | None = None, max_iterations: int = 5) -> dict:
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
                messages.append({"role": "assistant", "content": [{"type": "tool_use", "id": tool_call_id, "name": tool_name, "input": tool_input}]})
                messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_call_id, "content": result}]})
            else:
                messages.append({"role": "assistant", "content": f"[Tool '{tool_name}' not available]"})
        else:
            return response
    return {"type": "text", "text": "[对话轮次过多，已停止]"}


def _save_exchange(user_id: int, user_msg: str, assistant_msg: str):
    """Persist one Q&A exchange to conversation history (keep last 40 turns per user)."""
    try:
        db.session.add(UserConversationHistory(user_id=user_id, role='user', content=user_msg))
        db.session.add(UserConversationHistory(user_id=user_id, role='assistant', content=assistant_msg))
        db.session.commit()
        # Prune to last 40 turns
        total = UserConversationHistory.query.filter_by(user_id=user_id).count()
        if total > 40:
            oldest = UserConversationHistory.query.filter_by(user_id=user_id) \
                .order_by(UserConversationHistory.created_at.asc()) \
                .limit(total - 40).all()
            for rec in oldest:
                db.session.delete(rec)
            db.session.commit()
    except Exception as e:
        import logging
        logging.warning(f"[AI] Failed to save conversation: {e}")
        db.session.rollback()


def _load_history(user_id: int, limit: int = 10) -> list[dict]:
    """Load recent conversation turns for LLM context injection."""
    rows = UserConversationHistory.query.filter_by(user_id=user_id) \
        .order_by(UserConversationHistory.created_at.asc()) \
        .all()
    # Take last `limit` turns
    rows = rows[-limit:]
    return [{'role': r.role, 'content': r.content} for r in rows]


# ── GET /api/ai/context ───────────────────────────────────────────────────────

@ai_bp.route('/context', methods=['GET'])
@token_required
def get_context(current_user: User):
    """Return structured learning summary for AI context."""
    user_id = current_user.id

    book_progress = UserBookProgress.query.filter_by(user_id=user_id).all()
    chapter_progress = UserChapterProgress.query.filter_by(user_id=user_id).all()
    wrong_words = UserWrongWord.query.filter_by(user_id=user_id) \
        .order_by(UserWrongWord.wrong_count.desc()).limit(50).all()

    books = {}
    total_learned = total_correct = total_wrong = 0

    for bp in book_progress:
        total = bp.correct_count + bp.wrong_count
        books[bp.book_id] = {
            'id': bp.book_id,
            'accuracy': round(bp.correct_count / total * 100) if total > 0 else 0,
            'wrongCount': bp.wrong_count,
            'correctCount': bp.correct_count,
        }
        total_learned += bp.current_index
        total_correct += bp.correct_count
        total_wrong += bp.wrong_count

    for cp in chapter_progress:
        if cp.book_id in books:
            books[cp.book_id]['wrongCount'] = books[cp.book_id].get('wrongCount', 0) + cp.wrong_count
            books[cp.book_id]['correctCount'] = books[cp.book_id].get('correctCount', 0) + cp.correct_count
        total_learned += cp.words_learned
        total_correct += cp.correct_count
        total_wrong += cp.wrong_count

    total_attempted = total_correct + total_wrong
    accuracy_rate = round(total_correct / total_attempted * 100) if total_attempted > 0 else 0

    from routes.books import VOCAB_BOOKS
    book_title_map = {b['id']: b['title'] for b in VOCAB_BOOKS}
    book_word_count_map = {b['id']: b.get('word_count', 0) for b in VOCAB_BOOKS}

    for book_id, stats in books.items():
        stats['title'] = book_title_map.get(book_id, book_id)
        stats['wordCount'] = book_word_count_map.get(book_id, 0)
        total = stats['correctCount'] + stats.get('wrongCount', 0)
        stats['progress'] = round(stats['correctCount'] / total * 100) if total > 0 else 0

    # Recent trend
    recent = UserChapterProgress.query.filter_by(user_id=user_id) \
        .order_by(UserChapterProgress.updated_at.desc()).limit(5).all()
    if len(recent) >= 2:
        fh = sum(r.correct_count / max(r.correct_count + r.wrong_count, 1) for r in recent[len(recent)//2:])
        sh = sum(r.correct_count / max(r.correct_count + r.wrong_count, 1) for r in recent[:len(recent)//2])
        trend = "improving" if sh > fh else "declining" if sh < fh else "stable"
    else:
        trend = "new"

    # Mode performance (from study sessions logged by client)
    mode_perf = {}
    sessions = UserStudySession.query.filter_by(user_id=user_id).all()
    for s in sessions:
        if s.mode:
            if s.mode not in mode_perf:
                mode_perf[s.mode] = {'correct': 0, 'wrong': 0, 'sessions': 0}
            mode_perf[s.mode]['correct'] += s.correct_count
            mode_perf[s.mode]['wrong'] += s.wrong_count
            mode_perf[s.mode]['sessions'] += 1
    mode_accuracy = {}
    for mode, d in mode_perf.items():
        total = d['correct'] + d['wrong']
        mode_accuracy[mode] = round(d['correct'] / total * 100) if total > 0 else 0

    # Sessions last 7 days
    cutoff = datetime.utcnow() - timedelta(days=7)
    sessions_last7 = UserStudySession.query.filter(
        UserStudySession.user_id == user_id,
        UserStudySession.started_at >= cutoff
    ).count()

    return jsonify({
        'totalBooks': len(books),
        'totalLearned': total_learned,
        'totalCorrect': total_correct,
        'totalWrong': total_wrong,
        'accuracyRate': accuracy_rate,
        'books': list(books.values()),
        'wrongWords': [
            {'word': w.word, 'phonetic': w.phonetic, 'pos': w.pos,
             'definition': w.definition, 'wrongCount': w.wrong_count}
            for w in wrong_words
        ],
        'recentTrend': trend,
        'modeAccuracy': mode_accuracy,
        'sessionsLast7Days': sessions_last7,
    })


# ── Context builder helpers ───────────────────────────────────────────────────

def _build_learning_data_msg(ctx_data: dict, client_ctx: dict) -> str:
    """Build the [学习数据] block injected into every LLM call."""
    mode_names = {
        'smart': '智能模式', 'listening': '听音选义', 'meaning': '看词选义',
        'dictation': '听写模式', 'radio': '随身听', 'quickmemory': '快速记忆'
    }
    trend_names = {
        'improving': '📈 上升', 'declining': '📉 下降', 'stable': '➡ 平稳', 'new': '🌱 刚开始'
    }

    lines = [
        f"总学习词数：{ctx_data.get('totalLearned', 0)}",
        f"总正确：{ctx_data.get('totalCorrect', 0)}  总错误：{ctx_data.get('totalWrong', 0)}",
        f"整体准确率：{ctx_data.get('accuracyRate', 0)}%",
        f"近期趋势：{trend_names.get(ctx_data.get('recentTrend', 'new'), ctx_data.get('recentTrend', ''))}",
        f"最近7天学习次数：{ctx_data.get('sessionsLast7Days', 0)}",
    ]

    # Per-mode accuracy
    mode_acc = ctx_data.get('modeAccuracy', {})
    # Also merge client-reported mode performance (may have more recent data)
    client_mode = client_ctx.get('modePerformance', {})
    if client_mode:
        for mode, stats in client_mode.items():
            total = stats.get('correct', 0) + stats.get('wrong', 0)
            if total > 0 and mode not in mode_acc:
                mode_acc[mode] = round(stats['correct'] / total * 100)
    if mode_acc:
        parts = ', '.join(f"{mode_names.get(m, m)} {v}%" for m, v in mode_acc.items())
        lines.append(f"各练习模式准确率：{parts}")

    # Wrong words
    wrong_words = ctx_data.get('wrongWords', [])
    if wrong_words:
        top = wrong_words[:20]
        lines.append(f"最难记单词（错误次数排序）：{', '.join(f\"{w['word']}({w['wrongCount']}次)\" for w in top)}")
    else:
        lines.append("错词列表：暂无")

    # Books
    for b in ctx_data.get('books', []):
        lines.append(f"  词书《{b.get('title', b.get('id'))}》准确率 {b.get('accuracy', 0)}%，错词 {b.get('wrongCount', 0)} 个")

    # Quick memory records (from client)
    qm = client_ctx.get('quickMemorySummary')
    if qm:
        lines.append(
            f"快速记忆记录：认识 {qm.get('known', 0)} 词，不认识 {qm.get('unknown', 0)} 词，"
            f"今日应复习 {qm.get('dueToday', 0)} 词（艾宾浩斯计划）"
        )

    return '\n'.join(lines)


def _build_current_state_msg(ctx: dict) -> str:
    """Build the [当前学习状态] block."""
    mode_names = {
        'smart': '智能模式', 'listening': '听音选义', 'meaning': '看词选义',
        'dictation': '听写模式', 'radio': '随身听', 'quickmemory': '快速记忆'
    }
    parts = []
    if ctx.get('currentWord'):
        parts.append(f"当前单词：{ctx['currentWord']}")
        if ctx.get('currentPhonetic'): parts.append(f"  音标：{ctx['currentPhonetic']}")
        if ctx.get('currentPos'):      parts.append(f"  词性：{ctx['currentPos']}")
        if ctx.get('currentDefinition'): parts.append(f"  释义：{ctx['currentDefinition']}")
    if ctx.get('currentBook'):    parts.append(f"当前词书：{ctx['currentBook']}")
    if ctx.get('currentChapter'): parts.append(f"当前章节：{ctx['currentChapter']}")
    if ctx.get('practiceMode'):
        parts.append(f"当前练习模式：{mode_names.get(ctx['practiceMode'], ctx['practiceMode'])}")
    if ctx.get('sessionProgress') is not None:
        parts.append(f"本次已完成：{ctx['sessionProgress']} 个词")
    if ctx.get('sessionAccuracy') is not None:
        parts.append(f"本次准确率：{ctx['sessionAccuracy']}%")
    return '\n'.join(parts) if parts else '用户当前未在练习页面'


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是 IELTS 英语词汇学习助手，名叫"雅思小助手"。请用中文回复用户。

## 你的核心能力
1. **记忆用户**：你能访问用户的完整学习历史（错词记录、模式准确率、练习规律、快速记忆数据、历史对话），请主动利用这些数据，让每次对话都比上次更懂用户。
2. **主动分析**：不要等用户询问。打开对话时，主动发现问题并给出具体建议。
3. **数据驱动建议**：建议必须具体——指出具体单词、具体模式、具体数量。不说"多复习"，说"今天重点练习这5个词"。
4. **制定计划**：基于准确率趋势、错词分布、艾宾浩斯复习计划，调整学习方案。
5. **例句与解析**：用户问某个词时，先用 web_search 工具搜索真实例句再回答。

## 主动推送原则（每次对话开始时检查）
- 准确率 < 60% → 建议降低练习难度或切换模式
- 有词今日应复习（艾宾浩斯计划）→ 直接告知具体词汇，建议开始快速记忆
- 某模式准确率比其他模式低15%以上 → 建议针对性练习
- 错误次数≥3的词 → 重点标出，建议用听写模式强化
- 7天内学习次数<3 → 鼓励保持学习习惯，给出具体计划

## 记忆连续性
- 你能看到历史对话记录，请主动引用："你上次提到..."、"上周你在...方面有改善..."
- 每次给出建议后，记录用户的选择，下次跟进执行情况

## 回复格式

### 普通回复
直接用中文，清晰有条理，不超过300字。

### 需要用户选择时（末尾附选项）
[options]
A. 选项A
B. 选项B
C. 选项C
[/options]

## 重要原则
- 不编造例句，通过 web_search 获取真实例句
- 建议具体可执行（具体词数、时间安排、具体模式）
- 语气友好积极，不过于严肃
- 如果用户数据为空（刚注册），先询问目标：考试时间、目标分数、每日可投入时间
"""

GREET_PROMPT = """根据以下用户学习数据和历史对话，生成一条个性化打招呼消息（不超过200字）。

要求：
1. 称呼用户"同学"或根据上下文选用
2. 基于真实数据给出1-2条具体的今日建议或发现（必须引用具体数字/词汇）
3. 如果有快速记忆复习词汇到期，重点提醒
4. 如果有历史对话，引用上次的内容表现出"记得"
5. 末尾给出今日建议选项（[options]...[/options]）
6. 绝对不要给泛泛的欢迎语，每条建议必须有数据支撑

格式：打招呼 + 数据洞察 + 今日建议选项"""


# ── POST /api/ai/greet ────────────────────────────────────────────────────────

@ai_bp.route('/greet', methods=['POST'])
@token_required
def greet(current_user: User):
    """Generate a data-driven personalized greeting on chat open."""
    body = request.get_json() or {}
    client_ctx = body.get('context', {})

    try:
        ctx_resp = get_context(current_user)
        ctx_data = ctx_resp.get_json()
    except Exception:
        ctx_data = {}

    learning_data = _build_learning_data_msg(ctx_data, client_ctx)

    # Recent conversation memory (last 4 turns)
    history = _load_history(current_user.id, limit=4)
    history_str = ''
    if history:
        history_str = '\n'.join(
            f"{'用户' if h['role'] == 'user' else '助手'}：{h['content'][:100]}"
            for h in history
        )
        history_str = f"\n\n历史对话摘要（最近几条）：\n{history_str}"

    messages = [
        {"role": "system", "content": GREET_PROMPT},
        {"role": "user", "content": f"【用户学习数据】\n{learning_data}{history_str}"}
    ]

    try:
        response = chat(messages, max_tokens=600)
        final_text = response.get("text", str(response)) if isinstance(response, dict) else str(response)
        options = _parse_options(final_text)
        clean_reply = _strip_options(final_text)
        # Save greeting as assistant turn
        _save_exchange(current_user.id, '[用户打开助手]', clean_reply)
        return jsonify({'reply': clean_reply, 'options': options})
    except Exception as e:
        return jsonify({
            'reply': '你好！我是雅思小助手，有什么可以帮你的？',
            'options': None
        })


# ── POST /api/ai/ask ──────────────────────────────────────────────────────────

@ai_bp.route('/ask', methods=['POST'])
@token_required
def ask(current_user: User):
    """
    Chat endpoint with conversation memory, richer context, and tool support.
    - Loads last 10 turns from DB for continuity across sessions
    - Saves each exchange to DB
    - Accepts quickMemorySummary and modePerformance from client
    """
    body = request.get_json() or {}
    user_message = body.get('message', '').strip()
    client_ctx = body.get('context', {})

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    # Build LLM message stack
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject user learning data
    try:
        ctx_resp = get_context(current_user)
        ctx_data = ctx_resp.get_json()
        learning_data = _build_learning_data_msg(ctx_data, client_ctx)
        messages.append({"role": "user", "content": f"[学习数据]\n{learning_data}"})
    except Exception as e:
        messages.append({"role": "user", "content": "[学习数据]\n数据加载失败，请根据用户当前状态回复。"})

    # Inject current session state
    if client_ctx:
        state_str = _build_current_state_msg(client_ctx)
        if state_str.strip() != '用户当前未在练习页面':
            messages.append({"role": "user", "content": f"[当前学习状态]\n{state_str}"})

    # Inject conversation history (cross-session memory)
    history = _load_history(current_user.id, limit=10)
    for turn in history:
        messages.append({"role": turn['role'], "content": turn['content']})

    # Proactive search for example sentences
    search_triggers = ['例句', 'example', '怎么用', '用法', '这个词', '这个单词', '举例']
    needs_search = any(kw in user_message for kw in search_triggers)
    if needs_search and client_ctx.get('currentWord'):
        word = client_ctx['currentWord']
        try:
            from services.llm import web_search
            results = web_search(f"{word} IELTS example sentences usage")
            messages.append({"role": "user", "content": f"[网页搜索结果 for '{word}']\n{results}"})
        except Exception:
            pass

    messages.append({"role": "user", "content": user_message})

    try:
        response = _chat_with_tools(messages, tools=TOOLS)
        final_text = response.get("text", str(response))
        options = _parse_options(final_text)
        clean_reply = _strip_options(final_text)

        # Persist exchange for memory continuity
        _save_exchange(current_user.id, user_message, clean_reply)

        return jsonify({'reply': clean_reply, 'options': options})
    except Exception as e:
        return jsonify({'error': f'AI service error: {str(e)}'}), 500


# ── POST /api/ai/log-session ──────────────────────────────────────────────────

@ai_bp.route('/log-session', methods=['POST'])
@token_required
def log_session(current_user: User):
    """Log a completed practice session for pattern analysis."""
    body = request.get_json() or {}
    session = UserStudySession(
        user_id=current_user.id,
        mode=body.get('mode'),
        book_id=body.get('bookId'),
        chapter_id=body.get('chapterId'),
        words_studied=body.get('wordsStudied', 0),
        correct_count=body.get('correctCount', 0),
        wrong_count=body.get('wrongCount', 0),
        duration_seconds=body.get('durationSeconds', 0),
        started_at=datetime.utcfromtimestamp(body.get('startedAt', 0) / 1000)
                   if body.get('startedAt') else datetime.utcnow(),
    )
    db.session.add(session)
    db.session.commit()
    return jsonify({'ok': True, 'id': session.id})


# ── POST /api/ai/generate-book ───────────────────────────────────────────────

GENERATE_BOOK_PROMPT = """你是一个 IELTS 词汇专家。用户希望生成一份自定义词汇书，请根据以下信息生成词表。

要求：
1. 返回 JSON 格式，包含 title、description、chapters（数组）、words（数组）
2. 每个 word 必须包含：word（单词）、phonetic（音标，如 /əˈbdev/）、pos（词性，如 n.、v.、adj.）、definition（中文释义）
3. 章节数建议 3-5 章，每章 15-30 个词
4. 词汇要真实存在，是 IELTS 考试常见词汇
5. 不要与用户已掌握的词重复
6. 如果用户指定了 focusAreas，优先选择对应领域的词汇
7. 如果用户指定了 userLevel，按对应难度选词

输出格式（只需要 JSON，不要其他文字）：
{{
  "title": "词书标题",
  "description": "词书描述（20字内）",
  "chapters": [{{ "id": "ch1", "title": "第一章标题", "wordCount": 25 }}],
  "words": [{{ "chapterId": "ch1", "word": "abdicate", "phonetic": "/ˈæbdɪkeɪt/", "pos": "v.", "definition": "退位；放弃（职位）" }}]
}}
"""


@ai_bp.route('/generate-book', methods=['POST'])
@token_required
def generate_book(current_user: User):
    body = request.get_json() or {}
    target_words = body.get('targetWords', 100)
    user_level = body.get('userLevel', 'intermediate')
    focus_areas = body.get('focusAreas', [])
    exclude_words = body.get('excludeWords', [])

    try:
        ctx_resp = get_context(current_user)
        ctx = ctx_resp.get_json()
        wrong_word_list = [w['word'] for w in ctx.get('wrongWords', [])[:30]]
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
        json_match = re.search(r'\{[\s\S]*\}', raw if isinstance(raw, str) else raw.get('text', ''))
        if not json_match:
            return jsonify({'error': 'Failed to parse generated book data'}), 500

        data = json.loads(json_match.group())
        book_id = f"custom_{uuid.uuid4().hex[:12]}"
        book = CustomBook(
            id=book_id, user_id=current_user.id,
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
            db.session.add(CustomBookWord(
                chapter_id=w.get('chapterId', list(chapter_map.keys())[0] if chapter_map else 'ch1'),
                word=w.get('word', ''), phonetic=w.get('phonetic', ''),
                pos=w.get('pos', ''), definition=w.get('definition', '')
            ))

        db.session.commit()
        return jsonify({
            'bookId': book_id, 'title': book.title, 'description': book.description,
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


# ── GET /api/ai/custom-books ─────────────────────────────────────────────────

@ai_bp.route('/custom-books', methods=['GET'])
@token_required
def list_custom_books(current_user: User):
    books = CustomBook.query.filter_by(user_id=current_user.id) \
        .order_by(CustomBook.created_at.desc()).all()
    return jsonify({'books': [b.to_dict() for b in books]})


@ai_bp.route('/custom-books/<book_id>', methods=['GET'])
@token_required
def get_custom_book(current_user: User, book_id: str):
    book = CustomBook.query.filter_by(id=book_id, user_id=current_user.id).first()
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    return jsonify(book.to_dict())


# ── POST /api/ai/wrong-words/sync ────────────────────────────────────────────

@ai_bp.route('/wrong-words/sync', methods=['POST'])
@token_required
def sync_wrong_words(current_user: User):
    body = request.get_json() or {}
    words = body.get('words', [])
    if not isinstance(words, list):
        return jsonify({'error': 'words must be an array'}), 400

    updated = 0
    for w in words:
        if not w.get('word'):
            continue
        existing = UserWrongWord.query.filter_by(user_id=current_user.id, word=w['word']).first()
        if existing:
            existing.phonetic = w.get('phonetic') or existing.phonetic
            existing.pos = w.get('pos') or existing.pos
            existing.definition = w.get('definition') or existing.definition
            existing.wrong_count = w.get('wrongCount', existing.wrong_count + 1)
        else:
            db.session.add(UserWrongWord(
                user_id=current_user.id, word=w['word'],
                phonetic=w.get('phonetic'), pos=w.get('pos'),
                definition=w.get('definition'), wrong_count=w.get('wrongCount', 1)
            ))
        updated += 1

    db.session.commit()
    return jsonify({'updated': updated})
