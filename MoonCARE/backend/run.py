"""
MoonCARE 智能情绪管理平台 - 启动脚本
支持 HTTP/2、流式输出、语义缓存等优化特性
"""

import argparse
import os
import sys
from pathlib import Path

# 添加项目路径到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.config import settings


def main():
    parser = argparse.ArgumentParser(description="启动 MoonCARE 智能情绪管理平台")
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="绑定的主机地址 (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务端口 (default: 8000)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="启用热重载 (开发模式)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="工作进程数 (default: 1)"
    )
    
    parser.add_argument(
        "--http2",
        action="store_true",
        default=settings.HTTP2_ENABLED,
        help="启用 HTTP/2 支持"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="日志级别 (default: info)"
    )
    
    args = parser.parse_args()
    
    print("Starting MoonCARE v{0}".format(settings.APP_VERSION))
    print("Service address: http://{0}:{1}".format(args.host, args.port))
    print("API docs: http://{0}:{1}/docs".format(args.host, args.port))
    print("Auto-reload: {0}".format("enabled" if args.reload else "disabled"))
    print("HTTP/2: {0}".format("enabled" if args.http2 else "disabled"))
    print("Semantic cache: {0}".format("enabled" if settings.SEMANTIC_CACHE_ENABLED else "disabled"))
    print("Streaming: {0}".format("enabled" if settings.STREAMING_ENABLED else "disabled"))
    
    # 配置 Uvicorn
    uvicorn_config = {
        "app": "app.main:app",
        "host": args.host,
        "port": args.port,
        "reload": args.reload,
        "workers": args.workers,
        "log_level": args.log_level,
        "access_log": True,
    }
    
    # HTTP/2 配置
    if args.http2:
        uvicorn_config["http"] = "h11"
        print("Note: Production environment recommends HTTPS + HTTP/2 with SSL certificate")
    
    # 启动服务
    try:
        uvicorn.run(**uvicorn_config)
    except Exception as e:
        print("Start failed: {0}".format(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
