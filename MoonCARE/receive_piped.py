#!/usr/bin/env python3
"""
通过管道接收 MoonCare 蓝牙数据并发送到后端

使用方法:
    screen /dev/cu.Bluetooth-Incoming-Port 9600 | python3 receive_piped.py
"""
import sys
import requests
import json
from datetime import datetime

SERVER_URL = "http://localhost:8000/api/v1/biometric/upload"
DEVICE_ID = "MOONCARE_BT"

def send_to_server(temp, bpm, motion, wearing):
    """发送数据到后端"""
    if not wearing:
        print("  -> 设备未佩戴，跳过")
        return False

    data = {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now().isoformat(),
        "bpm": bpm,
        "temp": temp,
        "motion": motion if motion else "LOW",
        "confidence": "HIGH" if (bpm and temp) else "MEDIUM"
    }
    try:
        r = requests.post(SERVER_URL, json=data, timeout=5)
        print(f"  -> 已发送: temp={temp}, bpm={bpm}, motion={motion}, wearing={wearing}")
        print(f"  -> 服务器: {r.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print("  -> 服务器未运行 (http://localhost:8000)")
        return False
    except Exception as e:
        print(f"  -> 错误: {e}")
        return False

def main():
    print("=" * 50)
    print("MoonCare 蓝牙数据接收器 (管道模式)")
    print("=" * 50)
    print(f"目标服务器: {SERVER_URL}")
    print("等待数据...\n")

    buffer = ""

    try:
        for line in sys.stdin:
            buffer += line.strip()

            # 处理完整的数据行
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if not line:
                    continue

                # 跳过 screen 的控制字符
                if line.startswith('^') or '\x1b' in line:
                    continue

                try:
                    data = json.loads(line)
                    temp = float(data.get("temp")) if data.get("temp") else None
                    bpm = float(data.get("bpm")) if data.get("bpm") else None
                    motion = data.get("motion")
                    wearing = data.get("wearing", False)
                    send_to_server(temp, bpm, motion, wearing)
                except json.JSONDecodeError:
                    pass  # 忽略非 JSON 行
    except KeyboardInterrupt:
        print("\n已停止")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()
