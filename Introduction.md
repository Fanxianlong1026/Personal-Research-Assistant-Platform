# 科研助手平台 - 开发文档

> 供后续接手的开发者/智能体快速了解架构、技术栈、规范与已知问题。

## Hello
## 项目概览

面向科研人员的效率工具，含五大模块：论文管理、知识库笔记、实验记录、任务看板、AI问答。

**技术栈**: FastAPI（后端）+ React/Vite/TypeScript（前端）+ SQLite + Ant Design（UI）。所有依赖与文件均在 `d:\NewCode\科研助手平台\` 下。

## 快速启动

### 启动后端（端口 8000）
本地 AI 模式依赖 PyTorch + transformers，安装在 conda 环境 `pytorch_nightly`（Python 3.11 + CUDA），**必须用该环境的 Python 启动后端**：
```powershell
cd d:\NewCode\科研助手平台\backend
$env:PYTHONIOENCODING="utf-8"
& "D:\Anaconda\envs\pytorch_nightly\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API 文档: http://localhost:8000/docs

> 项目自带的 `backend/venv` 未装 torch/transformers，用它启动会在调用 AI 时报 `ModuleNotFoundError: No module named 'torch'`。纯 CRUD 接口可用 venv，AI 功能必须用 `pytorch_nightly`。

### 启动前端（端口 5173）
```powershell
cd d:\NewCode\科研助手平台\frontend
npm run dev
```

### 关闭端口
```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
```

### AI 功能配置
由 `backend/.env` 的 `AI_MODE` 控制两种模式：

**本地模型（默认 `AI_MODE=local`）** — 本地 Qwen2.5-3B
```
AI_MODE=local
AI_LOCAL_MODEL_PATH=D:\NewCode\Qwen2.5\model
AI_LOCAL_DEVICE=auto      # auto/cuda/cpu
AI_MAX_NEW_TOKENS=1024
```
- 模型在**首次对话请求时懒加载**，首条回复前端显示“正在加载本地模型…”。
- `POST /api/v1/ai/model/load` 手动预加载，`GET /api/v1/ai/model/status` 查状态。
- 实测 RTX/CUDA：加载 ~5s，生成 64 token ~1.5s。

**远程 API（`AI_MODE=api`）** — OpenAI 兼容服务（DeepSeek/智谱等）
```
AI_MODE=api
AI_API_KEY=your-key
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-3.5-turbo
```

## 项目结构

```
科研助手平台/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI 入口、CORS、路由注册、启动建表+FTS重建
│   │   ├── config.py                 # Pydantic Settings
│   │   ├── database.py               # SQLAlchemy + SQLite
│   │   ├── search_index.py           # FTS5 索引：中文单字分词、增量/全量索引、检索
│   │   ├── models/                   # paper / note / experiment / task / chat
│   │   ├── routers/                  # papers / notes / experiments /
│   │   │                             #   experiment_groups / tasks / ai(SSE) / search(FTS5)
│   │   └── schemas/                  # Pydantic 请求/响应模型
│   ├── data/                         # SQLite 数据库文件
│   ├── uploads/                      # papers/ + experiments/ 附件
│   └── venv/                         # 仅 CRUD 用，无 torch
├── frontend/
│   ├── src/
│   │   ├── App.tsx, main.tsx         # 路由 / 渲染入口
│   │   ├── services/api.ts           # axios API 封装
│   │   ├── index.css                 # 全局样式（⚠️ 见踩坑 #9）
│   │   ├── layouts/MainLayout.tsx    # 固定侧边栏 + 全宽内容区
│   │   ├── components/MetricsChart.tsx  # 实验指标对比图（ECharts 柱/折线）
│   │   └── pages/                    # Papers / Notes / Experiments /
│   │                                 #   Tasks / AIChat / Search
│   ├── vite.config.ts                # API 代理
│   └── package.json
└── Qoder.md
```

## 数据库 Schema

| 表名 | 主要字段 | 说明 |
|------|---------|------|
| `papers` | title, authors, abstract, year, journal, doi, tags(JSON), file_path, fulltext, status, rating | 论文管理（fulltext=PDF 提取正文，仅供全文搜索，不返回前端） |
| `notes` | title, content(Markdown), folder, tags(JSON), paper_id(FK), is_pinned | 知识库笔记 |
| `experiments` | title, description, parameters(JSON), metrics(JSON), group_id(FK), run_number, variant, status | 实验运行记录 |
| `experiment_groups` | name, description, base_parameters(JSON), compare_metrics(JSON) | 实验分组（重复/消融对比） |
| `tasks` | title, description, status, priority, due_date, tags(JSON), sort_order | 任务管理 |
| `chat_messages` | session_id, role, content | AI 对话记录 |

## API 端点

前缀 `/api/v1`。各资源标准 RESTful CRUD（`GET`列表/详情、`POST`、`PUT`、`DELETE`），下列为非标准项：

- **论文** `/papers`：`POST /{id}/upload` 上传 PDF（自动提取正文进全文索引）；`POST /{id}/extract` 为已有 PDF 重新提取正文；`GET /{id}/fulltext` 取提取的正文；`POST /{id}/download-pdf`（body `{url}`，从直链下载 PDF 入库、关联、提取正文）；`GET /{id}/file` 内嵌/打开 PDF（`content_disposition_type="inline"`，供前端 iframe 阅读）；`GET /tags/all`；`POST /import`（DOI/arXiv 拉取元数据，含 `pdf_url`，不落库供填表）；`GET /export/bibtex?ids=` 导出 BibTeX；`POST /import-bibtex` 解析 .bib 批量建库
- **笔记** `/notes`：`GET /tags/all`；列表支持按文件夹/标签/关键词筛选
- **实验** `/experiments`：`POST /{id}/upload` 上传附件；列表支持 `group_id` 筛选
- **实验组** `/experiment-groups`：`GET /{id}`（含所有运行+对比统计）、`GET /{id}/compare`（表格对比+参数差异检测）、`POST /{id}/add-run`（自动编号、继承基准参数）
- **任务** `/tasks`：`GET /board` 看板视图（todo/in_progress/done）
- **全文搜索** `/search`：`GET ?q=&type=all|paper|note&limit=30` 跨论文+笔记全文检索，bm25 排序，返回标题+片段+元信息
- **AI** `/ai`：`POST /chat`（SSE 流式）、`GET /sessions`、`GET /sessions/{id}`、`DELETE /sessions/{id}`、`POST /model/load`、`GET /model/status`

## ⚠️ 踩坑记录

### 1. CORS 跨域 ⭐⭐⭐
`app/main.py` 配置 `CORSMiddleware` 须在路由注册前。`allow_origins=["*"]` 与 `allow_credentials=True` 不能同时用，须明确列出前端地址。

### 2. Vite 代理 ⭐⭐⭐
`vite.config.ts` 须设 `changeOrigin: true`，target 指向 `http://localhost:8000`，否则开发模式 API 404。

### 3. SQLite JSON 字段查询 ⭐⭐
SQLite 对 JSON 数组支持有限，无法直接 `LIKE`/`JSON_CONTAINS` 筛选 tags。当前在 Python 层做列表过滤；数据量大需切 PostgreSQL。

### 4. SSE 流式响应 ⭐⭐
- 后端：`media_type="text/event-stream"`，`headers={"Cache-Control": "no-cache"}`，每条 `data: {json}\n\n`。
- 前端：用 `fetch` + `ReadableStream`（POST 不能用 `EventSource`）。

### 5. Markdown XSS ⭐
渲染用户 Markdown 前先 `DOMPurify.sanitize()` 再交给 `ReactMarkdown`。

### 6. Pydantic 前向引用 ⭐⭐⭐
`List["OtherModel"]` 字符串前向引用易报 `PydanticUndefinedAnnotation`。把被引用模型定义在引用者之前，用直接引用而非字符串。

### 7. 表结构变更需删旧库 ⭐⭐
`create_all` 不修改已有表，只在表不存在时建。开发阶段改字段后删 `backend/data/research.db` 重建；生产须用 Alembic 迁移。

### 8. 本地 Qwen2.5 集成 ⭐⭐⭐
- **环境**：torch/transformers 在 `pytorch_nightly`，不在 `backend/venv`，启动后端必须用前者。
- **f-string 反斜杠**：Python < 3.12 中 f-string `{}` 内不能含 `\n`。先把 `json.dumps(...)` 赋给变量，`\n\n` 留在 `{}` 外。
- **懒加载**：`_local_stream_chat` 内用 `asyncio.to_thread(_load_local_model)`；加载失败用 try/finally reset `_model_loading` 标志，否则后续请求静默挂起。
- **transformers 5.x**：`from_pretrained` 用 `dtype=` 而非已弃用的 `torch_dtype=`。
- **验证**：改完用 `pytorch_nightly` 的 python `py_compile` 校验，再用 httpx 打 `/api/v1/ai/chat` 跑通流式（PowerShell 的 curl/Invoke-WebRequest 对 JSON 转义不可靠）。

### 9. CSS 旧模板样式污染布局 ⭐⭐⭐
Vite 初始 `index.css` 含 `#root { width: 1126px; margin: 0 auto; }`，会把内容区限宽居中。核心规则应为 `html, body, #root { height: 100%; width: 100%; }`，禁止任何宽度限制。注意 `App.css` 若未引用可删。

### 10. SQLite FTS5 中文全文检索 ⭐⭐⭐（见 `search_index.py`）
- **问题**：`unicode61` 把整段中文当一个 token（无法子串匹配）；`trigram` 要求查询≥3字符，2字常用词（「模型」「实验」）搜不到。
- **方案**：**单字分词 + unicode61**——入索引时每个汉字用空格切开；查询时把中文词转成相邻引号短语（如 `"模 型"`）做 MATCH，2字词也能命中。构造 MATCH 须剔除 FTS5 特殊字符 `"()*:^`。
- **索引维护**：启动时 `rebuild_all` 全量重建，运行时由 papers/notes 路由增删改调 `index_*/delete_*` 增量更新（中文分词须在 Python 层而非 SQL 触发器）。
- **排序**：`bm25()` 分值越小越相关，升序排。

### 11. ECharts 在 React 的生命周期 ⭐⭐（见 `MetricsChart.tsx`）
`echarts.init` 只做一次（ref 缓存实例）；数据变化时 `setOption(option, true)` 全量替换；卸载时 `dispose()`，并监听 window resize 调 `chart.resize()`。echarts 约 1MB+ 会触发打包体积告警，可忽略或改按需引入 `echarts/core`。

### 12. PDF 正文提取进全文搜索 ⭐⭐（见 `pdf_extract.py`）
- **依赖**：PyMuPDF（`import fitz`）只装在 `pytorch_nightly`，`backend/venv` 没有。`pdf_extract` 把 import 做成软依赖——缺库时 `extract_text` 返回空串而非抛错，venv 启动的纯 CRUD 不受影响（但提取功能失效）。
- **时机**：上传 PDF 时自动提取写入 `papers.fulltext` 并 `index_paper` 重建该论文索引；`POST /{id}/extract` 可对已有 PDF 手动重提（前端详情抽屉「提取正文」按钮）。
- **迁移**：`fulltext` 是新列，`create_all` 不会给旧表加列（踩坑 #7）。启动时 `_migrate_papers_fulltext` 用 `PRAGMA table_info` 检测并 `ALTER TABLE ADD COLUMN`，再 `_backfill_fulltext` 给已上传 PDF 但 fulltext 为空的论文回填——免去删库。
- **搜索**：`fulltext` 已并入 `_paper_index_text` 与 search 的 snippet 原文，正文里的术语能被命中并截出片段。单篇正文上限 50 万字符防止撑爆 FTS。

## 前端布局规范

- **侧边栏**：`Sider width={200}`，`position: fixed`，固定。
- **内容区**：`marginLeft: 200` + `display: flex` + `flexDirection: column`，占满剩余空间。
- **全局样式**：`html, body, #root { height: 100%; width: 100%; }`。
- **各页面**：根容器 `width: 100%` + `flex: 1`；含内部 Layout 的页面（Notes/Experiments/AIChat）用 `flex: 1, minHeight: 0, overflow: hidden`；表格文本字段不设固定 width，让列弹性分配。
- **内部 Sider 宽度**：Notes=180px，Experiments=240px，AIChat=220px。

## 后续开发建议

- **用户认证**：当前无登录，可加 JWT 保护 API。
- **论文 PDF 解析**：集成 PyMuPDF/pdfplumber 自动提取文本。
- **标签系统增强**：统一管理、跨模块共享。
- **数据导出**：笔记导 PDF、论文列表导 BibTeX。
- **拖拽看板**：任务看板拖拽排序。
- **数据库升级**：SQLite → PostgreSQL（生产必须）。
- **部署**：Dockerfile + docker-compose。

## 技术决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 后端 | FastAPI | 异步高性能、自动 API 文档、类型安全 |
| 数据库 | SQLite | 零配置单文件，适合个人；生产需切换 |
| 前端 | React + Vite | 生态丰富、构建快 |
| UI | Ant Design | 成熟、组件丰富、中文文档完善 |
| AI | OpenAI 兼容格式 | 通用，可接 DeepSeek/智谱/本地模型 |
| 文件存储 | 本地文件系统 | 简单，后续可迁对象存储 |
