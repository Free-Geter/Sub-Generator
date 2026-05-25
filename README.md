# Sub-Generator — 视频字幕自动生成工具

基于 Whisper + Ollama/DeepL/OpenAI 的视频字幕自动生成系统，支持语音识别、多引擎翻译、SRT 字幕输出。

## 功能特性

- **语音识别** — 基于 faster-whisper，支持 tiny ~ large-v2 多级模型，GPU/CPU 自适应
- **多翻译引擎** — 支持 Ollama（本地）、DeepL、OpenAI 三种翻译引擎自由切换
- **自定义翻译 Prompt** — 支持用户自定义翻译提示词，可覆盖内置默认
- **批量翻译** — 多行合并批量提交，保留上下文连贯性，GPU 利用率高
- **任务重新翻译** — 已完成的任务可更换引擎/模型重新翻译，无需重复语音识别
- **实时进度** — 4 阶段流水线（音频提取 → 语音识别 → 翻译 → SRT 生成），WebSocket 实时推送
- **SRT 导出** — 生成标准 SRT 字幕文件，支持原文/译文双语模式

## 技术栈

| 层 | 技术 |
|---|------|
| 后端框架 | FastAPI + Uvicorn |
| 数据库 | SQLite (aiosqlite + SQLAlchemy async) |
| 语音识别 | faster-whisper (CTranslate2 + CUDA) |
| 音频处理 | FFmpeg (ffmpeg-python) |
| 翻译引擎 | Ollama / DeepL API / OpenAI API |
| 实时通信 | WebSocket |
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 打包 | PyInstaller (单 exe 部署) |

## 项目结构

```
Sub-Generator/
├── backend/
│   ├── app/
│   │   ├── api/              # REST API 路由
│   │   │   ├── history.py    # 历史记录、批删、重新翻译
│   │   │   ├── settings.py   # 全局配置读写
│   │   │   ├── tasks.py      # 任务创建/查询/取消/重跑
│   │   │   └── videos.py     # 视频目录扫描、预览
│   │   ├── pipeline/         # 字幕生成流水线
│   │   │   ├── orchestrator.py    # 流水线编排（全流程 + retranslate）
│   │   │   ├── audio_extractor.py # FFmpeg 音频分片提取
│   │   │   ├── speech_recognizer.py # faster-whisper 语音识别
│   │   │   ├── translator.py      # 多引擎翻译（含批量+重试）
│   │   │   └── srt_generator.py   # SRT 文件生成
│   │   ├── services/         # 公共服务
│   │   │   ├── ollama_client.py   # Ollama HTTP 客户端
│   │   │   ├── progress.py        # WebSocket 进度广播
│   │   │   └── temp_manager.py    # 临时文件管理
│   │   ├── ws/               # WebSocket 路由
│   │   ├── config.py         # 全局配置（pydantic-settings）
│   │   ├── database.py       # 数据库连接管理
│   │   ├── main.py           # FastAPI 应用入口 + SPA 静态服务
│   │   └── models.py         # ORM 模型 + Pydantic Schema
│   ├── requirements.txt
│   └── venv/                 # 虚拟环境（不提交）
├── frontend/
│   ├── src/
│   │   ├── api/index.js      # Axios API 封装
│   │   ├── components/       # 公共组件（TaskCard、ProgressBar、SubtitlePreview）
│   │   ├── views/            # 页面（Home、History、Progress、Settings）
│   │   ├── router/           # Vue Router 路由
│   │   ├── store/            # Pinia 状态管理
│   │   ├── utils/            # WebSocket 工具
│   │   ├── App.vue
│   │   └── main.js
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── data/
│   ├── settings.json         # 用户配置持久化
│   └── outputs/              # SRT 输出目录
├── start.bat                 # Windows 一键启动脚本
└── README.md
```

## 环境要求

- **Python** 3.11+
- **Node.js** 18+（前端构建）
- **FFmpeg**（需在 PATH 中，音频提取依赖）
- **CUDA**（可选，GPU 加速语音识别，推荐 RTX 3060+）
- **Ollama**（可选，使用本地模型翻译时需要）

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone <repo-url>
cd Sub-Generator

# 后端
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

# 前端
cd ../frontend
npm install
```

### 2. 构建前端

```bash
cd frontend
npm run build       # 产物输出到 frontend/dist/
```

### 3. 启动后端

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

打开浏览器访问 **http://localhost:8000**

> Windows 用户可直接双击项目根目录的 **`start.bat`** 一键启动。

### 4. 配置

启动后在设置页面（⚙ 图标）配置：

| 配置项 | 说明 |
|--------|------|
| 视频源目录 | 存放待处理视频的文件夹路径 |
| 翻译引擎 | Ollama / DeepL / OpenAI |
| Whisper 模型 | tiny ~ large-v2，越大精度越高但越慢 |
| 翻译 Prompt | 自定义翻译提示词，支持 `{target_lang}` 占位符 |

配置自动持久化到 `data/settings.json`，重启后保留。

## 使用流程

1. **设置视频源目录** — 在设置中指定视频文件夹路径
2. **提交任务** — 首页选择视频，选择目标语言和翻译引擎，点击开始
3. **查看进度** — 实时 4 阶段进度条，支持 WebSocket 推送
4. **下载 SRT** — 完成后可下载字幕文件
5. **重新翻译**（可选） — 对不满意结果可更换引擎/模型重新翻译，无需重复语音识别

## 流水线阶段

```
extracting (5-30%)   →  FFmpeg 分片提取音频
recognizing (30-62%)  →  faster-whisper 逐片语音识别
translating (62-90%)  →  翻译引擎批量翻译
generating (92-100%)  →  生成 SRT 字幕文件
```

## 配置参考

所有配置项可通过系统设置页面修改，或设置环境变量：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `SUBTITLE_HOST` | `0.0.0.0` | 监听地址 |
| `SUBTITLE_PORT` | `8000` | 监听端口 |
| `SUBTITLE_DATA_DIR` | `./data` | 数据存储目录 |
| `SUBTITLE_TRANSLATION_ENGINE` | `ollama` | 默认翻译引擎 |
| `SUBTITLE_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `SUBTITLE_OLLAMA_MODEL` | `qwen2.5:14b` | Ollama 默认模型 |
| `SUBTITLE_WHISPER_MODEL` | `medium` | Whisper 模型大小 |
| `SUBTITLE_CHUNK_DURATION` | `600` | 音频分片时长（秒） |

## 打包部署

```bash
# 构建前端
cd frontend && npm run build

# 打包为单文件 .exe（不含 CUDA 依赖约 2.3GB）
cd ../backend
pyinstaller SubGenerator.spec
```

产物在 `backend/dist/SubGenerator.exe`，双击启动，浏览器访问 `http://localhost:8000`。

## API 端点

### 视频

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/videos/list` | 扫描视频源目录，返回视频文件列表 |
| GET | `/api/videos/preview?path=...` | 预览视频文件（206 Range 流式传输） |

### 任务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks` | 创建新任务，触发流水线 |
| GET | `/api/tasks` | 查询所有任务列表 |
| GET | `/api/tasks/{task_id}` | 查询单个任务详情 + 字幕分段 |
| POST | `/api/tasks/{task_id}/cancel` | 取消正在执行的任务 |
| POST | `/api/tasks/{task_id}/retranslate` | 重新翻译（无需重复语音识别） |
| POST | `/api/tasks/{task_id}/rerun` | 完全重新执行流水线 |

### 历史记录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/history` | 分页查询历史任务 |
| DELETE | `/api/history` | 批量删除已完成/失败任务 |
| DELETE | `/api/history/{task_id}` | 删除单个任务 |

### 设置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 获取当前全局配置 |
| PUT | `/api/settings` | 更新全局配置并持久化 |

### WebSocket

| 路径 | 说明 |
|------|------|
| `/ws/progress/{task_id}` | 实时进度推送（step + progress + message） |

## WebSocket 消息格式

```json
{
  "task_id": "uuid",
  "step": "translating",
  "progress": 75.5,
  "message": "翻译: 75%"
}
```

`step` 枚举值：`extracting` | `recognizing` | `translating` | `generating` | `done` | `failed`

## 数据库 Schema

### tasks 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT (UUID) | 任务主键 |
| video_path | TEXT | 视频文件路径 |
| video_name | TEXT | 视频文件名 |
| status | TEXT | pending / extracting / recognizing / translating / generating / done / failed / cancelled |
| progress | REAL | 0-100 |
| source_lang | TEXT | 自动检测的源语言 |
| target_lang | TEXT | 目标语言（zh/en/ja 等） |
| translation_engine | TEXT | ollama / deepl / openai |
| whisper_model | TEXT | tiny ~ large-v2 |
| output_file | TEXT | 生成的 SRT 文件路径 |
| error_message | TEXT | 失败原因 |
| created_at | DATETIME | 创建时间（UTC） |
| updated_at | DATETIME | 最后更新时间（UTC） |

### segments 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT (UUID) | 分段主键 |
| task_id | TEXT (FK) | 关联任务 |
| start_time | REAL | 起始时间（秒） |
| end_time | REAL | 结束时间（秒） |
| source_text | TEXT | Whisper 识别的原文 |
| translated_text | TEXT | 翻译后的文本 |

## 翻译引擎对比

| 特性 | Ollama | DeepL | OpenAI |
|------|--------|-------|--------|
| 网络 | 无需联网 | 需要 API | 需要 API |
| 费用 | 免费 | 按字符计费 | 按 Token 计费 |
| 质量 | 取决于本地模型 | 优秀 | 优秀 |
| 速度 | 取决于 GPU VRAM | 快 | 快 |
| 推荐模型 | qwen2.5:14b / 32b | — | gpt-4o-mini |

## 故障排除

### FFmpeg 找不到

确保 FFmpeg 在系统 PATH 中，或修改 `start.bat` 中的 `FFMPEG_BIN` 路径。

验证：`ffmpeg -version`

### Ollama 连接失败

```bash
# 确认 Ollama 正在运行
ollama serve

# 检查是否拉取了模型
ollama list

# 拉取推荐模型
ollama pull qwen2.5:14b
```

### CUDA / GPU 不可用

确保安装了 NVIDIA CUDA Toolkit 和 cuBLAS。检查：

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

如返回 `False`，Whisper 将回退到 CPU 模式，速度会显著降低。

### 前端页面空白

1. 确保已构建前端：`cd frontend && npm run build`
2. 强制刷新浏览器：`Ctrl+F5`

### 端口被占用

```bash
# 查看 8000 端口占用
netstat -ano | findstr :8000

# 杀死占用进程
taskkill /PID <PID> /F
```

## License

MIT
