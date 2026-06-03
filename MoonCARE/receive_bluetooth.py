#!/usr/bin/env python3
"""
接收 MoonCare 蓝牙串口数据并发送到后端
使用 screen /dev/cu.Bluetooth-Incoming-Port 9600 方式
"""
import serial
import requests
import json
from datetime import datetime
import time

# 配置
BLUETOOTH_PORT = "/dev/cu.Bluetooth-Incoming-Port"
BAUD_RATE = 9600
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
        print(f"  -> 服务器响应: {r.json()}")
        return True
    except Exception as e:
        print(f"  -> 服务器错误: {e}")
        return False

def parse_and_forward(raw_data):
    """解析 JSON 数据并转发"""
    print(f"收到: {raw_data}")
    try:
        data = json.loads(raw_data)
        temp = float(data.get("temp")) if data.get("temp") else None
        bpm = float(data.get("bpm")) if data.get("bpm") else None
        motion = data.get("motion")
        wearing = data.get("wearing", False)
        send_to_server(temp, bpm, motion, wearing)
    except json.JSONDecodeError as e:
        print(f"  JSON 解析错误: {e}")
    except Exception as e:
        print(f"  解析错误: {e}")

def main():
    # 先尝试打开已存在的连接
    try:
        ser = serial.Serial(BLUETOOTH_PORT, BAUD_RATE, timeout=1)
        print(f"已连接到 {BLUETOOTH_PORT}")
    except serial.SerialException:
        print(f"无法打开 {BLUETOOTH_PORT}，等待其他设备连接...")
        print("请确保 MoonCare-Demo 蓝牙已连接")
        return

    print("等待数据...\n")
    buffer = ""

    try:
        while True:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                buffer += data.decode('utf-8', errors='ignore')

                # 处理完整的数据行
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if line:
                        parse_and_forward(line)

            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        ser.close()

if __name__ == "__main__":
    print("=" * 50)
    print("MoonCare 蓝牙数据接收器")
    print("=" * 50)
    main()
