"""抽人逻辑。

支持两种模式：
- ``repeat``：可重复抽取（每次从全名单随机）。
- ``no_repeat``(默认)：不重复抽取（抽出的名字会临时移出候选，
  直到所有名字都抽过一轮后自动重置）。
"""
from __future__ import annotations

import random
from typing import List, Optional


class Picker:
    def __init__(self, names: Optional[List[str]] = None, repeat: bool = False) -> None:
        self._pool: List[str] = list(names or [])
        self._repeat = repeat
        self._remaining: List[str] = list(self._pool)

    def set_names(self, names: List[str]) -> None:
        self._pool = list(names)
        self.reset()

    def reset(self) -> None:
        self._remaining = list(self._pool)

    def pick(self) -> Optional[str]:
        if not self._pool:
            return None
        if self._repeat:
            return random.choice(self._pool)
        if not self._remaining:
            # 一轮抽完，自动重置
            self._remaining = list(self._pool)
        idx = random.randrange(len(self._remaining))
        chosen = self._remaining.pop(idx)
        return chosen

    @property
    def remaining(self) -> int:
        return len(self._remaining)


picker = Picker()
