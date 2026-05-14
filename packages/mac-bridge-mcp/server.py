#!/usr/bin/env python3
"""
Mac Bridge MCP Server — 雅思词汇本地 Mac 应用与 Claude 的桥接层

提供以下工具：
- check_services     检查所有本地服务健康状态
- get_logs           读取 mac-app 或微服务运行时日志
- launch_app         启动 Mac 本地应用（dev / preview 模式）
- kill_app           停止运行中的 Mac 本地应用进程
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from urllib.error import URLError

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

# --------------------------------------------------------------------------- #
# 路径常量
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parents[2]
MAC_APP_LOG_DIR = REPO_ROOT / "logs" / "runtime" / "mac-apps"
MICROSERVICE_LOG_DIR = REPO_ROOT / "logs" / "runtime" / "microservices-mac"
RUN_MAC_APP_SCRIPT = REPO_ROOT / "scripts" / "run-mac-local-app.sh"

# --------------------------------------------------------------------------- #
# 服务定义（name -> (port, health_url)）
# --------------------------------------------------------------------------- #
SERVICES: dict[str, tuple[int, str]] = {
    "frontend-dev":          (3020, "http://127.0.0.1:3020"),
    "frontend-preview":      (3002, "http://127.0.0.1:3002"),
    "gateway-bff":           (8000, "http://127.0.0.1:8000/health"),
    "identity-service":      (8101, "http://127.0.0.1:8101/ready"),
    "learning-core-service": (8102, "http://127.0.0.1:8102/ready"),
    "catalog-content-service":(8103, "http://127.0.0.1:8103/ready"),
    "ai-execution-service":  (8104, "http://127.0.0.1:8104/ready"),
    "tts-media-service":     (8105, "http://127.0.0.1:8105/ready"),
    "asr-service":           (8106, "http://127.0.0.1:8106/ready"),
    "notes-service":         (8107, "http://127.0.0.1:8107/ready"),
    "admin-ops-service":     (8108, "http://127.0.0.1:8108/ready"),
    "asr-socketio":          (5001, "http://127.0.0.1:5001/ready"),
}

# --------------------------------------------------------------------------- #
# 辅助函数
# --------------------------------------------------------------------------- #

def _probe(url: str, timeout: float = 2.0) -> int:
    """返回 HTTP 状态码，连接失败返回 0。"""
    try:
        with urlopen(url, timeout=timeout) as r:
            return r.status
    except URLError:
        return 0
    except Exception:
        return 0


def _tail(path: Path, lines: int = 100) -> str:
    if not path.exists():
        return f"[文件不存在: {path}]"
    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), str(path)],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout or "[日志为空]"
    except Exception as e:
        return f"[读取失败: {e}]"


def _find_mac_app_pid(mode: str) -> list[int]:
    """通过进程名查找对应模式的 Mac 应用 PID。"""
    label = "开发版" if mode == "dev" else "预览版"
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"雅思词汇{label}"],
            capture_output=True, text=True,
        )
        return [int(p) for p in result.stdout.split() if p.strip()]
    except Exception:
        return []


def _format_status_table(statuses: dict[str, dict]) -> str:
    lines = ["服务状态一览：\n"]
    for name, info in statuses.items():
        icon = "✓" if info["ok"] else "✗"
        lines.append(f"  {icon} {name:<28} {info['status']:>4}  :{info['port']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# MCP Server
# --------------------------------------------------------------------------- #
server = Server("mac-bridge")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="check_services",
            description=(
                "探测所有本地服务的健康端点，返回每个服务的运行状态和 HTTP 状态码。"
                "可指定只检查特定服务名称，或不传参数检查全部。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "services": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "要检查的服务名列表，留空则检查全部。"
                            f"可选值: {list(SERVICES.keys())}"
                        ),
                    }
                },
            },
        ),
        types.Tool(
            name="get_logs",
            description=(
                "读取 mac-app 运行时日志或指定微服务的日志文件（最近 N 行）。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": (
                            "'mac-app-dev' / 'mac-app-preview' 读取 Mac 应用日志，"
                            "或填服务名（如 'gateway-bff'、'identity-service'）"
                            "读取对应微服务日志。"
                        ),
                    },
                    "stream": {
                        "type": "string",
                        "enum": ["stdout", "stderr"],
                        "description": "日志流，默认 stdout。",
                    },
                    "lines": {
                        "type": "integer",
                        "description": "读取末尾行数，默认 100，最大 500。",
                    },
                },
                "required": ["source"],
            },
        ),
        types.Tool(
            name="launch_app",
            description="启动雅思词汇 Mac 本地应用（会触发后端微服务和前端 Vite 启动）。",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["dev", "preview"],
                        "description": "启动模式：dev（端口 3020）或 preview（端口 3002）。",
                    }
                },
                "required": ["mode"],
            },
        ),
        types.Tool(
            name="kill_app",
            description="停止运行中的雅思词汇 Mac 本地应用（按模式）。",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["dev", "preview"],
                        "description": "要停止的应用模式。",
                    }
                },
                "required": ["mode"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if name == "check_services":
        return await _handle_check_services(arguments)
    if name == "get_logs":
        return await _handle_get_logs(arguments)
    if name == "launch_app":
        return await _handle_launch_app(arguments)
    if name == "kill_app":
        return await _handle_kill_app(arguments)
    raise ValueError(f"Unknown tool: {name}")


async def _handle_check_services(args: dict) -> list[types.TextContent]:
    requested = args.get("services") or list(SERVICES.keys())
    unknown = [s for s in requested if s not in SERVICES]
    if unknown:
        return [types.TextContent(type="text", text=f"未知服务名: {unknown}")]

    statuses: dict[str, dict] = {}
    loop = asyncio.get_event_loop()

    async def probe_one(svc: str) -> None:
        port, url = SERVICES[svc]
        code = await loop.run_in_executor(None, _probe, url)
        statuses[svc] = {"port": port, "status": code, "ok": 200 <= code < 500}

    await asyncio.gather(*[probe_one(s) for s in requested])

    up = sum(1 for v in statuses.values() if v["ok"])
    summary = f"在线 {up}/{len(statuses)}\n\n"
    return [types.TextContent(type="text", text=summary + _format_status_table(statuses))]


async def _handle_get_logs(args: dict) -> list[types.TextContent]:
    source: str = args["source"]
    stream: str = args.get("stream", "stdout")
    lines: int = min(int(args.get("lines", 100)), 500)

    # mac-app 日志
    if source.startswith("mac-app-"):
        mode = source.removeprefix("mac-app-")  # dev / preview
        suffix = "out" if stream == "stdout" else "err"
        log_path = MAC_APP_LOG_DIR / f"{mode}.{suffix}.log"
        content = _tail(log_path, lines)
        return [types.TextContent(type="text", text=f"[{log_path}]\n{content}")]

    # 微服务日志
    service_name = source
    suffix = "out" if stream == "stdout" else "err"
    log_path = MICROSERVICE_LOG_DIR / f"{service_name}.{suffix}.log"
    if not log_path.exists():
        # 也尝试 .log 不带 out/err 后缀
        alt = MICROSERVICE_LOG_DIR / f"{service_name}.log"
        if alt.exists():
            log_path = alt

    content = _tail(log_path, lines)
    return [types.TextContent(type="text", text=f"[{log_path}]\n{content}")]


async def _handle_launch_app(args: dict) -> list[types.TextContent]:
    mode: str = args["mode"]
    if not RUN_MAC_APP_SCRIPT.exists():
        return [types.TextContent(type="text", text=f"[错误] 启动脚本不存在: {RUN_MAC_APP_SCRIPT}")]

    loop = asyncio.get_event_loop()

    def _launch() -> str:
        proc = subprocess.Popen(
            ["bash", str(RUN_MAC_APP_SCRIPT), mode],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        # 等待脚本完成（脚本内部会 open 应用后退出）
        try:
            out, _ = proc.communicate(timeout=120)
            return out or f"[已启动，退出码 {proc.returncode}]"
        except subprocess.TimeoutExpired:
            proc.kill()
            return "[超时：脚本运行超过 120 秒]"

    result = await loop.run_in_executor(None, _launch)
    return [types.TextContent(type="text", text=result)]


async def _handle_kill_app(args: dict) -> list[types.TextContent]:
    mode: str = args["mode"]
    pids = _find_mac_app_pid(mode)
    if not pids:
        return [types.TextContent(type="text", text=f"未找到运行中的 {mode} 模式应用进程。")]

    killed: list[int] = []
    failed: list[str] = []
    for pid in pids:
        try:
            os.kill(pid, 15)  # SIGTERM
            killed.append(pid)
        except ProcessLookupError:
            pass
        except PermissionError as e:
            failed.append(f"PID {pid}: {e}")

    parts: list[str] = []
    if killed:
        parts.append(f"已发送 SIGTERM 给进程: {killed}")
    if failed:
        parts.append(f"终止失败: {failed}")
    return [types.TextContent(type="text", text="\n".join(parts))]


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
async def main() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
