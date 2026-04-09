import functools
import json
import os
import random
import re
import time
import uuid
from datetime import datetime, timedelta

from sqlalchemy import text

from models import (
    WRONG_WORD_DIMENSIONS,
    WRONG_WORD_PENDING_REVIEW_TARGET,
    CustomBook,
    CustomBookChapter,
    CustomBookWord,
    User,
    UserBookProgress,
    UserChapterModeProgress,
    UserChapterProgress,
    UserConversationHistory,
    UserLearningNote,
    UserMemory,
    UserQuickMemoryRecord,
    UserSmartWordStat,
    UserStudySession,
    UserWrongWord,
    _build_wrong_word_dimension_states,
    _empty_wrong_word_dimension_state,
    _normalize_wrong_word_dimension_state,
    _summarize_wrong_word_dimension_states,
    db,
)
from services.ai_context_service import build_context_data as _build_ai_context_data
from services.ai_shared_support import (
    alltime_distinct_practiced_words as _shared_alltime_distinct_words,
    alltime_words_display as _shared_alltime_words_display,
    calc_streak_days as _shared_calc_streak_days,
    chapter_title_map as _shared_chapter_title_map,
    decorate_wrong_words_with_quick_memory_progress as _shared_decorate_wrong_words,
    load_json_data as _shared_load_json_data,
    normalize_word_key as _shared_normalize_word_key,
    normalize_word_list as _shared_normalize_word_list,
    parse_client_epoch_ms as _shared_parse_client_epoch_ms,
    quick_memory_word_stats as _shared_quick_memory_word_stats,
    record_smart_dimension_delta_event as _shared_record_smart_delta,
    track_metric as _shared_track_metric,
)
from services import ai_vocab_catalog_service, books_catalog_service, books_registry_service
from services.learner_profile import build_learner_profile
from services.learning_events import record_learning_event
from services.listening_confusables import get_preset_listening_confusables
from services.llm import (
    TOOL_HANDLERS,
    TOOLS,
    chat,
    correct_text,
    differentiate_synonyms,
    stream_chat_events,
    web_search,
)
from services.local_time import (
    current_local_date,
    local_day_window_ms,
    recent_local_day_range,
    resolve_local_day_window,
    utc_naive_to_epoch_ms,
    utc_naive_to_local_date_key,
    utc_now_naive,
)
from services.memory_topics import build_memory_topics
from services.quick_memory_schedule import (
    load_user_quick_memory_records,
    resolve_quick_memory_next_review_ms,
)
from services.runtime_async import maybe_timeout, spawn_background
from services.study_sessions import (
    find_pending_session,
    get_live_pending_session_snapshot,
    get_session_window_metrics,
    normalize_chapter_id,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'routes', 'ai_routes', 'data')
_PENDING_SESSION_REUSE_WINDOW_SECONDS = 5
_PENDING_SESSION_MATCH_WINDOW_SECONDS = 15
_QUICK_MEMORY_MASTERY_TARGET = 6

SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习规划助手，名叫"雅思小助手"。请用中文回复用户。

你具备以下能力：
1. 分析用户的学习数据（进度、准确率、错词分布、当前学习状态、历史练习记录）
2. 给出学习计划建议（每日学习量、复习节奏），提供可操作的选项让用户选择
3. 激励用户保持学习习惯，结合用户目标和进步趋势给出针对性反馈
4. 解释英文单词的用法，通过网络搜索获取权威例句
5. 记住用户的目标、习惯、偏好，在未来对话中持续引用

## 四维记忆系统（必须遵守）
- 单词掌握必须拆成 4 个独立维度：认读、听力、口语、书写。
- 四个维度独立达标、独立复习，全部达标后，才能把一个单词称为“完全掌握”。
- 认读周期：第 1 / 3 / 7 / 30 天，目标是看到英文后 1 秒内说出核心中文义。
- 听力周期：第 1 / 2 / 4 / 7 / 14 天，目标是听到发音立刻反应词义。
- 口语周期：第 1 / 3 / 7 / 15 / 30 天，目标是发音正确并能主动造句。
- 书写周期：第 1 / 2 / 5 / 9 / 21 天，目标是看到中文能零错误拼写英文。
- 当上下文里出现【四维记忆系统】时，优先按这个区块决定今日复习顺序和计划，而不是只看总正确率。
- 如果口语维度显示“证据不足”或“尚未开始”，要明确指出这一点，并安排发音 + 造句任务，不要假装已经掌握。
- 不要把某一个维度达标说成整个单词已经永久掌握。

## 工具使用指南

### remember_user_note — 持久化用户信息
当对话中出现以下信息时，**主动调用** 将其持久化（无需问用户）：
- 考试目标（如"目标7分"、"6月考试"）
- 每日学习计划（如"每天学30分钟"）
- 学习偏好、薄弱点、重要成就

### get_wrong_words — 获取错词列表
当用户问"我哪些词错得多"、"帮我复习错词"、"我的薄弱词汇"，或者提到某个具体单词、某组关键词、昨天/最近的错词时调用。
参数：
- `query`：用户提到的单词或关键词。只要问题里出现具体词，就优先传 `query` 做相关检索。
- `recent_first`：做泛化复盘时设为 `true`，优先看最近产生或最近更新的错词。
- `limit`：只取必要数量，默认 12。不要为了回答一个局部问题把全部错词都拉出来。

### get_chapter_words — 获取章节单词
当用户问"第X章有哪些词"、"帮我看看这章内容"、"制定某章学习计划"时调用。
参数：book_id（词书ID）、chapter_id（章节号，整数）

### get_book_chapters — 获取词书章节结构
当用户问"这本书有几章"、"我完成了哪些章节"、"制定全书学习计划"时调用。
参数：book_id（词书ID）

**book_id 对照表：**
- 雅思听力高频词汇 → ielts_listening_premium
- 雅思阅读高频词汇 → ielts_reading_premium
- 雅思综合词汇5000+ → ielts_comprehensive
- 雅思终极词汇库 → ielts_ultimate
- AWL学术词汇表 → awl_academic

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

### 选项处理规则
- 用户可能只回复 "A" 或 "B" 等，识别并继续执行
- 回复选项时选项要有实际意义，每个选项要有明确的差异化

## 重要原则
- 如果看到【相关历史问答】，说明用户在同一主题反复卡住。要明确承认这一点，换一种解释方式，并主动追问是否需要更深入辨析、例句或小测。
- 不要编造例句，尽量通过网络搜索获取真实、地道的例句
- 建议要具体可执行（具体词数、时间安排）
- 语言要友好鼓励，不要过于严肃
- 如果用户还没有学习数据，鼓励他们开始学习
"""

def _normalize_chapter_id(value) -> str | None:
    return normalize_chapter_id(value)


def _normalize_word_key(value: str | None) -> str:
    return _shared_normalize_word_key(value)


def _normalize_word_list(values) -> list[str]:
    return _shared_normalize_word_list(values)


def _record_smart_dimension_delta_event(**kwargs):
    return _shared_record_smart_delta(**kwargs)


def _parse_client_epoch_ms(value) -> datetime | None:
    return _shared_parse_client_epoch_ms(value)


def _decorate_wrong_words_with_quick_memory_progress(user_id: int, words: list[UserWrongWord]) -> list[dict]:
    return _shared_decorate_wrong_words(
        user_id,
        words,
        get_global_vocab_pool=ai_vocab_catalog_service._get_global_vocab_pool,
        resolve_quick_memory_vocab_entry=ai_vocab_catalog_service._resolve_quick_memory_vocab_entry,
    )


def _find_pending_session(*, user_id: int, mode: str | None, book_id: str | None, chapter_id: str | None, started_at: datetime | None = None, window_seconds: int = _PENDING_SESSION_MATCH_WINDOW_SECONDS):
    return find_pending_session(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        started_at=started_at,
        window_seconds=window_seconds,
    )


def _load_json_data(filename: str, default):
    return _shared_load_json_data(DATA_DIR, filename, default)


def _track_metric(user_id: int, metric: str, payload: dict | None = None):
    return _shared_track_metric(user_id, metric, payload)


def _alltime_distinct_practiced_words(user_id: int) -> int:
    return _shared_alltime_distinct_words(user_id)


def _alltime_words_display(user_id: int, chapter_words_sum: int) -> int:
    return _shared_alltime_words_display(user_id, chapter_words_sum)


def _chapter_title_map(book_id: str) -> dict:
    try:
        return _shared_chapter_title_map(
            book_id,
            load_book_chapters=books_catalog_service.load_book_chapters,
        )
    except Exception:
        return {}


def _calc_streak_days(user_id: int, reference_date: str | None = None) -> int:
    now_utc = utc_now_naive()
    effective_reference_date = reference_date or utc_naive_to_local_date_key(now_utc)
    return _shared_calc_streak_days(user_id, effective_reference_date)


def _quick_memory_word_stats(user_id: int):
    now_utc = utc_now_naive()
    return _shared_quick_memory_word_stats(user_id, now_utc=now_utc)


def _load_vocab_books():
    return books_registry_service.list_vocab_books()


def _serialize_effective_book_progress_proxy(book_id, *, progress_record, chapter_records):
    return books_catalog_service.serialize_effective_book_progress(
        book_id,
        progress_record=progress_record,
        chapter_records=chapter_records,
    )


def _get_context_data(user_id: int) -> dict:
    from services.ai_assistant_memory_service import load_memory

    return _build_ai_context_data(
        user_id,
        alltime_words_display_resolver=_alltime_words_display,
        load_memory_resolver=load_memory,
        load_vocab_books=_load_vocab_books,
        serialize_effective_book_progress=_serialize_effective_book_progress_proxy,
    )
