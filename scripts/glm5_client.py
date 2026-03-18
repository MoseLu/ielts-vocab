"""
GLM-5 API 客户端封装
处理速率限制：每小时500次请求，整点重置
"""

import sys
import io
import time
import requests
from datetime import datetime, timedelta
from threading import Lock
from functools import wraps

# Windows 控制台编码修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class RateLimiter:
    """速率限制器 - 整点重置机制"""

    def __init__(self, max_requests: int = 500, window_minutes: int = 60):
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.request_count = 0
        self.current_hour = datetime.now().hour
        self.lock = Lock()

    def _get_reset_time(self) -> datetime:
        """获取下一个重置时间点（下一个整点）"""
        now = datetime.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return next_hour

    def _get_wait_seconds(self) -> float:
        """获取需要等待的秒数"""
        reset_time = self._get_reset_time()
        wait_seconds = (reset_time - datetime.now()).total_seconds()
        return max(0, wait_seconds)

    def _check_and_reset(self):
        """检查是否需要重置计数器（跨小时）"""
        current_hour = datetime.now().hour
        if current_hour != self.current_hour:
            self.request_count = 0
            self.current_hour = current_hour

    def acquire(self) -> dict:
        """
        获取请求许可

        Returns:
            dict: {
                'allowed': bool,      # 是否允许请求
                'wait_seconds': float, # 需要等待的秒数（如果不允许）
                'remaining': int,      # 剩余请求数
                'reset_at': str        # 重置时间
            }
        """
        with self.lock:
            self._check_and_reset()

            remaining = self.max_requests - self.request_count
            reset_time = self._get_reset_time()

            if self.request_count >= self.max_requests:
                wait_seconds = self._get_wait_seconds()
                return {
                    'allowed': False,
                    'wait_seconds': wait_seconds,
                    'remaining': 0,
                    'reset_at': reset_time.strftime('%Y-%m-%d %H:%M:%S')
                }

            self.request_count += 1
            return {
                'allowed': True,
                'wait_seconds': 0,
                'remaining': self.max_requests - self.request_count,
                'reset_at': reset_time.strftime('%Y-%m-%d %H:%M:%S')
            }

    def get_status(self) -> dict:
        """获取当前状态"""
        with self.lock:
            self._check_and_reset()
            return {
                'request_count': self.request_count,
                'remaining': self.max_requests - self.request_count,
                'max_requests': self.max_requests,
                'current_hour': self.current_hour,
                'reset_at': self._get_reset_time().strftime('%Y-%m-%d %H:%M:%S')
            }


class GLM5Client:
    """GLM-5 API 客户端"""

    def __init__(self, api_key: str, base_url: str = "https://mydamoxing.cn"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.rate_limiter = RateLimiter(max_requests=500, window_minutes=60)

    def _make_request(self, messages: list, model: str = "glm-5",
                      max_tokens: int = 4096, temperature: float = 0.7,
                      auto_wait: bool = True) -> dict:
        """
        发送请求到 API

        Args:
            messages: 消息列表
            model: 模型名称
            max_tokens: 最大输出tokens
            temperature: 温度参数
            auto_wait: 是否自动等待速率限制重置

        Returns:
            API 响应字典
        """
        # 获取请求许可
        permit = self.rate_limiter.acquire()

        if not permit['allowed']:
            if auto_wait:
                wait_time = permit['wait_seconds']
                print(f"⏳ 达到速率限制，等待 {wait_time:.1f} 秒至 {permit['reset_at']}")
                time.sleep(wait_time + 1)  # 多等1秒确保安全
                # 重新获取许可
                permit = self.rate_limiter.acquire()
            else:
                raise RateLimitError(
                    f"速率限制已达到，请在 {permit['reset_at']} 后重试",
                    wait_seconds=permit['wait_seconds'],
                    reset_at=permit['reset_at']
                )

        # 发送请求
        url = f"{self.base_url}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }

        if temperature != 0.7:
            payload["temperature"] = temperature

        response = requests.post(url, headers=headers, json=payload, timeout=120)

        if response.status_code == 429:
            # 服务器返回 429，可能是额外的速率限制
            retry_after = int(response.headers.get('Retry-After', 60))
            if auto_wait:
                print(f"⏳ 服务器返回 429，等待 {retry_after} 秒")
                time.sleep(retry_after)
                return self._make_request(messages, model, max_tokens, temperature, auto_wait)
            else:
                raise RateLimitError("服务器速率限制", wait_seconds=retry_after)

        response.raise_for_status()
        return response.json()

    def chat(self, user_message: str, system_prompt: str = None,
             max_tokens: int = 4096, auto_wait: bool = True) -> str:
        """
        简单对话接口

        Args:
            user_message: 用户消息
            system_prompt: 系统提示（可选）
            max_tokens: 最大输出tokens
            auto_wait: 是否自动等待

        Returns:
            模型回复文本
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": user_message})

        response = self._make_request(messages, max_tokens=max_tokens, auto_wait=auto_wait)

        # 提取回复文本
        if response.get('content') and len(response['content']) > 0:
            return response['content'][0].get('text', '')

        return ""

    def chat_with_history(self, messages: list, max_tokens: int = 4096,
                          auto_wait: bool = True) -> str:
        """
        带历史记录的对话

        Args:
            messages: 完整消息历史
            max_tokens: 最大输出tokens
            auto_wait: 是否自动等待

        Returns:
            模型回复文本
        """
        response = self._make_request(messages, max_tokens=max_tokens, auto_wait=auto_wait)

        if response.get('content') and len(response['content']) > 0:
            return response['content'][0].get('text', '')

        return ""

    def get_rate_limit_status(self) -> dict:
        """获取速率限制状态"""
        return self.rate_limiter.get_status()


class RateLimitError(Exception):
    """速率限制错误"""

    def __init__(self, message: str, wait_seconds: float = 0, reset_at: str = ""):
        super().__init__(message)
        self.wait_seconds = wait_seconds
        self.reset_at = reset_at


# 使用示例
if __name__ == "__main__":
    # 初始化客户端
    client = GLM5Client(
        api_key="sk-LF8RroI1Xc1OwMgVudF7Q4wEBKHPSW8GLx5T24UQqmYHJ8Ue",
        base_url="https://mydamoxing.cn"
    )

    # 查看当前状态
    status = client.get_rate_limit_status()
    print(f"📊 当前状态: 已用 {status['request_count']}/{status['max_requests']} 次")
    print(f"   剩余: {status['remaining']} 次")
    print(f"   重置时间: {status['reset_at']}")
    print()

    # 简单对话
    print("💬 发送测试消息...")
    response = client.chat("你好，请用一句话介绍你自己")
    print(f"回复: {response}")
    print()

    # 查看更新后的状态
    status = client.get_rate_limit_status()
    print(f"📊 更新后状态: 已用 {status['request_count']}/{status['max_requests']} 次")
    print(f"   剩余: {status['remaining']} 次")