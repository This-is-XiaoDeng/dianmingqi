"""FastAPI 应用：提供名单导入与点名接口。"""
from __future__ import annotations

import os
import tempfile
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .importer import parse_file
from .picker import picker
from .store import store

WEBUI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webui")


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


def create_app() -> FastAPI:
    app = FastAPI(title="点名器", version="1.0.0")

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

        store.replace(names, source=file.filename or "")
        picker.set_names(names)
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
        return PickResponse(name=name, remaining=picker.remaining)

    @app.post("/api/reset", response_model=ListResponse)
    def reset():
        picker.reset()
        return ListResponse(names=store.get(), count=store.count(), source=store.source())

    return app


app = create_app()
