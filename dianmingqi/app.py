"""FastAPI 应用：提供名单导入与点名接口。"""
from __future__ import annotations

import os
import sys
import tempfile
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .importer import parse_file
from .picker import picker
from .store import default_data_file, store


def _find_webui_dir() -> str:
    """定位 webui 静态目录。

    兼容多种运行形态：
    - 源码/poetry：相对于包目录 ../webui；
    - Nuitka standalone/onefile：可执行文件旁或解压临时目录。
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(here, "webui"),
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "webui"),
        os.path.join(os.getcwd(), "webui"),
    ]
    for cand in candidates:
        if os.path.isdir(cand):
            return cand
    return candidates[0]


WEBUI_DIR = _find_webui_dir()


class ImportResponse(BaseModel):
    count: int
    source: str


class PickRequest(BaseModel):
    repeat: bool = False


class PickResponse(BaseModel):
    name: Optional[str]
    remaining: int


class ListResponse(BaseModel):
    names: List[str]
    count: int
    source: Optional[str]


def create_app(data_dir: Optional[str] = None) -> FastAPI:
    """创建 FastAPI 应用。

    :param data_dir: 持久化目录（默认 ``~/.dianmingqi``）。
        创建应用时自动恢复上次导入的名单。
    """
    if data_dir:
        store.configure(os.path.join(data_dir, "names.json"))
    elif store.data_file is None:
        store.configure(default_data_file())
    # 恢复持久化名单：导入一次，重启后无需再次导入
    if store.load():
        picker.restore(store.get(), store.remaining())

    app = FastAPI(title="点名器", version="1.1.0")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(os.path.join(WEBUI_DIR, "index.html"))

    @app.get("/api/names", response_model=ListResponse)
    def list_names():
        return ListResponse(names=store.get(), count=store.count(), source=store.source())

    @app.post("/api/import", response_model=ImportResponse)
    async def import_names(
        file: UploadFile = File(...),
        sheet: Optional[int] = Form(None),
        column: Optional[int] = Form(None),
    ):
        suffix = os.path.splitext(file.filename or "")[1] or ".txt"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        try:
            names = parse_file(tmp_path, sheet=sheet, column=column)
        finally:
            os.unlink(tmp_path)

        if not names:
            raise HTTPException(status_code=400, detail="名单为空，请检查文件内容")

        store.replace(names, source=file.filename or "", remaining=list(names))
        picker.set_names(names)
        store.save()
        return ImportResponse(count=store.count(), source=store.source() or "")

    @app.post("/api/pick", response_model=PickResponse)
    def pick(req: Optional[PickRequest] = None):
        repeat = bool(req and req.repeat)
        if store.is_empty():
            raise HTTPException(status_code=400, detail="请先导入名单")
        if picker._repeat != repeat:  # noqa: SLF001
            picker._repeat = repeat  # noqa: SLF001
            picker.reset()
        name = picker.pick()
        store.set_remaining(picker.remaining_names())
        store.save()
        return PickResponse(name=name, remaining=picker.remaining)

    @app.post("/api/reset", response_model=ListResponse)
    def reset():
        picker.reset()
        store.set_remaining(picker.remaining_names())
        store.save()
        return ListResponse(names=store.get(), count=store.count(), source=store.source())

    return app


app = create_app()
