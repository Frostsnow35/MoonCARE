#!/usr/bin/env python3
"""
接收 Arduino USB 串口数据并发送到后端
"""
import serial
import requests
import json
from datetime import datetime

# 配置 - 根据实际调整
SERIAL_PORT = "/dev/cu.usbmodem5B7A1535671"  # Arduino USB 串口
BAUD_RATE = 115200  # Arduino 波特率
SERVER_URL = "http://localhost:8000/api/v1/biometric/upload"
DEVICE_ID = "MOONCARE_USB_001"

def send_to_server(temp, bpm, motion, wearing):
    """发送数据到后端"""
    # wearing 只作为提示信息，不影响数据写入
    if not wearing:
        print("  [注意] 设备未佩戴")

    data = {
        "device_id": DEVICE_ID,
        "timestamp": datetime.now().isoformat(),
        "bpm": bpm if bpm is not None else None,
        "temp": temp if temp is not None else None,
        "motion": motion,
        "confidence": "HIGH" if (bpm and temp) else "MEDIUM"
    }
    try:
        r = requests.post(SERVER_URL, json=data, timeout=5)
        print(f"  -> 已写入数据库 (ID: {r.json().get('data_id', '?')})")
        return True
    except Exception as e:
        print(f"  -> 服务器错误: {e}")
        return False

def parse_and_forward(raw_data):
    """解析 JSON 数据并转发"""
    print(f"收到原始数据: {raw_data}")

    try:
        data = json.loads(raw_data)

        temp = data.get("temp")
        if temp == "null":
            temp = None
        else:
            temp = float(temp)

        bpm = data.get("bpm")
        if bpm == "null":
            bpm = None
        else:
            bpm = float(bpm)

        motion = data.get("motion", "LOW")
        wearing = data.get("wearing", False)

        send_to_server(temp, bpm, motion, wearing)

    except json.JSONDecodeError as e:
        print(f"  JSON 解析错误: {e}")
    except Exception as e:
        print(f"  解析错误: {e}")

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"已连接到 {SERIAL_PORT}")
        print("等待数据...\n")

        while True:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    parse_and_forward(line)
    except serial.SerialException as e:
        print(f"串口错误: {e}")
    except KeyboardInterrupt:
        print("\n已停止")

if __name__ == "__main__":
    print("=" * 50)
    print("MoonCare USB 数据接收器")
    print("=" * 50)
    main()
