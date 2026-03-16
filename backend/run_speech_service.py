#!/usr/bin/env python
"""
语音识别服务启动脚本
"""

import sys
import os
import signal
from pathlib import Path

# 确保能找到模块
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# 设置工作目录
os.chdir(backend_dir)

# 导入并运行服务
from speech_service import print_banner, socketio, app, active_sessions, PORT

if __name__ == '__main__':
    print_banner()

    print("\nStarting Speech Recognition Service...")
    print("Press Ctrl+C to stop\n")

    # 使用 threading 模式的 WSGI 服务器
    from wsgiref.simple_server import make_server

    def signal_handler(sig, frame):
        print("\n[Speech] Shutting down...")
        # 关闭所有活跃会话
        for sid, session in list(active_sessions.items()):
            try:
                ws = session.get('ws')
                if ws:
                    ws.close()
            except:
                pass
        print("[Speech] Goodbye")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        httpd = make_server('0.0.0.0', PORT, app)
        print(f"[Speech] Server started on port {PORT}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Speech] Shutting down...")
        httpd.shutdown()
        print("[Speech] Goodbye")