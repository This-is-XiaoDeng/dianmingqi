"""命令行入口。

用法：
    dianmingqi                # 随机端口启动，自动打开浏览器
    dianmingqi --port 8123    # 指定端口
    dianmingqi --no-browser   # 不自动打开浏览器
"""
from __future__ import annotations

import argparse
import logging


def main() -> None:  # pragma: no cover - 入口
    parser = argparse.ArgumentParser(description="点名器")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    parser.add_argument("--port", type=int, default=None, help="端口（默认随机）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--debug", action="store_true", help="输出调试日志")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from .server import run

    run(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
