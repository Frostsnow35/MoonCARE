#!/usr/bin/env python3
"""
MoonCARE 一键启动脚本
自动启动 Awareness 记忆服务、后端和前端
"""

import subprocess
import sys
import os
import time
import platform
from pathlib import Path

def print_banner():
    print("=" * 60)
    print("  MoonCARE - 智能情绪管理平台")
    print("  一键启动所有服务")
    print("=" * 60)
    print()

def check_node():
    """检查 Node.js 是否安装"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Node.js 已安装: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    print("✗ Node.js 未安装")
    print("  请访问 https://nodejs.org/ 下载安装")
    return False

def check_python():
    """检查 Python 是否安装"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✓ Python 已安装: {version.major}.{version.minor}.{version.micro}")
        return True

    print(f"✗ Python 版本过低或未安装: {version.major}.{version.minor}.{version.micro}")
    print("  请访问 https://www.python.org/downloads/ 下载 Python 3.10+")
    return False

def check_npm():
    """检查 npm 是否安装"""
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ npm 已安装: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    print("✗ npm 未安装")
    print("  请安装 Node.js（包含 npm）https://nodejs.org/")
    return False

def start_awareness():
    """启动 Awareness 记忆服务"""
    print("\n[1/3] 启动 Awareness 记忆服务...")
    print("  (本地记忆存储，无需账号，完全离线)")

    try:
        # 使用 npx 启动 awareness 服务
        process = subprocess.Popen(
            ['npx', '--yes', '@awareness-sdk/local@latest', 'start'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 等待服务启动
        print("  等待服务启动...")
        time.sleep(5)

        # 检查进程是否还在运行
        if process.poll() is None:
            print("  ✓ Awareness 服务已启动 (http://localhost:37800)")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"  ✗ 启动失败: {stderr}")
            return None

    except Exception as e:
        print(f"  ✗ 启动失败: {e}")
        return None

def start_backend():
    """启动后端服务"""
    print("\n[2/3] 启动后端 FastAPI 服务...")

    backend_dir = Path(__file__).parent / "backend"
    if not backend_dir.exists():
        print(f"  ✗ 后端目录不存在: {backend_dir}")
        return None

    # 检查依赖
    requirements_file = backend_dir / "requirements.txt"
    if requirements_file.exists():
        print("  检查 Python 依赖...")

    try:
        # 启动后端服务
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(backend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print("  ✓ 后端服务已启动 (http://localhost:8000)")
        print("  ✓ API 文档: http://localhost:8000/docs")
        return process

    except Exception as e:
        print(f"  ✗ 启动失败: {e}")
        return None

def start_frontend():
    """启动前端服务"""
    print("\n[3/3] 启动前端 Vue 服务...")

    frontend_dir = Path(__file__).parent / "frontend"
    if not frontend_dir.exists():
        print(f"  ✗ 前端目录不存在: {frontend_dir}")
        return None

    # 检查 npm 依赖
    if not (frontend_dir / "node_modules").exists():
        print("  安装前端依赖...")
        subprocess.run(['npm', 'install'], cwd=str(frontend_dir), check=True)

    try:
        # 启动前端服务
        process = subprocess.Popen(
            ['npm', 'run', 'dev'],
            cwd=str(frontend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print("  ✓ 前端服务已启动 (http://localhost:3000)")
        return process

    except Exception as e:
        print(f"  ✗ 启动失败: {e}")
        return None

def main():
    """主函数"""
    print_banner()

    # 检查环境
    print("检查环境...")
    if not check_node():
        print("\n请先安装 Node.js")
        sys.exit(1)

    if not check_python():
        print("\n请先安装 Python 3.10+")
        sys.exit(1)

    if not check_npm():
        print("\n请先安装 npm（通过 Node.js）")
        sys.exit(1)

    # 启动服务
    processes = []

    awareness = start_awareness()
    if awareness:
        processes.append(awareness)
    else:
        print("\n警告: Awareness 服务启动失败，记忆功能将使用本地数据库")

    backend = start_backend()
    if backend:
        processes.append(backend)
    else:
        print("\n错误: 后端服务启动失败")
        sys.exit(1)

    frontend = start_frontend()
    if frontend:
        processes.append(frontend)
    else:
        print("\n错误: 前端服务启动失败")
        sys.exit(1)

    # 打印完成信息
    print("\n" + "=" * 60)
    print("  所有服务启动完成！")
    print("=" * 60)
    print()
    print("  前端地址:    http://localhost:3000")
    print("  后端地址:    http://localhost:8000")
    print("  API 文档:    http://localhost:8000/docs")
    print("  记忆服务:    http://localhost:37800")
    print()
    print("  按 Ctrl+C 停止所有服务")
    print("=" * 60)

    # 等待用户中断
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n正在停止所有服务...")

        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()

        print("所有服务已停止")

if __name__ == "__main__":
    main()
