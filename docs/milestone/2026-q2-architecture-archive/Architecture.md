# 雅思词汇 (IELTS Vocab) 系统架构

版本: v1.0 | 更新: 2026-05-14 | 架构阶段: Wave 5 后稳定期

## 概述

IELTS Vocab 是一个雅思词汇学习全栈应用，采用 **pnpm + Python 混合 Monorepo**。后端正在从 Flask 单体架构向微服务架构迁移（Strangler Fig 模式），当前处于 Wave 5 后稳定期。

生产部署于腾讯云 CVM，通过 Nginx 反向代理对外提供 `https://axiomaticworld.com`。

---

## 一、Monorepo 结构

```
ielts-vocab/
├── frontend/                    # React 19 Web 前端 (pnpm workspace)
│   ├── src/
│   │   ├── app/                 # 路由、Shell、路由守卫、Provider
│   │   ├── components/          # 18 个领域组件目录
│   │   ├── composables/         # 页面级组合逻辑 hooks
│   │   ├── contexts/            # Auth / Settings / Toast / AIChat
│   │   ├── features/            # 跨路由领域服务
│   │   ├── hooks/               # 共享 hooks
│   │   ├── lib/                 # apiClient / schemas / 工具函数
│   │   ├── styles/              # SCSS + CSS 设计令牌 (127 文件)
│   │   └── types/               # TypeScript 类型
│   └── tests/e2e/               # Playwright E2E 测试 (15 文件)
│
├── apps/
│   ├── gateway-bff/             # 浏览器 API 网关 (FastAPI, 端口 8000)
│   └── mobile/                  # React Native 移动端 (Android + iOS)
│
├── packages/
│   ├── app-core/                # 共享 TS 库: API Client / Auth / Schema / 存储
│   ├── platform-sdk/            # 共享 Python 平台 SDK (~120+ 模块)
│   └── mac-bridge-mcp/          # MCP 服务 (管理本地开发运行时)
│
├── backend/                     # 遗留 Flask 单体 + 共享业务逻辑
│   ├── app.py                   # 兼容单体 API (:5000)
│   ├── speech_service.py        # 兼容语音 Socket.IO (:5001)
│   ├── config.py                # 全局 Flask 配置
│   ├── models.py                # 模型加载器 (加载 15 个模型定义文件)
│   ├── model_definitions/       # 共享表定义 (15 文件)
│   ├── service_models/          # 各服务独立模型 (11 文件)
│   ├── routes/                  # HTTP 路由模块
│   ├── services/                # 业务逻辑实现 (~80 文件)
│   └── migrations/              # Alembic 数据库迁移
│
├── services/                    # 微服务入口 (每个 main.py)
│   ├── identity-service/        # 认证/用户 (:8101)
│   ├── learning-core-service/   # 学习进度 (:8102)
│   ├── catalog-content-service/ # 词库/书本 (:8103)
│   ├── ai-execution-service/    # AI 对话/评估 (:8104)
│   ├── tts-media-service/       # TTS 语音 (:8105)
│   ├── asr-service/             # 语音识别 HTTP + Socket.IO (:8106, :5001)
│   ├── notes-service/           # 笔记/摘要 (:8107)
│   └── admin-ops-service/       # 管理后台 (:8108)
│
├── scripts/                     # 部署/迁移/验证 (~65 文件)
├── docs/                        # 架构/治理/运维文档
└── vocabulary_data/             # 雅思词库 JSON 数据集
```

---

## 二、微服务运行时拓扑

### 2.1 请求入口

```
浏览器 (https://axiomaticworld.com)
  │
  ▼
Nginx (:443/:80)
  ├── /api/*        → Gateway BFF    (127.0.0.1:18000 / :28000 蓝绿)
  ├── /socket.io/*  → ASR Socket.IO  (127.0.0.1:5001)
  └── /*            → Vite Preview 静态文件
```

### 2.2 端口分配

| 服务 | 本地端口 | 生产端口 (蓝) | 生产端口 (绿) |
|------|---------|-------------|-------------|
| Frontend Preview | 3002 | - | - |
| Gateway BFF | 8000 | 18000 | 28000 |
| Identity Service | 8101 | 18101 | 28101 |
| Learning Core | 8102 | 18102 | 28102 |
| Catalog Content | 8103 | 18103 | 28103 |
| AI Execution | 8104 | 18104 | 28104 |
| TTS Media | 8105 | 18105 | 28105 |
| ASR HTTP | 8106 | 18106 | 28106 |
| Notes | 8107 | 18107 | 28107 |
| Admin Ops | 8108 | 18108 | 28108 |
| ASR Socket.IO | 5001 | 5001 | 5001 |

### 2.3 领域 Worker

| Worker | 运行于 | 职责 |
|--------|--------|------|
| core-eventing-worker | identity-service | 核心事件发布/路由 |
| notes-domain-worker | notes-service | 笔记摘要生成 |
| ai-execution-domain-worker | ai-execution-service | AI 投影物化 |
| admin-ops-domain-worker | admin-ops-service | 管理投影物化 |

---

## 三、服务架构模式

### 3.1 统一服务结构

除了 Gateway BFF 和 ASR Service，其他 6 个微服务采用相同的架构模式：

```python
# 1. 加载服务专属环境变量
load_split_service_env(service_name='xxx-service')

# 2. 创建 Flask 应用 (业务逻辑，由 platform-sdk 中的 xxx_runtime.py 提供)
flask_app = create_xxx_flask_app()

# 3. 创建 Starlette 外壳 (提供 /health /ready /version)
app = create_service_shell_app(service_name='xxx-service', readiness_checks={...})

# 4. 通过 WSGI 中间件将 Flask 挂载到 Starlette
app.mount('/', WSGIMiddleware(flask_app))
```

**设计要点**：
- **Starlette 外壳**: 提供健康检查端点 (`/health`, `/ready`, `/version`)
- **Flask 内核**: 承载所有业务路由和中间件，复用 `backend/config.py` 配置
- **Flask 应用工厂**: 位于 platform-sdk 的 `*_runtime.py` 文件中
- **数据库**: 通过 SQLAlchemy + 每服务独立 PostgreSQL 数据库

### 3.2 三类服务入口

| 类型 | 服务 | 特征 |
|------|------|------|
| **纯代理网关** | Gateway BFF | FastAPI (`create_service_app`)，不挂载 Flask |
| **Starlette + Flask** | Identity, Learning Core, Catalog, AI Exec, Notes, Admin Ops | `create_service_shell_app` + `WSGIMiddleware(flask_app)` |
| **纯 Starlette** | ASR HTTP, ASR Socket.IO | `create_service_shell_app`，无 Flask 依赖 |

TTS Media Service 比较特殊：主体使用 FastAPI (`create_service_app`)，同时持有 Flask 应用仅用于数据库访问 (`tts_media_flask_app.app_context()`)。

---

## 四、Gateway BFF 路由映射

Gateway BFF 是**无业务逻辑的纯代理层**。路由映射定义在 `platform-sdk/platform_sdk/gateway_browser_routes.py`：

```
/api/auth/*                              → identity-service
/api/progress/*                          → learning-core-service
/api/books/progress/*                    → learning-core-service
/api/books/my/*                          → learning-core-service
/api/books/favorites/*                   → learning-core-service
/api/books/familiar/*                    → learning-core-service
/api/books/word-feedback                 → admin-ops-service
/api/books/word-details/note             → notes-service
/api/books/*                             → catalog-content-service
/api/vocabulary/*                        → catalog-content-service
/api/ai/*                                → ai-execution-service
/api/notes/*                             → notes-service
/api/admin/*                             → admin-ops-service
/api/exams/*                             → admin-ops-service
/api/feature-wishes/*                    → admin-ops-service
/api/ops/frontend-error-logs             → admin-ops-service
/api/tts/*                               → 网关直接处理 (代理至 tts-media-service)
/api/speech/transcribe                   → 网关直接处理 (代理至 asr-service)
```

代理层特性：熔断器、超时重试、SSE 流式转发、请求 tracing。

---

## 五、服务间通信

### 5.1 内部认证链

```
浏览器 Cookie (JWT access_token, 30min TTL)
  → Gateway BFF 提取 token 并解码
    → 创建内部 JWT (60s TTL, x-internal-service-auth header)
      → 传播: x-user-id, x-request-id, x-trace-id, x-service-name
        → 下游服务解码内部 token 获取 InternalServiceUser
```

### 5.2 领域事件系统 (RabbitMQ)

6 个事件契约通过 **Outbox 模式** 发布到 RabbitMQ Topic Exchange `ielts-vocab.domain`：

| 事件 | 发布者 | 消费者 |
|------|--------|--------|
| `identity.user.registered` | identity | admin-ops |
| `learning.session.logged` | learning-core | admin-ops, notes |
| `learning.wrong_word.updated` | learning-core | admin-ops, ai-execution, notes |
| `notes.summary.generated` | notes | admin-ops, ai-execution |
| `tts.media.generated` | tts-media | admin-ops |
| `ai.prompt_run.completed` | ai-execution | admin-ops, notes |

**Outbox 模式工作流**: `queue_outbox_event → claim_outbox_events → publish to RabbitMQ → mark_outbox_event_published`

### 5.3 内部 HTTP 调用

跨服务同步读请求通过内部 HTTP 客户端实现（如 `learning_core_internal_client.py`），使用 `x-internal-service-auth` 头进行认证。严格模式下如果目标服务不可用则返回 503，向后兼容模式下可回退到共享表读取。

---

## 六、代码分层

### 6.1 共享层 (platform-sdk)

`packages/platform-sdk/platform_sdk/` 约 120+ 模块，按职责组织：

| 层次 | 命名模式 | 职责 |
|------|---------|------|
| Transport | `*_transport.py` | FastAPI Router / Flask Blueprint |
| Runtime | `*_runtime.py` | Flask 应用工厂、服务初始化 |
| Application | `*_application.py` | 业务用例编排、事务协调 |
| Repository | `*_repository*.py` / `backend/services/*_repository.py` | 数据访问 |
| Internal Client | `*_internal_client.py` | 跨服务 HTTP 调用客户端 |
| Infrastructure | `redis_runtime.py`, `rabbitmq_runtime.py`, `outbox_runtime.py` | 基础设施 |
| Auth | `internal_service_auth.py` | 服务间 JWT 认证 |
| Proxy | `http_proxy.py`, `gateway_browser_routes.py` | HTTP 代理和网关路由 |
| Storage | `storage/aliyun_oss.py` | 阿里云 OSS 集成 |

### 6.2 服务模型注册

每个服务加载一组独立的 SQLAlchemy 模型模块（定义在 `service_model_registry.py`）：

| 服务 | 加载的模型模块 |
|------|-------------|
| identity-service | identity_models, eventing_models |
| learning-core-service | learning_core_models, eventing_models, identity_models, catalog_content_models |
| catalog-content-service | catalog_content_models, eventing_models, identity_models, notes_models |
| ai-execution-service | ai_execution_models, eventing_models, identity_models, learning_core_models, notes_models, catalog_content_models |
| notes-service | notes_models, eventing_models, identity_models, learning_core_models, catalog_content_models |
| admin-ops-service | admin_ops_models, eventing_models, identity_models, learning_core_models, catalog_content_models |
| tts-media-service | eventing_models, identity_models |
| asr-service | eventing_models, identity_models |

---

## 七、数据库

### 7.1 基础设施

- **本地开发**: PostgreSQL 127.0.0.1:55432 + Redis 127.0.0.1:56379 + RabbitMQ 127.0.0.1:5679
- **生产**: PostgreSQL + Redis + RabbitMQ 部署于同一 CVM
- **每个服务独立 PostgreSQL 数据库**（如 `ielts_identity_service`, `ielts_learning_core_service` 等）
- **Redis**: 每服务独立 DB 编号 (DB 0-8)
- **ORM**: SQLAlchemy + Flask-SQLAlchemy (带安全保护的自定义子类)
- **迁移**: Alembic + 服务级迁移脚本

### 7.2 模型组织

两套模型体系共存：

1. **`model_definitions/`** (15 个文件) — 遗留共享表定义，由 `backend/models.py` 通过 `load_split_module_files()` 加载
2. **`service_models/`** (11 个文件) — 按服务拆分的模型引用，每个服务只导入所需的模型子集

### 7.3 核心数据表

- **用户/认证**: `users`, `revoked_tokens`, `email_verification_codes`, `user_oauth_identities`
- **学习进度**: `user_progress`, `user_book_progress`, `user_chapter_progress`, `user_chapter_mode_progress`
- **学习汇总** (5 层物化聚合): `user_learning_daily_ledgers` → `user_learning_chapter_rollups` → `user_learning_mode_rollups` → `user_learning_book_rollups` → `user_learning_user_rollups`
- **学习活动**: `user_study_sessions`, `user_wrong_words`, `user_quick_memory_records`, `user_smart_word_stats`
- **书本内容**: `custom_books`, `custom_book_chapters`, `custom_book_words`
- **AI 运行时**: `ai_prompt_runs`, `ai_word_image_assets`, `ai_speaking_assessments`
- **事件溯源**: 每服务独立的 `*_outbox_events` / `*_inbox_events` 表
- **管理投影**: 按 admin/ai/notes 服务分别维护的投影表（`admin_projected_users`, `ai_projected_wrong_words`, `notes_projected_study_sessions` 等）

---

## 八、前端架构

### 8.1 技术栈

- **框架**: React 19.2 + TypeScript 5.9
- **构建**: Vite 5.4
- **路由**: react-router-dom 7.13
- **样式**: SCSS + CSS Custom Properties (设计令牌系统)
- **验证**: Zod 4.3
- **实时通信**: Socket.IO Client 4.8
- **测试**: Vitest 2.1 + Testing Library 16 (148 单元测试) / Playwright 1.58 (15 E2E 测试)

### 8.2 依赖方向

```
app/  (路由、Shell、Provider)
  → components/<domain>/page  (页面组件)
    → composables/<domain>    (页面编排逻辑)
      → features/<domain>     (领域服务、hooks、store)
        → lib/                (apiClient、schemas、工具)
        → components/ui/      (基础 UI 原语)
```

### 8.3 状态管理

不使用 Redux 等外部库，纯 **React Context + Custom Hooks**:

| Context | 职责 |
|---------|------|
| AuthContext | 认证状态、Token 刷新、HttpOnly Cookie + localStorage 缓存 |
| SettingsContext | 暗黑模式、字体大小、主题色 (持久化到 localStorage) |
| ToastContext | 全局 Toast 通知 |
| AIChatContext | AI 对话学习上下文 (当前单词/书本/模式/进度) |

### 8.4 路由结构 (22 个路由)

| 路由 | 页面 | 认证 |
|------|------|------|
| `/login`, `/register`, `/forgot-password` | AuthPage | Guest |
| `/terms` | TermsPage | 公开 |
| `/plan` | HomePage (学习计划) | Required |
| `/practice?mode=` | PracticePage (8 种练习模式) | Required |
| `/practice/confusable` | ConfusableMatchPage | Required |
| `/books`, `/books/create` | VocabBookPage, CreateCustomBookPage | Required |
| `/game`, `/game/themes`, `/game/themes/:id`, `/game/themes/:id/mission`, `/game/mission` | GameCampaignPage | Required |
| `/exams`, `/exams/:id` | ExamsLibraryPage, ExamAttemptPage | Required |
| `/errors` | ErrorsPage (错词复习) | Required |
| `/stats` | StatsPage (统计) | Required |
| `/profile` | ProfilePage | Required |
| `/journal` | LearningJournalPage | Required |
| `/vocab-test` | VocabTestPage | Required |
| `/admin` | AdminDashboard | Admin |
| `/speaking` | → 重定向至 `/game` | Required |

### 8.5 练习模式 (8 种)

| 模式 | ID | 描述 |
|------|-----|------|
| Smart | `smart` | 自适应模式，基于学习者画像 |
| Quick Memory | `quickmemory` | 快速单词识别 + 艾宾浩斯间隔复习链 |
| Listening | `listening` | 听发音选中文释义 |
| Meaning | `meaning` | 看中文释义写英文单词 |
| Dictation | `dictation` | 听单词拼写 |
| Follow | `follow` | 慢速跟读 + 语音评分 |
| Radio | `radio` | 连续音频播放 |
| Errors | `errors` | 专注错词复习 |

### 8.6 API 调用层

集中在 `lib/apiClient.ts`，所有请求通过 `apiFetch<T>()` 发送，特性：
- HttpOnly Cookie 自动携带 (`credentials: 'include'`)
- 主动 Token 刷新 (过期前 60s)
- 响应式 401 处理 (尝试刷新后重试一次)
- 并发刷新请求去重
- 默认 30s 超时
- 可选的 `X-Trace-Id` / `Idempotency-Key` 头

### 8.7 设计令牌系统

`styles/base.tokens.scss` 定义约 300+ CSS 变量：
- 尺寸/圆角/间距标准化
- 响应式断点 (375/480/640/768/1024/1280/1440)
- 完整色彩体系 (基础/语义/图表色)
- 暗黑模式 (`[data-theme="dark"]`)
- Z-index 分层体系
- 排版 (PingFang SC, Microsoft YaHei 中文字体栈)

---

## 九、部署架构

### 9.1 生产环境

- **主机**: 腾讯云 CVM (2核4GB) @ `119.29.182.134`
- **OS**: Linux (systemd + Nginx)
- **Web 根**: `/var/www/ielts-vocab/current` → 当前发布 symlink
- **应用根**: `/opt/ielts-vocab/`
- **发布模式**: `releases/{timestamp}-{commit}/`
- **无 Docker/K8s**，裸金属部署

### 9.2 部署方式

**蓝绿部署**：两套完整微服务实例运行在不同端口范围，Nginx 切换 upstream：

- **蓝槽**: Gateway BFF :18000, 服务 :18101-18108
- **绿槽**: Gateway BFF :28000, 服务 :28101-28108

**systemd 管理**：
- `ielts-service@gateway-bff` 等 10 个服务单元
- `ielts-service@core-eventing-worker` 等 4 个 Worker 单元
- `ielts-health-watchdog.service` + `.timer` 健康监控

### 9.3 CI/CD

GitHub Actions 流水线：

1. **CI** (每次 push/PR): 文档检查 → 前端 lint/test/build → 后端 pytest → 依赖审计 → macOS 冒烟测试
2. **Deploy** (push main / 手动触发): 解析 ref → 测试门禁 (前端/后端发布风险测试) → 构建产物 → rsync 上传 → 远端部署

---

## 十、当前迁移状态 (Wave 5 后)

### 10.1 已完成

- 8 个微服务全部拆分并独立运行
- 领域事件系统上线 (6 个事件，Outbox + RabbitMQ)
- 管理/笔记/AI 投影系统已建立
- 蓝绿部署机制就绪
- 服务间内部认证链路完成
- OSS 存储集成完成

### 10.2 进行中

- 共享表读取"退役"：逐步将 `admin / notes / ai` 对共享表的直接读取改为内部 API 调用 + 本地投影
- 严格运行模式下，缺失投影标记视为边界错误（不再静默回退共享行）

### 10.3 仍存在的兼容模式

- `start-monolith-compat.sh`: 旧版单体 Flask 兼容模式，作为回退路径
- `backend/services/` 中部分文件与 `platform-sdk/` 存在耦合
- 部分跨服务读请求在内部调用失败时仍可回退到共享表读取（仅在非严格模式下）

---

## 十一、关键技术决策

1. **Strangler Fig 而非 Big Bang 重写**: 保留旧版单体作为兼容回退，逐步提取服务
2. **Starlette + Flask 而非纯 FastAPI**: 复用现有 Flask 中间件和配置系统，最小化改动
3. **Outbox 模式保证事件可靠投递**: 数据库写入与事件发布在同一事务中，异步 Worker 消费
4. **内部 JWT 传播用户身份**: Gateway 解码浏览器 Token 后签发短 TTL 内部 Token，下游无感
5. **蓝绿部署**: 支持零停机发布和快速回滚
6. **裸金属而非容器化**: 适配单机部署场景，减少运维复杂度
7. **React Context 而非 Redux**: 应用状态复杂度不需要外部状态管理库
