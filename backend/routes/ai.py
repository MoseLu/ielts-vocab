import re
import json
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request
from models import db, User, UserBookProgress, UserChapterProgress, CustomBook, CustomBookChapter, CustomBookWord, UserWrongWord, UserStudySession, UserQuickMemoryRecord, UserSmartWordStat, UserConversationHistory, UserMemory, UserLearningNote
from routes.middleware import token_required
from services.llm import chat, web_search, TOOLS, TOOL_HANDLERS

ai_bp = Blueprint('ai', __name__)


# ── Global vocabulary pool (all books, deduplicated) ─────────────────────────

_global_vocab_pool: list | None = None


def _get_global_vocab_pool() -> list:
    """
    Load every word from every book into one flat list.
    Deduplicates by lowercase word string.  Cached after first call.
    """
    global _global_vocab_pool
    if _global_vocab_pool is not None:
        return _global_vocab_pool

    from routes.books import VOCAB_BOOKS, load_book_vocabulary
    seen: dict[str, dict] = {}
    for book in VOCAB_BOOKS:
        words = load_book_vocabulary(book['id']) or []
        for w in words:
            key = w.get('word', '').strip().lower()
            if key and key not in seen:
                seen[key] = {
                    'word':       w.get('word', '').strip(),
                    'phonetic':   w.get('phonetic', ''),
                    'pos':        w.get('pos', ''),
                    'definition': w.get('definition', ''),
                }
    _global_vocab_pool = list(seen.values())
    return _global_vocab_pool


# ── Similarity helpers ────────────────────────────────────────────────────────

def _levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            tmp = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = tmp
    return dp[n]


_IPA_STRIP = re.compile(r'[/\[\]ˈˌ.: ]')


def _confusability_score(
    tw: str, tp: str, tpos: str,
    cw: str, cp: str, cpos: str,
) -> float:
    """Score how confusable candidate (cw) is with target (tw) for listening mode."""
    tw_l, cw_l = tw.lower(), cw.lower()
    score = 0.0

    # Same POS
    if tpos and cpos and tpos == cpos:
        score += 2.0

    # Spelling similarity (normalised Levenshtein)
    sd = _levenshtein(tw_l, cw_l)
    mx = max(len(tw_l), len(cw_l))
    if mx:
        score += (1 - sd / mx) * 5

    # Common prefix
    pfx = 0
    while pfx < len(tw_l) and pfx < len(cw_l) and tw_l[pfx] == cw_l[pfx]:
        pfx += 1
    score += min(pfx * 0.8, 3.0)

    # Common suffix
    sfx = 0
    while sfx < len(tw_l) and sfx < len(cw_l) and tw_l[-(sfx + 1)] == cw_l[-(sfx + 1)]:
        sfx += 1
    score += min(sfx * 0.5, 1.5)

    # Similar length ±2
    if abs(len(tw_l) - len(cw_l)) <= 2:
        score += 0.5

    # Phonetic similarity
    if tp and cp:
        tp_s = _IPA_STRIP.sub('', tp).lower()
        cp_s = _IPA_STRIP.sub('', cp).lower()
        if tp_s and cp_s:
            pd = _levenshtein(tp_s, cp_s)
            mp = max(len(tp_s), len(cp_s))
            if mp:
                score += (1 - pd / mp) * 4

    return score


# ── GET /api/ai/similar-words ─────────────────────────────────────────────────

@ai_bp.route('/similar-words', methods=['GET'])
@token_required
def get_similar_words(current_user: User):
    """
    Return the N most confusable words from the global vocabulary pool.
    Query params:
      word     – target word (required)
      phonetic – IPA string (optional, improves phonetic scoring)
      pos      – part of speech (optional)
      n        – result count (default 10, max 20)
    """
    target_word = (request.args.get('word') or '').strip()
    if not target_word:
        return jsonify({'error': 'word is required'}), 400

    target_phonetic = request.args.get('phonetic', '')
    target_pos      = request.args.get('pos', '')
    n               = min(int(request.args.get('n', 10)), 20)

    pool = _get_global_vocab_pool()
    tw_lower = target_word.lower()

    scored: list[tuple[float, dict]] = []
    for w in pool:
        if w['word'].lower() == tw_lower:
            continue
        s = _confusability_score(
            target_word, target_phonetic, target_pos,
            w['word'], w.get('phonetic', ''), w.get('pos', ''),
        )
        scored.append((s, w))

    scored.sort(key=lambda x: -x[0])
    return jsonify({'words': [w for _, w in scored[:n]]})


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

    # ── Recent study sessions (last 20) for AI context ────────────────────────
    recent_sessions = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.words_studied > 0)
        .order_by(UserStudySession.started_at.desc())
        .limit(20)
        .all()
    )

    # Per-chapter session stats: session count + accuracy trend (last 5 sessions per chapter)
    from collections import defaultdict
    chapter_sessions: dict = defaultdict(list)
    for s in UserStudySession.query.filter_by(user_id=user_id).filter(UserStudySession.words_studied > 0).order_by(UserStudySession.started_at.desc()).limit(200).all():
        key = f"{s.book_id}__{s.chapter_id}"
        chapter_sessions[key].append(s)

    chapter_session_stats = {}
    from routes.books import VOCAB_BOOKS
    book_title_map = {b['id']: b['title'] for b in VOCAB_BOOKS}

    for key, sessions in chapter_sessions.items():
        book_id, chapter_id = key.split('__', 1)
        # Accuracy per session (oldest → newest)
        ordered = sorted(sessions, key=lambda s: s.started_at or 0)
        accuracies = [
            round(s.correct_count / s.words_studied * 100)
            for s in ordered if s.words_studied > 0
        ]
        # Trend: compare average of first half vs last half
        if len(accuracies) >= 2:
            mid = max(1, len(accuracies) // 2)
            early_avg = sum(accuracies[:mid]) / mid
            late_avg = sum(accuracies[mid:]) / max(len(accuracies) - mid, 1)
            trend = "↑进步" if late_avg - early_avg >= 5 else "↓下滑" if early_avg - late_avg >= 5 else "→稳定"
        else:
            trend = "—"
        total_words = sum(s.words_studied for s in sessions)
        avg_acc = round(sum(accuracies) / len(accuracies)) if accuracies else 0
        chapter_session_stats[key] = {
            'book_id': book_id,
            'chapter_id': chapter_id,
            'book_title': book_title_map.get(book_id, book_id),
            'session_count': len(sessions),
            'total_words': total_words,
            'avg_accuracy': avg_acc,
            'accuracies': accuracies,
            'trend': trend,
            'modes': list({s.mode for s in sessions if s.mode}),
        }

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

    book_word_count_map = {b['id']: b.get('word_count', 0) for b in VOCAB_BOOKS}

    for book_id, stats in book_map.items():
        stats['title'] = book_title_map.get(book_id, book_id)
        stats['wordCount'] = book_word_count_map.get(book_id, 0)
        stats['progress'] = round(stats['correctCount'] / (stats['correctCount'] + stats.get('wrongCount', 0)) * 100) if (stats['correctCount'] + stats.get('wrongCount', 0)) > 0 else 0

    # Recent trend: use actual study sessions (more reliable than chapter progress timestamps)
    if len(recent_sessions) >= 4:
        mid = len(recent_sessions) // 2
        # recent_sessions is newest-first; older sessions = second half
        newer = recent_sessions[:mid]
        older = recent_sessions[mid:]
        def _avg_acc(sessions):
            items = [s for s in sessions if s.words_studied > 0]
            if not items:
                return 0
            return sum(s.correct_count / s.words_studied for s in items) / len(items)
        trend = "improving" if _avg_acc(newer) > _avg_acc(older) + 0.05 else \
                "declining" if _avg_acc(newer) < _avg_acc(older) - 0.05 else "stable"
    elif recent_sessions:
        trend = "stable"
    else:
        # Fall back to chapter progress trend
        recent_cp = UserChapterProgress.query.filter_by(user_id=user_id).order_by(
            UserChapterProgress.updated_at.desc()
        ).limit(5).all()
        if len(recent_cp) >= 2:
            first_half = sum(r.correct_count / max(r.correct_count + r.wrong_count, 1) for r in recent_cp[len(recent_cp)//2:])
            second_half = sum(r.correct_count / max(r.correct_count + r.wrong_count, 1) for r in recent_cp[:len(recent_cp)//2])
            trend = "improving" if second_half > first_half else "declining" if second_half < first_half else "stable"
        else:
            trend = "new"

    # Build serialisable recent-session list
    recent_sessions_data = []
    for s in recent_sessions[:10]:
        acc = round(s.correct_count / s.words_studied * 100) if s.words_studied else 0
        recent_sessions_data.append({
            'mode': s.mode,
            'book_id': s.book_id,
            'chapter_id': s.chapter_id,
            'book_title': book_title_map.get(s.book_id or '', s.book_id or ''),
            'words_studied': s.words_studied,
            'correct_count': s.correct_count,
            'wrong_count': s.wrong_count,
            'accuracy': acc,
            'duration_seconds': s.duration_seconds,
            'started_at': s.started_at.isoformat() if s.started_at else None,
        })

    # Load persistent AI memory for this user
    memory = _load_memory(user_id)

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
        'recentTrend': trend,
        'recentSessions': recent_sessions_data,
        'chapterSessionStats': list(chapter_session_stats.values()),
        'totalSessions': len(recent_sessions),
        'memory': memory,
    })


# ── POST /api/ai/ask ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习规划助手，名叫"雅思小助手"。请用中文回复用户。

你具备以下能力：
1. 分析用户的学习数据（进度、准确率、错词分布、当前学习状态、历史练习记录）
2. 给出学习计划建议（每日学习量、复习节奏），提供可操作的选项让用户选择
3. 激励用户保持学习习惯，结合用户目标和进步趋势给出针对性反馈
4. 解释英文单词的用法，通过网络搜索获取权威例句
5. 记住用户的目标、习惯、偏好，在未来对话中持续引用

## 记忆工具：remember_user_note
当对话中出现以下信息时，**主动调用 remember_user_note** 工具将其持久化：
- 用户的考试目标（如"目标7分"、"6月考试"）
- 每日学习计划（如"每天学30分钟"、"每天100词"）
- 学习偏好（如"喜欢听力模式"、"不喜欢默写"）
- 薄弱点（如"学术词汇较弱"、"听力场景词容易混淆"）
- 重要成就（如"完成第5章，正确率95%"）

调用示例：对用户说"好的，我记下来了"之后，立即调用 remember_user_note。
不要每次都问用户是否要记住，直接记录即可。

## 上下文优先级（从高到低）
1. 【AI记忆】— 跨会话持久的用户目标和 AI 笔记（最重要，始终优先引用）
2. 【历史对话摘要】— 压缩的旧会话上下文
3. 【最近练习记录】— 实际练习行为数据
4. 【当前学习状态】— 当前正在做什么
5. 【用户学习数据摘要】— 整体统计数字

## 最重要的原则：优先使用用户的真实数据
- 引用【AI记忆】中的内容时，要自然融入回复（"我记得你说过目标是7分…"）
- 如果用户问你记住了哪些单词，要明确说出具体单词名称，而不是泛泛而谈
- 如果用户在学习过程中问你当前单词的例句，先用 web_search 搜索真实例句
- 绝对不要在用户询问个人学习情况时给出通用词汇表

## 当用户没有历史数据时（totalLearned=0 或 [当前学习状态] 为空）
- 说明用户刚开始，先询问他们的目标：每天多少时间、目标分数等
- 获取到目标后立即用 remember_user_note 记录
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


def _chat_with_tools(
    messages: list[dict],
    tools: list | None = None,
    max_iterations: int = 5,
    extra_handlers: dict | None = None,
) -> dict:
    """
    Chat with MiniMax, automatically handling tool_use blocks.
    Appends assistant responses and tool results to messages in-place.
    Returns the final text response.

    extra_handlers: optional dict of {tool_name: callable} that extends/overrides
    TOOL_HANDLERS for this call (used to inject per-request handlers, e.g. memory writes).
    """
    handlers = {**TOOL_HANDLERS, **(extra_handlers or {})}
    for i in range(max_iterations):
        response = chat(messages, tools=tools, max_tokens=4096)

        if response.get("type") == "tool_call":
            tool_name = response.get("tool")
            tool_input = response.get("input", {})
            tool_call_id = response.get("tool_call_id", f"call_{i}")
            handler = handlers.get(tool_name)

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


GREET_SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习规划助手，名叫"雅思小助手"。请用中文回复用户。

你的任务是生成一条个性化的问候语，让用户感到被关注和激励。

## 问候规则
- 如果用户有历史学习数据（totalLearned > 0），回顾他们的进度并鼓励继续
- 如果用户正在学习中（有 [当前学习状态]），提及当前进度
- 如果用户是新用户（totalLearned=0），热情欢迎，引导开始学习
- 问候语要简洁（3-5句话），不要过长
- 可以提供 2-3 个选项让用户快速选择接下来要做什么

## 回复格式
直接输出问候内容，可在末尾加选项：
[options]
A. 选项A
B. 选项B
[/options]
"""


def _build_learning_context_msg(ctx_data: dict, frontend_context: dict) -> str:
    """Build a combined context message from server data + frontend state."""
    parts = []

    # ── Persistent AI memory (goals, notes, compressed history) ──────────────
    memory = ctx_data.get('memory', {})
    goals = memory.get('goals', {})
    ai_notes = memory.get('ai_notes', [])
    conv_summary = memory.get('conversation_summary', '')

    if goals or ai_notes or conv_summary:
        parts.append("【AI记忆（跨会话持久）】")
        if goals:
            goal_parts = []
            if goals.get('target_band'):
                goal_parts.append(f"目标分数：{goals['target_band']}")
            if goals.get('exam_date'):
                goal_parts.append(f"考试日期：{goals['exam_date']}")
            if goals.get('daily_minutes'):
                goal_parts.append(f"每日学习：{goals['daily_minutes']}分钟")
            if goals.get('focus'):
                goal_parts.append(f"重点方向：{goals['focus']}")
            if goal_parts:
                parts.append("  用户目标：" + "，".join(goal_parts))
        if ai_notes:
            cat_zh = {'goal': '目标', 'habit': '习惯', 'weakness': '薄弱', 'preference': '偏好', 'achievement': '成就', 'other': '其他'}
            for n in ai_notes[-10:]:  # last 10 notes
                cat = cat_zh.get(n.get('category', 'other'), n.get('category', ''))
                parts.append(f"  [{cat}] {n.get('note', '')}（{n.get('created_at', '')}）")
        if conv_summary:
            parts.append(f"\n【历史对话摘要】\n{conv_summary}")

    # Server-side learning summary
    total_learned = ctx_data.get('totalLearned', 0)
    total_correct = ctx_data.get('totalCorrect', 0)
    total_wrong = ctx_data.get('totalWrong', 0)
    accuracy = ctx_data.get('accuracyRate', 0)
    trend = ctx_data.get('recentTrend', 'new')
    books = ctx_data.get('books', [])
    wrong_words = ctx_data.get('wrongWords', [])
    recent_sessions = ctx_data.get('recentSessions', [])
    chapter_stats = ctx_data.get('chapterSessionStats', [])

    trend_zh = {'improving': '上升', 'declining': '下滑', 'stable': '平稳', 'new': '刚开始'}.get(trend, trend)

    parts.append(
        f"【用户学习数据摘要】\n"
        f"总学习词数：{total_learned}\n"
        f"总正确数：{total_correct}  总错误数：{total_wrong}\n"
        f"整体准确率：{accuracy}%\n"
        f"近期趋势：{trend_zh}\n"
        f"正在学习的词书：{len(books)} 本"
    )
    for b in books:
        parts.append(
            f"  - {b.get('title', b.get('id'))} "
            f"(准确率 {b.get('accuracy', 0)}%，错词数 {b.get('wrongCount', 0)})"
        )

    # ── Recent sessions (最近练习记录) ────────────────────────────────────────
    if recent_sessions:
        parts.append("\n【最近练习记录（最新10条）】")
        mode_zh = {
            'smart': '智能', 'listening': '听音选义', 'meaning': '看词选义',
            'dictation': '听写', 'radio': '随身听', 'quickmemory': '速记',
        }
        for s in recent_sessions:
            date_str = (s.get('started_at') or '')[:10]
            mode_label = mode_zh.get(s.get('mode', ''), s.get('mode', '未知'))
            chapter_label = f"第{s.get('chapter_id', '?')}章" if s.get('chapter_id') else '全书'
            book_label = s.get('book_title') or s.get('book_id') or '?'
            dur = s.get('duration_seconds', 0) or 0
            dur_str = f"{dur // 60}分{dur % 60}秒" if dur >= 60 else f"{dur}秒"
            parts.append(
                f"  {date_str} | {book_label} {chapter_label} | {mode_label} | "
                f"{s.get('words_studied', 0)}词 | 正确率{s.get('accuracy', 0)}% | 用时{dur_str}"
            )
    else:
        parts.append("\n【最近练习记录】暂无")

    # ── Per-chapter repeated practice stats ───────────────────────────────────
    repeated = [c for c in chapter_stats if c.get('session_count', 0) >= 2]
    if repeated:
        # Sort by session count desc, show top 5
        repeated.sort(key=lambda c: c.get('session_count', 0), reverse=True)
        parts.append("\n【多次练习章节（练了2次以上的）】")
        for c in repeated[:5]:
            acc_list = c.get('accuracies', [])
            acc_str = ' → '.join(f"{a}%" for a in acc_list[-5:])  # last 5 sessions
            modes_str = '、'.join(c.get('modes', []))
            parts.append(
                f"  {c.get('book_title', c.get('book_id', '?'))} 第{c.get('chapter_id', '?')}章："
                f"共练 {c.get('session_count')} 次，"
                f"平均正确率 {c.get('avg_accuracy')}%，"
                f"趋势 {c.get('trend', '—')}，"
                f"各次正确率 [{acc_str}]，"
                f"使用模式：{modes_str}"
            )

    if wrong_words:
        words_list = '、'.join([w['word'] for w in wrong_words[:20]])
        parts.append(f"\n错词列表（最近50条）：{words_list}")
    else:
        parts.append("\n错词列表：暂无")

    # Frontend session context
    if frontend_context:
        ctx_str = _build_context_msg(frontend_context)
        if ctx_str and ctx_str != '暂无':
            parts.append(f"\n[当前学习状态]\n{ctx_str}")

    return '\n'.join(parts)


@ai_bp.route('/greet', methods=['POST'])
@token_required
def greet(current_user: User):
    """
    Personalized greeting — called when user opens the AI chat panel.
    Returns a greeting based on the user's real learning progress.
    """
    body = request.get_json() or {}
    frontend_context = body.get('context', {})

    messages = [{"role": "system", "content": GREET_SYSTEM_PROMPT}]

    try:
        ctx_resp = get_context(current_user)
        ctx_data = ctx_resp.get_json()
        context_msg = _build_learning_context_msg(ctx_data, frontend_context)
        messages.append({"role": "user", "content": f"[学习数据]\n{context_msg}\n\n请根据以上数据，生成一条个性化的问候。"})
    except Exception as e:
        import logging
        logging.warning(f"[AI] greet context load failed for user={current_user.id}: {e}")
        messages.append({"role": "user", "content": "请生成一条欢迎问候语，用户可能刚开始学习。"})

    try:
        response = _chat_with_tools(messages, tools=None)
        final_text = response.get("text", str(response))
        options = _parse_options(final_text)
        clean_reply = _strip_options(final_text)
        # Save greeting as the opening assistant turn so /ask can reference it
        _save_turn(current_user.id, '[用户打开了AI助手]', clean_reply)
        return jsonify({'reply': clean_reply, 'options': options})
    except Exception as e:
        return jsonify({'error': f'AI service error: {str(e)}'}), 500


# ── Conversation history helpers ──────────────────────────────────────────────

_HISTORY_LIMIT = 20  # max past turns to include in context


def _load_history(user_id: int) -> list[dict]:
    """Load last N conversation turns from DB as LLM-ready message dicts."""
    rows = (
        UserConversationHistory.query
        .filter_by(user_id=user_id)
        .order_by(UserConversationHistory.created_at.desc())
        .limit(_HISTORY_LIMIT)
        .all()
    )
    # Reverse so oldest first
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def _save_turn(user_id: int, user_message: str, assistant_reply: str):
    """Persist a user+assistant turn to DB."""
    try:
        db.session.add(UserConversationHistory(
            user_id=user_id, role='user', content=user_message
        ))
        db.session.add(UserConversationHistory(
            user_id=user_id, role='assistant', content=assistant_reply
        ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import logging
        logging.warning(f"[AI] Failed to save conversation turn: {e}")


# ── User memory helpers ───────────────────────────────────────────────────────

def _get_or_create_memory(user_id: int) -> 'UserMemory':
    """Return the UserMemory row for this user, creating it if absent."""
    mem = UserMemory.query.filter_by(user_id=user_id).first()
    if not mem:
        mem = UserMemory(user_id=user_id)
        db.session.add(mem)
        db.session.flush()   # assign id without full commit
    return mem


def _load_memory(user_id: int) -> dict:
    """Return serialisable memory dict for context injection."""
    mem = UserMemory.query.filter_by(user_id=user_id).first()
    if not mem:
        return {}
    return {
        'goals': mem.get_goals(),
        'ai_notes': mem.get_ai_notes(),
        'conversation_summary': mem.conversation_summary or '',
    }


def _add_memory_note(user_id: int, note: str, category: str) -> str:
    """Append an AI-written note to UserMemory.ai_notes. Returns confirmation."""
    from datetime import datetime as _dt
    try:
        mem = _get_or_create_memory(user_id)
        notes = mem.get_ai_notes()
        # Avoid exact duplicates
        if not any(n.get('note') == note for n in notes):
            notes.append({
                'category': category,
                'note': note,
                'created_at': _dt.utcnow().strftime('%Y-%m-%d'),
            })
            # Keep last 30 notes to avoid unbounded growth
            mem.set_ai_notes(notes[-30:])
        db.session.commit()
        return f"已记录：[{category}] {note}"
    except Exception as e:
        db.session.rollback()
        import logging
        logging.warning(f"[AI] Failed to save memory note: {e}")
        return f"记录失败：{e}"


# Threshold: when total turns exceed this, compress the oldest chunk
_SUMMARIZE_THRESHOLD = 40   # total turns before triggering compression
_SUMMARIZE_CHUNK = 20       # how many old turns to compress each time


def _maybe_summarize_history(user_id: int):
    """If conversation history is long, compress old turns into UserMemory.conversation_summary."""
    total = UserConversationHistory.query.filter_by(user_id=user_id).count()
    mem = UserMemory.query.filter_by(user_id=user_id).first()
    already_summarized = mem.summary_turn_count if mem else 0

    unsummarized = total - already_summarized
    if unsummarized <= _SUMMARIZE_THRESHOLD:
        return  # Not enough new turns yet

    # Fetch the oldest un-summarized chunk
    old_rows = (
        UserConversationHistory.query
        .filter_by(user_id=user_id)
        .order_by(UserConversationHistory.created_at.asc())
        .offset(already_summarized)
        .limit(_SUMMARIZE_CHUNK)
        .all()
    )
    if not old_rows:
        return

    # Build a conversation snippet for the LLM to summarize
    snippet = '\n'.join(
        f"{'用户' if r.role == 'user' else 'AI'}：{r.content[:300]}"
        for r in old_rows
    )
    existing_summary = mem.conversation_summary if mem else ''

    summary_prompt = [
        {"role": "system", "content": (
            "你是一个摘要助手，请将以下对话压缩为一段简洁的中文摘要（100-200字），"
            "重点保留：用户的学习目标、偏好、困难、AI给出的重要建议和用户的关键反应。"
            "不要编造内容，只提炼对话中已有的信息。"
        )},
        {"role": "user", "content": (
            (f"【已有摘要】\n{existing_summary}\n\n" if existing_summary else '') +
            f"【新增对话（{len(old_rows)}条）】\n{snippet}\n\n"
            "请输出更新后的完整摘要："
        )},
    ]
    try:
        resp = chat(summary_prompt, max_tokens=400)
        new_summary = resp.get('text', '').strip()
        if new_summary:
            mem = _get_or_create_memory(user_id)
            mem.conversation_summary = new_summary
            mem.summary_turn_count = already_summarized + len(old_rows)
            db.session.commit()
    except Exception as e:
        import logging
        logging.warning(f"[AI] Summarization failed for user={user_id}: {e}")


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
        context_msg = _build_learning_context_msg(ctx_data, frontend_context)
        messages.append({"role": "user", "content": f"[学习数据]\n{context_msg}"})
    except Exception as e:
        logging.warning(f"[AI] Failed to fetch user context: {e}")
        messages.append({"role": "user", "content": "[学习数据]\n数据加载失败，请根据用户当前状态回复。"})
        # Still inject frontend context if available
        if frontend_context:
            ctx_str = _build_context_msg(frontend_context)
            messages.append({"role": "user", "content": f"[当前学习状态]\n{ctx_str}"})

    # Load and append conversation history so AI remembers past turns
    history = _load_history(current_user.id)
    messages.extend(history)

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

    # Build per-request handler for remember_user_note so it has access to user_id
    def _handle_remember(note: str, category: str = 'other') -> str:
        return _add_memory_note(current_user.id, note, category)

    extra_handlers = {'remember_user_note': _handle_remember}

    # Run chat with tool calling support (includes web_search + remember_user_note)
    try:
        response = _chat_with_tools(messages, tools=TOOLS, extra_handlers=extra_handlers)

        final_text = response.get("text", str(response))
        options = _parse_options(final_text)
        # Strip [options] blocks from the visible reply text
        clean_reply = _strip_options(final_text)

        # Persist this turn so future calls include it as history
        _save_turn(current_user.id, user_message, clean_reply)

        # Auto-save Q&A as a learning note for the journal
        try:
            word_ctx = frontend_context.get('currentWord') if frontend_context else None
            note = UserLearningNote(
                user_id=current_user.id,
                question=user_message,
                answer=clean_reply,
                word_context=word_ctx,
            )
            db.session.add(note)
            db.session.commit()
        except Exception as note_err:
            db.session.rollback()
            logging.warning(f"[AI] Failed to save learning note: {note_err}")

        # Trigger background summarization if history is getting long (non-blocking)
        try:
            _maybe_summarize_history(current_user.id)
        except Exception:
            pass

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
            # Overwrite dimension stats if provided (client sends latest snapshot)
            if 'listeningCorrect' in w:
                existing.listening_correct = w['listeningCorrect']
                existing.listening_wrong   = w.get('listeningWrong', 0)
                existing.meaning_correct   = w.get('meaningCorrect', 0)
                existing.meaning_wrong     = w.get('meaningWrong', 0)
                existing.dictation_correct = w.get('dictationCorrect', 0)
                existing.dictation_wrong   = w.get('dictationWrong', 0)
        else:
            new_w = UserWrongWord(
                user_id=current_user.id,
                word=w['word'],
                phonetic=w.get('phonetic'),
                pos=w.get('pos'),
                definition=w.get('definition'),
                wrong_count=w.get('wrongCount', 1),
                listening_correct=w.get('listeningCorrect', 0),
                listening_wrong=w.get('listeningWrong', 0),
                meaning_correct=w.get('meaningCorrect', 0),
                meaning_wrong=w.get('meaningWrong', 0),
                dictation_correct=w.get('dictationCorrect', 0),
                dictation_wrong=w.get('dictationWrong', 0),
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


@ai_bp.route('/start-session', methods=['POST'])
@token_required
def start_session(current_user: User):
    """Create a session record with server-side start time; returns sessionId for later completion."""
    session = UserStudySession(
        user_id=current_user.id,
        started_at=datetime.utcnow(),
    )
    db.session.add(session)
    db.session.commit()
    return jsonify({'sessionId': session.id}), 201


@ai_bp.route('/log-session', methods=['POST'])
@token_required
def log_session(current_user: User):
    """Persist a study session record to the database.

    If sessionId is provided the existing session row (created by /start-session) is
    updated and duration_seconds is calculated server-side from started_at → now.
    Otherwise a new row is inserted using the client-supplied durationSeconds.
    """
    body = request.get_json() or {}
    try:
        session_id = body.get('sessionId')
        if session_id:
            # Update the existing session row created by /start-session
            session = UserStudySession.query.filter_by(
                id=session_id, user_id=current_user.id
            ).first()
            if session:
                ended_at = datetime.utcnow()
                session.ended_at = ended_at
                session.duration_seconds = max(0, int((ended_at - session.started_at).total_seconds()))
                session.mode = body.get('mode', session.mode)
                session.book_id = body.get('bookId', session.book_id)
                session.chapter_id = body.get('chapterId', session.chapter_id)
                session.words_studied = body.get('wordsStudied', 0)
                session.correct_count = body.get('correctCount', 0)
                session.wrong_count = body.get('wrongCount', 0)
                db.session.commit()
                return jsonify({'id': session.id}), 200

        # Fallback: create a new row using client-supplied timestamps/duration
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


# ── GET /api/ai/quick-memory ──────────────────────────────────────────────────

@ai_bp.route('/quick-memory', methods=['GET'])
@token_required
def get_quick_memory(current_user: User):
    """Return all quick-memory records for the current user."""
    records = UserQuickMemoryRecord.query.filter_by(user_id=current_user.id).all()
    return jsonify({'records': [r.to_dict() for r in records]}), 200


# ── POST /api/ai/quick-memory/sync ───────────────────────────────────────────

@ai_bp.route('/quick-memory/sync', methods=['POST'])
@token_required
def sync_quick_memory(current_user: User):
    """Bulk upsert quick-memory records. Accepts {records: [{word, status, firstSeen, lastSeen, knownCount, unknownCount, nextReview}]}."""
    body = request.get_json() or {}
    records_in = body.get('records', [])
    if not isinstance(records_in, list):
        return jsonify({'error': 'records must be a list'}), 400

    for r in records_in:
        word = (r.get('word') or '').strip().lower()
        if not word:
            continue
        existing = UserQuickMemoryRecord.query.filter_by(
            user_id=current_user.id, word=word
        ).first()
        if existing:
            # Only overwrite if client data is newer (lastSeen is epoch ms)
            if (r.get('lastSeen') or 0) >= (existing.last_seen or 0):
                existing.status        = r.get('status', existing.status)
                existing.first_seen    = r.get('firstSeen', existing.first_seen)
                existing.last_seen     = r.get('lastSeen', existing.last_seen)
                existing.known_count   = r.get('knownCount', existing.known_count)
                existing.unknown_count = r.get('unknownCount', existing.unknown_count)
                existing.next_review   = r.get('nextReview', existing.next_review)
                # fuzzy_count: take the max so it never decreases
                if r.get('fuzzyCount') is not None:
                    existing.fuzzy_count = max(existing.fuzzy_count or 0, r['fuzzyCount'])
        else:
            new_rec = UserQuickMemoryRecord(
                user_id=current_user.id,
                word=word,
                status=r.get('status', 'unknown'),
                first_seen=r.get('firstSeen', 0),
                last_seen=r.get('lastSeen', 0),
                known_count=r.get('knownCount', 0),
                unknown_count=r.get('unknownCount', 0),
                next_review=r.get('nextReview', 0),
                fuzzy_count=r.get('fuzzyCount', 0),
            )
            db.session.add(new_rec)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({'ok': True}), 200


# ── GET /api/ai/smart-stats ───────────────────────────────────────────────────

@ai_bp.route('/smart-stats', methods=['GET'])
@token_required
def get_smart_stats(current_user: User):
    """Return all smart-mode word stats for the current user."""
    stats = UserSmartWordStat.query.filter_by(user_id=current_user.id).all()
    return jsonify({'stats': [s.to_dict() for s in stats]}), 200


# ── POST /api/ai/smart-stats/sync ─────────────────────────────────────────────

@ai_bp.route('/smart-stats/sync', methods=['POST'])
@token_required
def sync_smart_stats(current_user: User):
    """Bulk upsert smart-mode word stats. Accepts {stats: [{word, listening, meaning, dictation}]}."""
    body = request.get_json() or {}
    stats_in = body.get('stats', [])
    if not isinstance(stats_in, list):
        return jsonify({'error': 'stats must be a list'}), 400

    for s in stats_in:
        word = (s.get('word') or '').strip().lower()
        if not word:
            continue
        listening = s.get('listening') or {}
        meaning   = s.get('meaning')   or {}
        dictation = s.get('dictation') or {}

        existing = UserSmartWordStat.query.filter_by(
            user_id=current_user.id, word=word
        ).first()
        if existing:
            existing.listening_correct = listening.get('correct', existing.listening_correct)
            existing.listening_wrong   = listening.get('wrong',   existing.listening_wrong)
            existing.meaning_correct   = meaning.get('correct',   existing.meaning_correct)
            existing.meaning_wrong     = meaning.get('wrong',     existing.meaning_wrong)
            existing.dictation_correct = dictation.get('correct', existing.dictation_correct)
            existing.dictation_wrong   = dictation.get('wrong',   existing.dictation_wrong)
        else:
            new_stat = UserSmartWordStat(
                user_id=current_user.id,
                word=word,
                listening_correct=listening.get('correct', 0),
                listening_wrong=listening.get('wrong', 0),
                meaning_correct=meaning.get('correct', 0),
                meaning_wrong=meaning.get('wrong', 0),
                dictation_correct=dictation.get('correct', 0),
                dictation_wrong=dictation.get('wrong', 0),
            )
            db.session.add(new_stat)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({'ok': True}), 200
