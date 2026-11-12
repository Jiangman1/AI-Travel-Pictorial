# AI-Travel-Pictorial

> 旅行图文自动营销 MVP —— 输入一个地点，自动完成「文案生成 → 配图 → 内容校验 → HTML 预览 → 人工审核 → 头条发布」的完整链路。

个人实战项目，本地运行，未做公网部署。

---

## 它解决什么问题

内容运营里有一类高度重复的工作：给定一个旅游目的地，写一篇图文，配上合适的图片，检查合规性，然后发到平台上。流程固定、判断标准固定，但每一步都要人来做。

这个项目用 **LangGraph 把这条流程编排成状态机**：一个地点关键词进去，一条可发布的图文出来，中间在需要人拍板的地方停下来等审核。同时提供 **FastAPI 服务**和 **MCP 工具协议**两种接入方式，前者给前端页面用，后者给对话式 Agent 用。

## 工作流

```
输入地点
   │
   ▼
文案生成 ──► 配图 ──► 校验 ──► HTML 预览 ──► 人工审核(可选) ──► 头条发布
 (LLM)      (AI/爬虫)  (校验)   (模板渲染)      (interrupt)     (Playwright)
              ▲            │
              └──── 不通过 ┘
```

- 7 个节点、4 处条件路由、1 个人工中断点
- checkpoint 落 SQLite，按 `thread_id` 隔离，支持暂停后恢复
- 配图有两条通道：AI 生图（阿里云百炼）和百度图片下载，通过 `IMAGE_SOURCE` 一行配置切换

## 技术栈

| 层 | 技术 |
|---|---|
| 编排 | LangGraph 1.x（`StateGraph` / `interrupt` / `Command(resume)`） |
| 模型 | LangChain + `langchain-openai`（OpenAI 兼容协议，当前接 DeepSeek） |
| 结构化输出 | Pydantic + `JsonOutputParser` |
| 生图 | 阿里云百炼 DashScope `MultiModalConversation` |
| 爬虫 | `requests` + 百度图片 acjson 接口 |
| 自动发布 | Playwright（Chromium，`storage_state` 复用登录态） |
| 服务 | FastAPI + Uvicorn |
| 前端 | React 18 UMD + Babel Standalone（无构建步骤） |
| 管理页 | Streamlit |
| 工具协议 | MCP（`FastMCP` + `langchain-mcp-adapters`） |

## 目录结构

```
__001__workflow/     LangGraph 状态机：状态定义、节点、路由、checkpoint
__002__fastapi/      FastAPI 服务 + React 前端页面
__003__streamlit/    Streamlit 管理页
__004__mcp/          MCP Server / Client
common/              配置、LLM 封装、百度图片工具、路径与产物工具
docs/                技术文档、难点与解决方案
```

## 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env       # 然后填入 API Key

# 2. Windows 一键启动（自动建 venv、装依赖、装 Chromium、起服务）
powershell -ExecutionPolicy Bypass -File .\start.ps1

# 或手动
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python -m __002__fastapi.__001__server
```

默认服务地址：`http://127.0.0.1:8000`

环境变量说明见 `.env.example`。**真实密钥只放在本地 `.env`，不入库。**

## 设计取舍

- **MCP 链路不经过 LangGraph**：它直接调用业务函数，是给对话式调用方准备的独立入口，避免把多轮编排逻辑耦合进工具层。
- **配图双通道**：生图质量高但不稳定、有配额；爬虫快但图片可控性差。做成配置项而不是硬编码，切换成本降到一行。
- **人工审核做成可选中断点**：默认关闭以便调试，发布前打开，`interrupt` + `Command(resume)` 实现暂停和恢复。
- **前端零构建**：React 18 UMD + Babel Standalone，省掉 Node 工具链，便于单机演示。

更细的实现细节、接口定义、排错速查见 [`docs/技术文档.md`](docs/技术文档.md)。

## 已知限制

- 未做公网部署，无鉴权、无限流，仅限本地使用
- 头条发布依赖 Playwright 复用登录态，平台改版可能导致失效
- 百度图片接口非官方，稳定性不受控
- 单机单进程，未做并发与任务队列

## 免责声明

本项目仅用于个人技术学习与实践，自动化发布功能请遵守目标平台的服务条款；请勿用于批量刷量、内容农场等用途。
