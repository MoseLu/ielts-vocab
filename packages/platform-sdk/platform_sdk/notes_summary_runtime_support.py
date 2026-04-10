from __future__ import annotations

import threading

from platform_sdk.llm_provider_adapter import stream_text

SUMMARY_SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习助手。请根据用户当天的学习数据和 AI 问答记录，生成一份简洁、可读的每日学习总结，使用 Markdown 格式。

总结结构请尽量包含：
1. 学习概况
2. AI 问答记录
3. 薄弱点与建议
4. 今日亮点

要求：
- 使用中文
- 内容具体，不要空泛
- 如果当天学习记录很少，也要明确指出并给出下一步建议
"""

GENERATE_COOLDOWN_SECONDS = 300
SUMMARY_JOB_TTL_SECONDS = 3600
SUMMARY_MODE_LABELS = {
    'smart': '智能练习',
    'listening': '听音选义',
    'meaning': '默写模式',
    'dictation': '听写',
    'radio': '随身听',
    'quickmemory': '速记',
    'errors': '错词强化',
}

_summary_jobs: dict[str, dict] = {}
_summary_jobs_lock = threading.Lock()


def stream_summary_text(user_content: str):
    messages = [{'role': 'user', 'content': user_content}]
    yield from stream_text(messages, system=SUMMARY_SYSTEM_PROMPT, max_tokens=2000)
