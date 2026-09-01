# 点名器（dianmingqi）

一个面向 **希沃大屏**（Seewo 交互式白板）的随机点名 Web 应用：把名单导入进去，一键随机抽人，字体铺满整个屏幕，适合课堂/会议抽人。

## 特性

- 🎲 **随机点名**：支持「不重复抽取」（抽过的人本轮不再出现，一轮抽完自动重置）与「可重复抽取」。
- 📂 **多数据源**：
  - **txt**：一行一个名字；
  - **xlsx**：选择一整列并自动去除表头（支持指定列号与工作表）。
- 💾 **名单持久化**：导入一次后自动保存到 `~/.dianmingqi/names.json`（可用 `--data-dir` 指定），**重启后无需再次导入**，连剩余未抽中的人也会恢复。
- 🖥️ **希沃大屏适配**：全屏铺满 viewport，字号随名字长度自动缩放，超大触摸按钮，支持空格键触发。
- 🚀 **零配置启动**：随机端口 + 启动后自动打开浏览器，**网页关闭后应用自动退出**，用完即走不残留进程。
- ⚠️ **断连提示**：网页连不上后端（程序被关闭）时全屏提示「无法连接服务器」。
- 🪟 **Windows 单文件版**：GitHub CI 通过 Nuitka 编译为一个 `.exe`，双击即用，并带冒烟测试；打 tag 发 Release 自动编译并上传产物。

## 技术栈

- Python 3.9+ / [Poetry](https://python-poetry.org/)
- [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
- [openpyxl](https://openpyxl.readthedocs.io/)（xlsx 解析）
- 原生 HTML/CSS/JS Web UI（无前端构建步骤）

## 快速开始

```bash
# 1. 安装依赖
poetry install

# 2. 启动（默认随机端口，自动打开浏览器）
poetry run dianmingqi

# 或直接运行
poetry run python -m dianmingqi

# 指定端口 / 不开浏览器 / 指定持久化目录
poetry run dianmingqi --port 8123
poetry run dianmingqi --no-browser
poetry run dianmingqi --data-dir /path/to/data
```

启动后终端会打印访问地址：

```
点名器已启动：http://127.0.0.1:8513/
```

浏览器自动打开该地址。**关闭网页后，约 8 秒应用自动退出。** 再次启动时，上次导入的名单会自动恢复，无需重新导入。

### 手动运行服务器

```bash
uvicorn dianmingqi.app:app
```

## 使用说明

1. 点击 **📂 导入名单** 选择 `txt` 或 `xlsx` 文件。
   - `txt`：一行一个名字，空行自动忽略。
   - `xlsx`：默认读取第 1 列并**去除表头**；可在导入面板输入列号选择其它列。
2. 点击 **🎲 开始点名** 随机抽取（带滚动动画）。
3. 点击 **🔄 重置** 让所有名字重新可抽。

导入的名单与剩余候选会持久化到本地，重启后自动恢复。

## 断连提示

前端持续检测与后端的连接：连续 2 次请求失败（例如程序被关闭）后，全屏提示 **⚠️ 无法连接服务器**；后端恢复后提示自动消失。

## Windows 单文件版

在 [Releases](../../releases) 页面下载 `dianmingqi.exe`，双击即可运行（首次启动解包会稍慢）。无需安装 Python。

也可以在本地编译：

```bash
poetry run python -m nuitka \
  --onefile \
  --assume-yes-for-downloads \
  --windows-console-mode=force \
  --include-data-dir=webui=webui \
  --output-dir=dist \
  --output-filename=dianmingqi.exe \
  dianmingqi/__main__.py
```

## 自动退出原理

页面打开后每 2 秒向 `/api/ping` 发送一次心跳；服务器记录最近一次心跳时间，一旦网页被关闭（心跳停止超过 8 秒）即自动关闭服务进程。这样既不会在无人使用时长期占用端口，也不会因为误开浏览器而残留进程。

## 开发 / 测试

```bash
poetry install --with dev
poetry run pytest -q
```

## 许可证

[AGPL-3.0](./LICENSE)
