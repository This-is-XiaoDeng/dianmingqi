"""picker + FastAPI 接口测试。"""
import io

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from dianmingqi.app import create_app
from dianmingqi.picker import picker
from dianmingqi.store import store


@pytest.fixture(autouse=True)
def clean_state(tmp_path):
    """每个测试前清空全局缓存并指向临时持久化文件，避免测试间相互污染。"""
    store.configure(str(tmp_path / "names.json"))
    store.replace([])
    store.set_remaining([])
    picker.set_names([])
    yield


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_pick_no_repeat_exhausts_names():
    from dianmingqi.picker import Picker
    p = Picker(names=["张三", "李四", "王五"])
    picked = {p.pick() for _ in range(3)}
    assert picked == {"张三", "李四", "王五"}
    # 抽完自动重置，可继续抽
    assert p.pick() in {"张三", "李四", "王五"}


def test_pick_repeat_mode():
    from dianmingqi.picker import Picker
    p = Picker(names=["张三"], repeat=True)
    assert p.pick() == "张三"
    assert p.pick() == "张三"


def test_import_txt_and_pick(client, tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("张三\n李四\n王五\n", encoding="utf-8")
    # 先 GET 确认空
    assert client.get("/api/names").json()["count"] == 0

    with open(f, "rb") as fh:
        resp = client.post("/api/import", files={"file": ("a.txt", fh, "text/plain")})
    assert resp.status_code == 200
    assert resp.json()["count"] == 3

    names = client.get("/api/names").json()
    assert names["count"] == 3

    r = client.post("/api/pick", json={"repeat": False})
    assert r.status_code == 200
    assert r.json()["name"] in {"张三", "李四", "王五"}
    assert r.json()["remaining"] == 2


def test_import_xlsx(client, tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["姓名"])
    ws.append(["张三"])
    ws.append(["李四"])
    p = tmp_path / "b.xlsx"
    wb.save(p)

    with open(p, "rb") as fh:
        resp = client.post("/api/import", files={"file": ("b.xlsx", fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, data={"column": "1"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


def test_pick_before_import_400(client):
    assert client.post("/api/pick", json={}).status_code == 400


def test_reset(client, tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("张三\n李四\n", encoding="utf-8")
    with open(f, "rb") as fh:
        client.post("/api/import", files={"file": ("a.txt", fh, "text/plain")})
    client.post("/api/pick", json={"repeat": False})
    r = client.post("/api/reset")
    assert r.status_code == 200
    assert r.json()["count"] == 2


# ---- 持久化 ----

def test_import_persists_and_restores(tmp_path):
    """导入后写入磁盘；重新创建应用（模拟重启）自动恢复名单。"""
    data_dir = tmp_path / "data"
    f = tmp_path / "a.txt"
    f.write_text("张三\n李四\n王五\n", encoding="utf-8")

    # 第一次启动：导入
    store.configure(str(data_dir / "names.json"))
    picker.set_names([])
    app1 = create_app(data_dir=str(data_dir))
    with TestClient(app1) as c:
        with open(f, "rb") as fh:
            r = c.post("/api/import", files={"file": ("a.txt", fh, "text/plain")})
        assert r.json()["count"] == 3

    # 持久化文件已写入
    import json
    assert (data_dir / "names.json").exists()
    saved = json.loads((data_dir / "names.json").read_text(encoding="utf-8"))
    assert saved["names"] == ["张三", "李四", "王五"]

    # 第二次启动（新的应用实例，等价于重启进程）：无需再导入
    store.replace([])
    picker.set_names([])
    app2 = create_app(data_dir=str(data_dir))
    with TestClient(app2) as c:
        names = c.get("/api/names").json()
        assert names["count"] == 3
        assert names["names"] == ["张三", "李四", "王五"]


def test_persist_remaining_state(tmp_path):
    """抽取后的剩余候选也持久化，重启后继续从未抽中的人里抽。"""
    data_dir = tmp_path / "data"
    f = tmp_path / "a.txt"
    f.write_text("张三\n李四\n王五\n", encoding="utf-8")

    store.configure(str(data_dir / "names.json"))
    picker.set_names([])
    app1 = create_app(data_dir=str(data_dir))
    with TestClient(app1) as c:
        with open(f, "rb") as fh:
            c.post("/api/import", files={"file": ("a.txt", fh, "text/plain")})
        r = c.post("/api/pick", json={"repeat": False})
        picked = r.json()["name"]
        assert r.json()["remaining"] == 2

    # 重启后剩余候选恢复为 2 人（除了已抽中的 picked）
    store.replace([])
    picker.set_names([])
    app2 = create_app(data_dir=str(data_dir))
    assert store.count() == 3
    assert len(store.remaining()) == 2
    assert picked not in store.remaining()
    with TestClient(app2) as c:
        names = c.get("/api/names").json()
        assert names["count"] == 3
        # 复位后全名单可抽，initial 抽中的人应在候选里
        c.post("/api/reset")
        all_after_reset = {c.post("/api/pick", json={}).json()["name"] for _ in range(3)}
        assert picked in all_after_reset
