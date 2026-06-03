#!/usr/bin/env python3
"""
实时读取硬件数据通过USB串口，并发送到后端API
Usage: python3 read_hardware.py
"""

import serial
import requests
import json
import time
import sys

# 配置
SERIAL_PORT = "/dev/cu.usbmodem5B7A1535671"
BAUD_RATE = 115200
API_URL = "http://localhost:8000/api/v1/biometric/raw"
DEVICE_ID = "DEVICE_001"
INTERVAL = 1  # 发送间隔（秒）

def read_and_send():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"已连接到 {SERIAL_PORT}")
        print(f"数据将发送到 {API_URL}")
        print(f"按 Ctrl+C 退出\n")

        buffer = ""
        while True:
            try:
                # 读取串口数据
                data = ser.read(ser.in_waiting or 1)
                if data:
                    buffer += data.decode('utf-8', errors='ignore')

                    # 查找JSON对象（以{开头，以}结尾）
                    while '{' in buffer and '}' in buffer:
                        start = buffer.find('{')
                        end = buffer.find('}', start)
                        if end != -1:
                            json_str = buffer[start:end+1]
                            buffer = buffer[end+1:]

                            try:
                                obj = json.loads(json_str)
                                print(f"收到数据: temp={obj.get('temp')}, bpm={obj.get('bpm')}, motion={obj.get('motion')}")

                                # 发送到后端
                                try:
                                    response = requests.post(
                                        API_URL,
                                        json=obj,
                                        params={"user_id": 1, "device_id": DEVICE_ID},
                                        timeout=5
                                    )
                                    if response.status_code == 200:
                                        print(f"  -> 上传成功: {response.json()}")
                                    else:
                                        print(f"  -> 上传失败: {response.status_code}")
                                except requests.exceptions.RequestException as e:
                                    print(f"  -> 上传失败: {e}")

                            except json.JSONDecodeError:
                                pass  # 不是有效的JSON，跳过

                time.sleep(0.1)

            except serial.SerialException as e:
                print(f"串口错误: {e}")
                break

    except serial.SerialException as e:
        print(f"无法打开串口 {SERIAL_PORT}: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已退出")
        sys.exit(0)

if __name__ == "__main__":
    read_and_send()
