"""名单存储（进程内缓存）。

导入后的名单缓存在内存中，重启即丢失，符合「本地单机小工具」的定位。
提供线程安全的最小读写。
"""
from __future__ import annotations

import threading
from typing import List, Optional


class NameStore:
    def __init__(self) -> None:
        self._names: List[str] = []
        self._lock = threading.Lock()
        self._source: Optional[str] = None

    def replace(self, names: List[str], source: Optional[str] = None) -> None:
        with self._lock:
            self._names = list(names)
            self._source = source

    def get(self) -> List[str]:
        with self._lock:
            return list(self._names)

    def count(self) -> int:
        with self._lock:
            return len(self._names)

    def source(self) -> Optional[str]:
        with self._lock:
            return self._source

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._names) == 0


store = NameStore()
