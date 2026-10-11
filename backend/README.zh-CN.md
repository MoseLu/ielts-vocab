# 后端总览

## 当前定位

后端不再是扁平的文件布局。
最贴切的描述是 **演进中的「微服务风格分层模块化单体」**:

- 一个可部署的 Flask 后端进程,负责对外提供 HTTP 接口
- 一个独立的语音进程,负责长生命周期的实时音频会话
- 能力模块按领域或外部供应商能力切分
- 共享的数据模型与 SQLite 持久化
- 当前的运行时路径已不再依赖路由到路由的直接 import,也不再在路由层直接执行 ORM 查询

它 **尚不是** 完整的微服务体系,因为存储、部署以及大部分业务逻辑仍然位于同一份代码库,基本共用同一份数据库。
当前后端是规划中微服务拆分的迁移源架构,并非最终的长期运行时形态。

## 分层地图

### L0 运行时与启动

- `app.py`
- `speech_service.py`
- `config.py`
- `services/runtime_async.py`

负责进程启动、Flask 装配、Socket.IO 装配、代理/运行时行为以及启动期修复。

### L1 传输与接口

- `routes/**`
- `routes/middleware.py`

负责 HTTP 与 Socket.IO 契约、请求解析、鉴权守卫、响应格式化以及端点注册。

### L2 应用服务

- `services/*_service.py`
- `services/study_sessions.py`
- `services/session_logging_service.py`
- `services/notes_query_service.py`

负责用例编排。该层为一项后端能力协调领域规则、持久化与供应商调用。

### L3 领域模块

- `services/learner_profile_service/**`
- `services/learning_stats_service_parts/**`
- `services/notes_summary_service_parts/**`
- `services/books_confusable_service_parts/**`
- `services/word_catalog_service_parts/**`

负责领域规则、计算、归一化、规划与不应依赖传输细节的业务策略。

### L4 供应商与集成适配器

- `services/llm_service/**`
- `services/word_tts_service/**`
- `services/asr_service.py`
- `services/asr_service_parts/**`
- `services/db_backup.py`

负责对接外部系统或运行时基础设施,例如 LLM、TTS、ASR、备份以及流式适配器。

### L5 持久化与数据模型

- `models.py`
- `model_definitions/**`
- `migrations/**`
- `services/*_repository.py`
- `database.sqlite`

负责 ORM 模型、Schema 形态、迁移状态以及持久化契约。

### L6 脚本、测试与运维

- `scripts/**`
- `tests/**`
- 根目录下的 `test_*.py`
- 日志、缓存、生成的音频产物

负责验证、一次性运维操作、本地诊断与资产生成。

## 能力模块

- `auth`:登录、注册、刷新、登出、邮箱验证
- `books`:词书目录、熟悉/收藏/易混词书、进度
- `ai`:助手、学习者画像、学习统计、工具上下文、摘要
- `notes`:摘要、任务、导出、笔记查询
- `speech`:实时 ASR 进程与上传转写
- `tts`:单词音频、句子音频、批量生成、OSS/音频缓存
- `shared runtime`:异步助手、本地时间、数据库备份、安全检查

## 主要数据流

1. 浏览器 -> `routes/*` -> `services/*` -> `models/db` -> JSON 响应
2. 浏览器 -> `speech_service.py` -> `services/asr_service*` -> DashScope 实时 ASR -> Socket.IO 事件
3. 浏览器 -> `routes/tts*` -> `services/word_tts*` 或 `services/tts_*` -> 供应商适配器 -> 音频字节或音频链接

## 推荐的依赖方向

`Runtime -> Transport -> Application -> Domain -> Provider/Persistence`

规则:

- `routes/*` 应优先调用 `services/*`,而不是直接查询模型
- 当前传输模块在运行时路径上已遵循该规则;剩余清理主要是兼容性的导出
- 领域模块不应依赖 Flask 请求对象
- 供应商适配器不应感知 HTTP 响应形态
- 持久化关注点应远离面向前端的传输代码

## 文档

- API 参考:[API.md](./API.md)
- 详细分层架构:[backend-layered-architecture.md](../docs/architecture/backend-layered-architecture.md)
- 服务归属矩阵:[service-ownership-matrix.md](../docs/architecture/service-ownership-matrix.md)
- 网关服务契约:[gateway-service-contracts.md](../docs/architecture/gateway-service-contracts.md)

面向浏览器的鉴权现已将 `HttpOnly Cookie + gateway-bff` 视为规范契约。任何面向用户的 API 示例都应通过 `gateway-bff` 引用 `/api/*`,而不是浏览器侧的 header-token 流程。
