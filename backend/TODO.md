# TODO
Last updated: 2026-04-09 00:05:00 +08:00

## 目标定位
- [进行中] 下一阶段后端目标不再是“长期保持微服务风格的分层模块化单体”，而是以当前单体为迁移源，升级为标准化微服务体系。
- [进行中] 当前 `5000` 主 Flask 应用继续作为过渡期 gateway / BFF 和核心编排层存在，但它是迁移中的过渡角色，不是最终架构终点。
- [进行中] 当前已拆出的 [speech_service.py](/F:/enterprise-workspace/projects/ielts-vocab/backend/speech_service.py) 继续作为第一批独立服务样板，用来验证独立部署、独立健康检查、代理转发和服务契约。
- [进行中] 所有新增后端代码仍需遵守 `route -> application service -> domain/provider -> repository/models`，避免在迁移期一边拆服务、一边重新把耦合写回主应用。

## 平台前置项
- [待完成] 冻结第一版服务目录、服务职责和 authoritative data ownership matrix，明确每个服务“谁负责写、谁只能读、谁必须通过接口访问”。
- [待完成] 定义统一的服务间鉴权与上下文传递协议，至少覆盖 `request_id`、`trace_id`、`user_id`、`scopes`、内部服务签名或内部 JWT。
- [待完成] 定义统一的服务配置规范，约束环境变量命名、密钥注入、端口命名、超时配置、重试配置和 provider 凭据加载方式。
- [待完成] 为每个独立服务补齐 `/health`、`/ready`、启动失败可观测日志和依赖自检，避免“端口起来但服务不可用”。
- [待完成] 建立统一的结构化日志、指标和链路追踪基线，至少覆盖 gateway、ASR、TTS、Catalog、AI execution 这第一批候选服务。
- [待完成] 统一服务调用的超时、重试、幂等键、熔断和降级规则，禁止在 gateway 中无限等待下游服务。
- [待完成] 补齐本地多服务联调方案，目标是单命令或单编排文件拉起 `gateway + ASR + TTS + Catalog + AI execution` 的最小开发环境。
- [待完成] 补齐 gateway 与下游服务之间的契约测试、兼容性测试和回归测试，不允许只靠浏览器手点验证服务拆分。
- [待完成] 在涉及跨服务状态同步前，确定 outbox / event / replay / idempotency 策略，避免未来出现“双写成功一半”的一致性问题。

## 目标服务目录
- [待完成] `gateway-bff`：统一承接浏览器入口、会话鉴权、接口聚合、版本兼容、限流和服务路由；不再长期持有大段业务规则或 provider 适配逻辑。
- [待完成] `asr-service`：负责实时识别、文件转写、音频会话管理和 ASR provider 适配；对外暴露明确的 Socket.IO / HTTP 契约。
- [待完成] `tts-media-service`：负责音频生成、缓存、素材产物管理和 TTS provider 适配；从核心应用中移出音频生成生命周期。
- [待完成] `catalog-content-service`：负责词库内容、目录、详情富化、例句和内容索引；内容类能力从学习状态类能力中彻底分离。
- [待完成] `ai-execution-service`：负责 LLM 调用、prompt 执行、流式输出、工具执行适配和模型 provider 路由；核心应用保留用户上下文拼装和产品编排。
- [待完成] `learning-core-service`：作为后续核心域服务，负责学习进度、错词、quick-memory、study session、learner profile 输入和学习统计原始事实。
- [待完成] `notes-service`：作为后续内容型域服务，负责学习笔记、总结任务、导出和日记类数据。
- [待完成] `identity-service`：在会话模型、权限边界和内部鉴权稳定后，再从 gateway 中分离认证、刷新令牌、邮件验证和账号安全能力。
- [待完成] `admin-ops-service`：在权限、审计和后台运营边界明确后，再从核心应用中拆出管理员视角的查询、操作和报表能力。

## 数据所有权规则
- [待完成] 一旦某个能力被认定为独立服务，其写路径必须收口到该服务；gateway 和其他服务不得继续直写其表或文件产物。
- [待完成] 在独立服务完全接管前，允许过渡期共享数据库，但必须先冻结“谁拥有写权限”的规则，避免名义上分服务、实际上共享写库。
- [待完成] 数据库拆分必须晚于服务 ownership 稳定；禁止用“先拆库”代替“先拆职责”。
- [待完成] 为未来拆库准备迁移方案，包括数据导出、回填、只读镜像、双写窗口、回滚路径和数据校验脚本。
- [待完成] 对跨服务查询优先使用接口聚合、缓存只读投影或事件驱动读模型，而不是重新建立跨服务共享写表。

## 迁移阶段
- [待完成] Phase 0: 平台准备。先完成服务目录、鉴权上下文、健康检查、日志指标追踪、契约测试和多服务本地运行基线。
- [待完成] Phase 1: 抽象接口。先在主仓库内为 `ASR / TTS / Catalog / AI execution` 建立稳定服务契约、请求 DTO、错误码和 provider adapter 边界。
- [待完成] Phase 2: 独立部署。将 `ASR / TTS / Catalog / AI execution` 至少三个能力从主应用中切成独立可部署服务，由 gateway 通过明确协议调用。
- [待完成] Phase 3: Gateway 收敛。将主 Flask 应用逐步缩减为真正的 gateway / BFF，仅保留边缘鉴权、聚合、兼容和路由职责。
- [待完成] Phase 4: 核心域拆分。依据学习事实、笔记内容、身份认证、运营管理的 ownership，逐步拆出 `learning-core / notes / identity / admin-ops`。
- [待完成] Phase 5: 存储拆分。仅在服务拥有稳定接口、稳定部署、稳定观测和清晰 ownership 后，再执行 per-service storage 分离。

## 拆分门槛
- [待完成] 任何能力在升级为独立微服务前，必须先拥有明确 API 契约、错误语义、超时策略、重试策略和回滚预案。
- [待完成] 任何能力在升级为独立微服务前，必须先拥有独立健康检查、独立部署入口、独立日志和基础指标。
- [待完成] 任何能力在升级为独立微服务前，必须先明确 authoritative data、写权限边界和与 gateway 的兼容策略。
- [待完成] 任何能力在升级为独立微服务前，必须先通过自动化契约测试，而不是只在浏览器页面上做冒烟验证。
- [待完成] Gateway 只有在下游服务可独立部署、可独立观测、可独立回滚后，才允许删除主应用内的兼容实现。

## 暂不提前拆分
- [待完成] 在内部鉴权、上下文传递和数据 ownership matrix 稳定前，不提前拆 `auth`。
- [待完成] 在学习事实源和统计读模型稳定前，不提前拆 `learning-stats`、`learner-profile`。
- [待完成] 在运营后台的权限模型、审计需求和服务依赖稳定前，不提前拆 `admin`。
- [待完成] 在 `notes` 与 `AI execution` 的接口和生成任务边界稳定前，不急于把笔记和总结能力拆成独立写库服务。

## 已完成基线
- [已完成] 后端已经从平铺式结构演进为分层模块化单体，主运行路径中的 transport、application、domain、provider、persistence 边界已经基本明确。
- [已完成] `backend/services` 主运行路径中的直接 `.query` / `db.session` 已经大范围收敛到 `*_repository.py`，为未来按能力移动持久化边界打下基础。
- [已完成] 实时语音已经完成第一阶段拆分：主 HTTP 服务和语音 Socket.IO 服务已分成两个运行进程，端口分别为 `5000` 和 `5001`。
- [已完成] 主后端 HTTP 入口已切换为 `waitress + Flask app` 模式，运行时已经具备“应用逻辑”和“HTTP 服务进程”分层的基础形态。
