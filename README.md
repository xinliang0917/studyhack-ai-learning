# AI 智能学习辅助系统

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/xinliang0917/studyhack-ai-learning)

基于 FastAPI + Vue.js 的智能学习辅助平台，集成知识库管理、混合检索 RAG、课程大纲生成、AI 测验出题、错题复习、学习计划、人脸识别登录与语音控制。

> 天池大赛 · StudyHack 学习科研赛道参赛项目

## 赛道对应

| 赛题方向 | 本项目能力 |
|------|------|
| 课件与知识库 | 多格式课件上传、解析、分块与 faiss 向量索引 |
| RAG 问答 | BM25 + 向量混合检索、RRF 融合、流式回答、引用可跳转原文 |
| 学习场景 Agent | 自动生成课程大纲、章节内容、分层练习题与错题解析 |
| 课表与作业管理 | 学习计划/作业/考试截止管理、从大纲自动生成计划、SM-2 复习 |
| 科研/学习 Copilot | DeepSeek / Ollama 驱动的讲解、出题、原文溯源与语音导航 |

## 功能概述

| 模块 | 功能 |
|------|------|
| 知识库管理 | 上传 PDF/DOCX/PPTX/TXT/MD 文档，自动解析、分块并构建向量索引 |
| AI 问答 | BM25 + 向量混合检索、RRF 融合、SSE 流式回答、Markdown/公式渲染、引用跳原文 |
| 学习计划 | 课程/作业/考试任务管理、截止时间/优先级/逾期统计、从大纲自动生成计划 |
| 课程大纲 | AI 根据知识库内容自动生成结构化课程大纲与章节内容 |
| 在线测验 | 基于知识库自动生成选择题/判断题，支持难度筛选、自动评分、错题本 |
| 错题复习 | 错题记录关联原文分块、SM-2 间隔复习、AI 基于原文生成错题解析 |
| 人脸登录 | MediaPipe 关键点特征 + OpenCV LBPH 本地人脸识别，支持中文路径 |
| 语音控制 | 语音指令识别，支持导航到各功能页面 |
| 考试历史 | 查看历史考试记录、成绩趋势、错题分布统计 |

## 技术栈

**后端**
- FastAPI (Python 3.12)
- SQLAlchemy 2.0 + SQLite / MySQL
- DeepSeek / Ollama（OpenAI 兼容，可切换本地模型）
- BGE 中文 embedding + faiss 向量检索（可关闭）
- BM25 + RRF 混合检索，可选 CrossEncoder 重排
- OpenCV + MediaPipe (人脸识别)
- bcrypt + JWT (用户认证)

**前端**
- Vue 3 + Element Plus
- Pinia (状态管理)
- Vue Router
- Axios (HTTP 请求)
- Vite (构建工具)

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── config.py             # 配置管理
│   │   ├── database.py           # 数据库初始化
│   │   ├── models/               # SQLAlchemy 模型
│   │   │   ├── user.py           # 用户模型
│   │   │   ├── knowledge.py      # 知识库文档/分块模型
│   │   │   ├── course.py         # 课程大纲/章节/进度模型
│   │   │   ├── quiz.py           # 测验/考试/错题模型
│   │   │   ├── face.py           # 人脸编码模型
│   │   │   └── schedule.py       # 学习计划/作业模型
│   │   ├── schemas/              # Pydantic 数据模式
│   │   ├── routers/              # API 路由
│   │   │   ├── auth.py           # 注册/登录/人脸认证
│   │   │   ├── knowledge.py      # 文档上传/管理
│   │   │   ├── course.py         # 大纲生成/章节/进度
│   │   │   ├── quiz.py           # 测验生成/提交/评分
│   │   │   ├── rag.py            # 知识库 RAG 问答
│   │   │   ├── schedule.py       # 学习计划/作业管理
│   │   │   └── voice.py          # 语音指令解析
│   │   ├── services/             # 核心服务层
│   │   │   ├── document_parser.py # 文档解析 (PDF/DOCX/PPTX/TXT/MD)
│   │   │   ├── quiz_engine.py    # 出题引擎与评分
│   │   │   ├── llm_service.py    # DeepSeek LLM 调用
│   │   │   ├── vector_store.py   # faiss 向量检索
│   │   │   └── face_service.py   # 人脸特征提取与比对
│   │   └── utils/
│   │       └── auth.py           # JWT 令牌验证依赖
│   ├── tests/                    # 自动化测试
│   ├── face_landmarker.task      # MediaPipe 人脸关键点模型
│   ├── requirements.txt          # 完整依赖（含向量模型）
│   ├── requirements-deploy.txt   # 部署精简依赖（BM25 模式）
│   └── requirements-test.txt     # CI 测试依赖
├── frontend/
│   ├── src/
│   │   ├── views/                # 页面组件
│   │   ├── components/           # 通用组件
│   │   ├── api/                  # API 封装
│   │   ├── router/               # 路由配置
│   │   ├── store/                # Pinia 状态管理
│   │   └── composables/          # 组合式函数
│   └── package.json
├── Dockerfile                    # 前后端一体镜像
├── render.yaml                   # Render 一键部署
├── .dockerignore
├── .gitignore
├── .env.example
├── start-dev.ps1                 # 一键启动前后端（Windows）
└── README.md
```

## 快速开始

### 前置条件

- Python 3.10+
- Node.js 18+
- DeepSeek API Key

### 1. 克隆项目

```bash
git clone https://github.com/xinliang0917/studyhack-ai-learning.git
cd studyhack-ai-learning
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy ..\.env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

可选配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EMBEDDING_ENABLED` | `true` | 设为 `false` 跳过向量模型，仅用 BM25（低配/免费部署） |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 中文资料推荐；也可用多语言模型 |
| `RETRIEVAL_MODE` | `hybrid` | `hybrid` / `vector` / `bm25` |
| `RERANK_ENABLED` | `false` | 开启 CrossEncoder 重排，首次加载较慢 |
| `RAG_MAX_DISTANCE` | `1.6` | 过滤过远检索片段；设为 `0` 关闭绝对距离阈值 |
| `LLM_PROVIDER` | `deepseek` | 设为 `ollama` 使用本地模型 |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama OpenAI 兼容地址 |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama 模型名 |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8000` | 逗号分隔 |
| `MAX_UPLOAD_MB` | `50` | 上传大小限制 |
| `FACE_IMAGES_DIR` | `backend/face_images` | 人脸样本目录，已支持中文路径 |

### 3. 启动后端

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档访问 http://localhost:8000/docs

### 4. 前端构建

```bash
cd frontend
npm install
npm run build      # 构建生产版本
npm run dev        # 或启动开发服务器
```

### 5. 访问系统

浏览器打开 http://localhost:8000 (前后端一体部署) 或 http://localhost:5173 (前端开发服务器)

完成依赖安装与 `.env` 配置后，也可以在项目根目录运行 `.\start-dev.ps1`，一键启动后端与前端开发服务器。

## API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/auth/register/password` | POST | 密码注册 |
| `/api/auth/login/password` | POST | 密码登录 |
| `/api/auth/register/face` | POST | 人脸注册 |
| `/api/auth/login/face` | POST | 人脸登录 |
| `/api/knowledge/upload` | POST | 上传文档 |
| `/api/knowledge/documents` | GET | 文档列表 |
| `/api/knowledge/documents/{id}` | DELETE | 删除文档 |
| `/api/knowledge/documents/{id}/content` | GET | 文档内容 |
| `/api/knowledge/documents/{id}/chunks/{chunk_index}` | GET | 读取指定分块（引用溯源） |
| `/api/knowledge/search` | GET | 知识库混合检索 |
| `/api/knowledge/refresh` | POST | 刷新索引 |
| `/api/course/outline/generate` | POST | 生成大纲 |
| `/api/course/outline` | GET | 大纲列表 |
| `/api/course/chapters/{outline_id}` | GET | 章节列表 |
| `/api/course/progress` | GET/PUT | 学习进度 |
| `/api/course/progress/reset` | POST | 重置进度 |
| `/api/quiz/generate-by-course` | POST | 按课程出题 |
| `/api/quiz/generate` | POST | 按章节出题 |
| `/api/quiz/{exam_id}/submit` | POST | 提交答卷 |
| `/api/quiz/{exam_id}/questions` | GET | 考试题目 |
| `/api/quiz/history` | GET | 考试历史 |
| `/api/quiz/progress/stats` | GET | 学习统计 |
| `/api/quiz/wrong-questions` | GET | 错题本 |
| `/api/quiz/wrong-questions/review` | GET | 到期复习队列（SM-2） |
| `/api/quiz/wrong-questions/{id}/review` | POST | 提交复习评价并更新下次复习时间 |
| `/api/quiz/wrong-questions/{id}/explain` | POST | 基于知识库生成错题解析 |
| `/api/rag/chat` | POST | 知识库 RAG 问答（多轮对话 + 引用来源） |
| `/api/rag/chat/stream` | POST | RAG 流式问答（SSE） |
| `/api/schedule/items` | GET/POST | 学习计划列表/新建任务 |
| `/api/schedule/items/{id}` | PUT/DELETE | 编辑/删除任务 |
| `/api/schedule/items/{id}/toggle` | PATCH | 切换完成状态 |
| `/api/schedule/auto-plan` | POST | 从课程大纲自动生成学习计划 |
| `/api/schedule/stats` | GET | 任务统计与近 7 天待办 |
| `/api/voice/interpret` | POST | 语音指令解析 |

## 测试

项目包含 88 个自动化测试用例，当前全部通过。

```bash
cd backend
pytest tests/ -v
```

详见 [测试总结报告](测试总结报告.md)

## 部署

### Render 一键部署（推荐）

仓库包含 `render.yaml` 和 `Dockerfile`：

1. 在 Render 新建 Blueprint，选择本仓库；
2. 按提示填写 `DEEPSEEK_API_KEY`；
3. 部署完成后访问 `https://<service>.onrender.com`。

免费实例默认使用 `BM25 + SQLite`（`EMBEDDING_ENABLED=false`），不加载向量模型，内存占用低。注意免费实例重启后本地 SQLite 数据会重置，演示前重新上传资料即可。

### Docker 部署

```bash
docker build -t studyhack-ai-learning .
docker run -p 8000:8000 \
  -e DEEPSEEK_API_KEY=your-key \
  -e JWT_SECRET=change-me \
  -e EMBEDDING_ENABLED=false \
  -e RETRIEVAL_MODE=bm25 \
  studyhack-ai-learning
```

浏览器打开 http://localhost:8000。生产环境建议挂载 `/app/backend/uploads`、`/app/backend/vector_index` 和 SQLite 文件。

### 传统 Linux 部署

```bash
cd backend
pip install -r requirements.txt
cd ../frontend && npm install && npm run build
cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 许可证

MIT
