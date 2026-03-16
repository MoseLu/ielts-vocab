"""
测试千问 ASR 实时语音识别服务
"""
import os
import json
import time
import threading
import websocket
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get('DASHSCOPE_API_KEY', '')
print(f"API Key: {API_KEY[:20]}...")

if not API_KEY:
    print("错误: 未找到 DASHSCOPE_API_KEY")
    exit(1)

def test_asr():
    """测试 ASR WebSocket 连接"""
    url = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3-asr-flash-realtime"
    
    print(f"\n连接到: {url}")
    
    ws_ready = threading.Event()
    results = []
    
    def on_open(ws):
        print("[WS] 连接已打开")
        # 发送会话配置
        config = {
            "event_id": "event_1",
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "input_audio_format": "pcm",
                "sample_rate": 16000,
                "input_audio_transcription": {
                    "language": "zh"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.0,
                    "silence_duration_ms": 1000
                }
            }
        }
        ws.send(json.dumps(config))
        print("[WS] 已发送会话配置")
    
    def on_message(ws, message):
        data = json.loads(message)
        event_type = data.get('type', '')
        print(f"[WS] 收到事件: {event_type}")
        
        if event_type == 'session.created':
            print(f"[WS] 会话已创建: {data.get('session', {}).get('id')}")
            ws_ready.set()
        elif event_type == 'conversation.item.input_audio_transcription.completed':
            text = data.get('transcript', '')
            print(f"[WS] 识别结果: {text}")
            results.append(text)
        elif event_type == 'error':
            print(f"[WS] 错误: {data}")
    
    def on_error(ws, error):
        print(f"[WS] WebSocket 错误: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"[WS] 连接关闭: {close_status_code} - {close_msg}")
    
    ws = websocket.WebSocketApp(
        url,
        header=[
            f"Authorization: Bearer {API_KEY}",
            "OpenAI-Beta: realtime=v1"
        ],
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # 在线程中运行
    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()
    
    # 等待会话创建
    if ws_ready.wait(timeout=10):
        print("\n[测试] 会话已就绪，可以发送音频")
        print("[测试] 等待 3 秒后关闭...")
        time.sleep(3)
        
        # 发送结束事件
        finish_event = {
            "event_id": "event_finish",
            "type": "session.finish"
        }
        ws.send(json.dumps(finish_event))
        print("[WS] 已发送结束事件")
    else:
        print("[测试] 超时：会话未创建")
    
    time.sleep(2)
    ws.close()
    print("\n[测试] 完成")

if __name__ == '__main__':
    test_asr()