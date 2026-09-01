"""启动服务器：随机端口 + 自动打开浏览器 + 网页关闭后自动退出。"""
from __future__ import annotations

import logging
import random
import socket
import threading
import time
import webbrowser
from typing import Optional

import uvicorn

from .app import create_app

logger = logging.getLogger("dianmingqi")

# 页面上一次心跳时间（client 持续 ping 表示页面还开着）
_last_ping: list[float] = [0.0]
# 是否至少出现过一次页面连接
_had_client: list[bool] = [False]
_lock = threading.Lock()

# 页面关闭后等待这么久仍无心跳则退出（秒）
EXIT_GRACE = 8.0


def _find_free_port(low: int = 8000, high: int = 9000) -> int:
    for _ in range(200):
        port = random.randint(low, high)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    # 兜底：让系统分配
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def register_heartbeat(app) -> None:
    """在 app 上挂载 /api/ping，供前端心跳（页面还开着）。"""

    @app.get("/api/ping")
    def ping():
        now = time.time()
        with _lock:
            _last_ping[0] = now
            _had_client[0] = True
        return {"ok": True}


def _monitor(server: uvicorn.Server) -> None:
    """当浏览器网页被关闭（停止心跳）后自动关闭服务器。"""
    while True:
        time.sleep(EXIT_GRACE / 2.0)
        with _lock:
            had_client = _had_client[0]
            last = _last_ping[0]
        if had_client and (time.time() - last) > EXIT_GRACE:
            logger.info("网页已关闭，正在退出…")
            server.should_exit = True
            return


def run(
    host: str = "127.0.0.1",
    port: Optional[int] = None,
    open_browser: bool = True,
    data_dir: Optional[str] = None,
) -> None:
    if port is None:
        port = _find_free_port()

    app = create_app(data_dir=data_dir)
    register_heartbeat(app)

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    url = f"http://{host}:{port}/"
    logger.info("点名器已启动：%s", url)

    if open_browser:
        threading.Thread(target=lambda: _open_later(url), daemon=True).start()

    monitor = threading.Thread(target=_monitor, args=(server,), daemon=True)
    monitor.start()

    server.run()


def _open_later(url: str) -> None:
    # 等服务真正起来再开浏览器
    time.sleep(0.8)
    try:
        webbrowser.open(url)
    except Exception as exc:  # pragma: no cover
        logger.warning("自动打开浏览器失败：%s", exc)
