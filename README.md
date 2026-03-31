# IELTS Vocabulary

一个面向 IELTS 词汇学习的 Web 应用，包含词书学习、练习模式、AI 助手、学习日志、每日总结和学习画像。

## 当前能力

- 词书与章节学习：支持按词书、章节浏览和进入学习。
- 多练习模式：`smart`、`listening`、`meaning`、`dictation`、`radio`、`quick memory`、`errors`。
- 进度与错词追踪：记录章节进度、正确率、错词和模式表现。
- AI 助手：支持上下文问答、Markdown 渲染、历史记忆注入、画像驱动问候。
- 学习日志与每日总结：支持问答历史查看、主题聚合、每日总结导出。
- 统一学习画像：把练习表现、错词、重复困惑主题和后续建议汇总给 AI 与总结页使用。
- 管理与运维能力：包含管理员接口、TTS 生成、后端 WAL 模式与迁移支持。

## 技术栈

- 前端：React 19 + TypeScript + Vite
- 样式：SCSS + CSS Variables
- 校验：Zod
- 后端：Flask + SQLite + Flask-SocketIO
- 鉴权：JWT + localStorage
- 实时能力：Socket.IO / WebSocket

## 目录概览

```text
src/
- app/                      # 路由入口
- components/               # 页面与通用组件
- contexts/                 # Auth / Settings / Toast / AIChat
- features/                 # 领域功能
- hooks/                    # 共享 hooks
- lib/                      # schema、工具、markdown 渲染等
- styles/                   # 页面样式

backend/
- app.py                    # Flask 入口
- models.py                 # 数据模型
- routes/                   # 各类 API 路由
- services/                 # 后端服务逻辑
- tests/                    # 后端测试

docs/                       # 设计、计划、审计文档
vocabulary_data/            # 词书与词汇数据
```

## 本地开发

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端默认运行在 `http://localhost:5000`。

### 2. 启动前端

```bash
npm install
npm run dev
```

前端开发服务器默认运行在 `http://127.0.0.1:3002`。

常用前端命令：

```bash
npm run build
npm run preview
npm test
```

## 本地代理链路

这个项目默认按生产式代理链路调试：

1. Vite 开发服务器：`http://127.0.0.1:3002`
2. 本地 `nginx`：监听 `80`，转发到 `3002`
3. `natapp`：把 `https://axiomaticworld.com` 转发到本地 `80`

也就是：

```text
https://axiomaticworld.com
-> natapp
-> local :80
-> nginx
-> local :3002
```

如果出现 `ERR_SSL_PROTOCOL_ERROR`、`/api/...` 异常或前后端跨域表现不一致，先检查这条代理链路，而不是只看前端代码。

## 主要接口

- `/api/auth`：登录、注册、登出、用户信息、头像
- `/api/books`：词书、章节、词汇、进度
- `/api/ai`：AI 助手、学习画像、学习统计、错词、练习相关接口
- `/api/notes`：问答历史、每日总结、导出
- `/api/tts`：TTS 音频与生成状态
- `/api/admin`：管理员能力

## 质量检查

推荐至少执行以下检查：

```bash
npm test
npm run build
pytest backend/tests/test_source_text_integrity.py -q
```

`test_source_text_integrity.py` 会扫描仓库里的 `py/ts/tsx/scss/md/json/yml/yaml/toml`，拦截常见乱码和编码异常文本。

## 备注

- SQLite 连接默认启用 WAL 模式，提升并发读写表现。
- 数据库迁移使用 Flask-Migrate，详细说明见 [backend/AGENTS.md](backend/AGENTS.md)。
- 仓库编辑策略、编码和补丁命中策略见 [AGENTS.md](AGENTS.md)。

## License

MIT
