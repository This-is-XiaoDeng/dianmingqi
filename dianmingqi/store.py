"""名单存储（进程内缓存 + 磁盘持久化）。

导入后的名单缓存在内存中，同时持久化到磁盘（默认 ``~/.dianmingqi/names.json``），
重启后自动恢复，无需再次导入。提供线程安全的最小读写，写文件采用原子替换。
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import List, Optional


def default_data_file() -> str:
    """默认持久化文件位置：用户主目录下的 .dianmingqi/names.json。"""
    return str(Path.home() / ".dianmingqi" / "names.json")


class NameStore:
    def __init__(self, data_file: Optional[str] = None) -> None:
        self._names: List[str] = []
        self._source: Optional[str] = None
        self._remaining: List[str] = []
        self._data_file: Optional[str] = data_file
        self._lock = threading.Lock()

    def configure(self, data_file: str) -> None:
        with self._lock:
            self._data_file = data_file

    @property
    def data_file(self) -> Optional[str]:
        with self._lock:
            return self._data_file

    def replace(self, names: List[str], source: Optional[str] = None, remaining: Optional[List[str]] = None) -> None:
        with self._lock:
            self._names = list(names)
            self._source = source
            self._remaining = list(remaining if remaining is not None else names)

    def get(self) -> List[str]:
        with self._lock:
            return list(self._names)

    def remaining(self) -> List[str]:
        with self._lock:
            return list(self._remaining)

    def set_remaining(self, remaining: List[str]) -> None:
        with self._lock:
            self._remaining = list(remaining)

    def count(self) -> int:
        with self._lock:
            return len(self._names)

    def source(self) -> Optional[str]:
        with self._lock:
            return self._source

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._names) == 0

    # ---- 持久化 ----

    def load(self) -> bool:
        """从磁盘加载名单。返回是否成功加载到数据（含空名单也算加载成功）。"""
        with self._lock:
            path = self._data_file
        if not path or not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            names = [str(n) for n in data.get("names", [])]
            source = data.get("source")
            remaining = [str(n) for n in data.get("remaining", names)]
            with self._lock:
                self._names = names
                self._source = source if isinstance(source, str) else None
                self._remaining = remaining
            return True
        except (OSError, ValueError, TypeError):
            # 文件损坏时忽略，保持空状态
            return False

    def save(self) -> bool:
        """把当前状态写到磁盘（原子替换）。"""
        with self._lock:
            path = self._data_file
            data = {
                "names": list(self._names),
                "source": self._source,
                "remaining": list(self._remaining),
            }
        if not path:
            return False
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp, path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
            return True
        except OSError:
            return False


store = NameStore()