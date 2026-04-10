# IELTS Vocabulary

一个面向 IELTS 词汇学习的全栈 Web 应用，包含词书学习、多练习模式、AI 助手、学习日志、每日总结、学习画像，以及独立语音识别服务。

## 当前能力

- 词书学习：支持词书、章节、单词详情、收藏/熟词/易混词等学习入口。
- 多练习模式：支持 `smart`、`listening`、`meaning`、`dictation`、`radio`、`quickmemory`、`errors`。
- 学习统计与画像：提供学习记录、模式占比、错词 Top10、艾宾浩斯复习达成和统一学习画像。
- AI 助手：支持带上下文的问答、学习建议、错词分析、总结辅助和用户记忆注入。
- 日志与总结：支持学习日志、主题聚合、每日总结和相关导出能力。
- 语音能力：HTTP API 与实时语音识别拆分为独立进程，支持 Socket.IO 语音链路。
- 管理与运维：支持管理员能力、TTS 生成、启动脚本、生产式本地代理链路和提交日志归档。

## 技术栈

- 前端：React 19 + TypeScript + Vite
- 样式：SCSS + CSS Variables
- 校验：Zod
- 后端：Flask + SQLite + Waitress
- 实时：Flask-SocketIO + Socket.IO
- 鉴权：JWT + localStorage
- 语音：独立 `speech_service.py` + DashScope 相关适配

## 仓库结构

```text
frontend/
- package.json              # 前端包清单
- vite.config.ts            # dev / preview / proxy 端口配置
- src/
  - app/                    # 路由入口
  - components/             # 页面与 UI 组件
  - composables/            # 页面级组合逻辑
  - contexts/               # Auth / Settings / Toast / AIChat
  - features/               # 领域功能
  - hooks/                  # 共享 hooks
  - lib/                    # schema、工具与本地同步逻辑
  - styles/                 # 页面样式
  - tests/                  # 单元与集成测试

backend/
- app.py                    # 主 API 入口，默认端口 5000
- speech_service.py         # 独立语音服务入口，默认端口 5001
- models.py                 # 数据模型
- routes/                   # HTTP / Socket.IO 路由层
- services/                 # 服务层、仓储层、提供方适配层
- tests/                    # 后端测试
- README.md                 # 后端架构与层次说明
- API.md                    # API 索引

docs/
- architecture/             # 架构说明与设计文档
- governance/               # UI / 产品治理记录
- milestones/               # 里程碑文档
- operations/               # 运维与工具文档
- planning/                 # 计划文档
- logs/submit/              # 提交批次日志

scripts/                    # 守卫脚本与仓库工具
vocabulary_data/            # 词书与词汇数据
AGENTS.md                   # 仓库级工作约束
MILESTONE.md                # 里程碑总览
TODO.md                     # 当前任务清单
start-project.bat           # Windows 一键启动入口
start-project.ps1           # 本地生产式启动脚本
```

## 运行拓扑

当前本地运行默认分成四个关键端口：

- 前端开发：`http://127.0.0.1:3020`
- 前端预览：`http://127.0.0.1:3002`
- 后端 API：`http://127.0.0.1:5000`
- 语音服务：`http://127.0.0.1:5001`

生产式本地代理链路：

```text
https://axiomaticworld.com
-> natapp
-> local :80
-> nginx
-> vite preview :3002
-> /api -> backend app :5000
-> /socket.io -> speech service :5001
```

如果遇到域名访问异常、`ERR_SSL_PROTOCOL_ERROR`、Socket.IO 失败或 `/api` 表现与本地开发不一致，优先检查这条整链路，而不是只看前端页面代码。

## 快速开始

### 1. 安装依赖

前端依赖：

```bash
pnpm install
```

后端依赖：

```bash
cd backend
pip install -r requirements.txt
```

### 2. 一键启动

Windows 下优先使用：

```bash
start-project.bat
```

或者直接运行：

```bash
powershell -ExecutionPolicy Bypass -File .\start-project.ps1
```

这个脚本会按当前约定启动：

- backend API
- speech service
- Vite preview
- 与本地代理链路配套的日志与健康检查

### 3. 手动启动

后端 API：

```bash
cd backend
python app.py
```

独立语音服务：

```bash
cd backend
python speech_service.py
```

前端开发：

```bash
pnpm dev
```

前端预览：

```bash
pnpm preview
```

## 常用命令

根目录 workspace 命令：

```bash
pnpm dev
pnpm build
pnpm preview
pnpm lint
pnpm test
pnpm test:e2e
pnpm check:file-lines
pnpm verify:repo-guards
```

后端常用命令：

```bash
pytest -q
pytest backend/tests/test_source_text_integrity.py -q
```

## 质量守卫

提交前至少建议通过：

```bash
pnpm check:file-lines
pnpm lint
pnpm build
pnpm test
pytest backend/tests/test_source_text_integrity.py -q
```

说明：

- `pnpm build` 会自动触发前端仓库守卫。
- `check-file-lines` 会拦截新的超长手工维护文件。
- `test_source_text_integrity.py` 用于发现文本编码异常和常见乱码。

## 主要接口

- `/api/auth`：注册、登录、登出、当前用户、邮箱绑定与恢复
- `/api/books`：词书、章节、单词详情、进度、熟词/收藏/易混词
- `/api/ai`：AI 助手、学习统计、学习画像、错词、练习支撑、速记同步
- `/api/notes`：学习日志、总结、任务与导出
- `/api/tts`：单词/句子音频与批量生成状态
- `/api/admin`：管理员能力
- `/socket.io`：独立 speech service 的实时语音链路

## 参考文档

- 仓库工作约束：[AGENTS.md](./AGENTS.md)
- 后端总览：[backend/README.md](./backend/README.md)
- 后端架构：[docs/architecture/backend-layered-architecture.md](./docs/architecture/backend-layered-architecture.md)
- API 索引：[backend/API.md](./backend/API.md)
- 文档目录说明：[docs/README.md](./docs/README.md)

## License

MIT
