# Project Notes
最后更新：2026-05-07 21:04:03 +08:00

## 完成后禁止停手（全局硬约束）

> 2026-06-03 新增：源于 `products/ielts-vocab` 上的真实失败案例——Agent 完成 13 次 `git-commit-batch` 提交循环后，列出四个 "下一步" 选项（m1 / m2 / m3 / m4），在用户已经接受 A 合并计划的情况下仍然停下来等待用户挑选，违反契约。用户明确要求停止这种行为。本节覆盖工作区其他位置及 OMX 模板中所有更温和的措辞，与上文的 "User-Confirmation Lockdown" 同级强制。

### 不变量（绝对）

- 已完成的步骤 **不是** 交接点。Agent 在得到可验证结果后，MUST 继续执行显然的下一项安全动作并在结尾汇报，除非下一项动作落在下文显式列出的"高风险集合"内。
- 在显然的下一步已经明确的情况下，**禁止**在任务末尾罗列多选项（"选 m1/m2/m3/m4"、"你要 X 还是 Y?"、"我该做 A 还是 B?"）。选定默认值、执行、汇报。
- "等待用户确认" 对普通的可逆本地工作而言 **永远不是** 合法的终态。只有当动作命中下文"高风险集合"时才允许等待。
- Agent 掌握下一动作的节奏。Owner 决定范围，而非节奏。

### 高风险集合（ONLY 唯一允许停下来的场景）

仅当动作命中以下类别之一时才允许停下来询问，且问题必须指明具体风险：

- 破坏性 / 不可逆动作（`rm -rf`、force-push、删除数据库、清空状态、删掉唯一副本）。
- 凭据相关动作（部署密钥、发布令牌、生产密钥、SSH 私钥）。
- 外部生产动作（真实用户、付费服务、发布包、基础设施 apply）。
- 超出用户当前任务陈述范围的实质性范围变更。
- 权限缺失（无法读取文件、无法连接服务、无法运行工具、仓库拒绝访问）。

其余一切——git commit / branch / push、文件编辑、安装、构建、测试、lint、typecheck、重启本地服务、运行脚本、生成报告、发送通知、编写文档、更新记忆、清理产物——Agent MUST 直接执行并汇报。

### "继续" 在实践中的体现

- 一批提交完成并验证后：选择显然的下一项本地动作（例如切到集成分支、跑一次快速验证、写汇总文档、任务说 push 就 push）并执行。**不要**列选项。
- 一次 build / test / lint 通过后：汇报结果，然后继续任务的下一步。**不要**问 "还有其他事吗？"
- 通知发出后：记录日志，不要等待。
- 长命令执行完后：读取输出、决策、行动。
- 遇到真阻塞时：点明阻塞、最小的默认计划、唯一能解除阻塞的不可逆动作——但不要凭空添加额外的检查点。

### 反模式（不得出现在 Agent 输出中）

- "Next steps: m1 ... m2 ... m3 ... which do you want?"
- "Let me know if you'd like me to ..."
- "I can do X or Y, your call."
- "Should I continue with ..."
- "Just confirm and I'll proceed."
- "If you want, I can ..."
- 在已经交付了清晰、可逆的结果后，把节奏决定权甩回给用户的结尾段落。
- 在成功步骤后写 "Stopping here" / "I'll wait" / "Ready when you are"。

### 发送任务最终消息前的自检

在发出任务最后一条消息前，先问自己：

1. "我是不是刚在一个已完成步骤后罗列了多选项？"如果是，删掉列表，改成我下一步要做的动作。
2. "下一步是否在上文高风险集合内？"如果不在，现在就执行下一步，并在同一条消息内汇报。
3. "如果我正要发问，问题是用户独有信息缺失，还是我在要求他们重做已经决定的事？"如果是后者，删掉问题。
4. "在同一条回合内，是否还有安全、可逆的下一步可以做？"如果有，先做完再发。

一条正确的最终消息读起来是"汇报 + 下一动作"，绝不是"汇报 + 菜单"。


## 仓库概览
- IELTS 词汇学习 monorepo，包含 Web 端、React Native 移动端、共享 TypeScript 客户端核心，以及 Flask / 拆分服务的后端形态。
- 主要 scope：`frontend/` 承载 Web 包；`apps/mobile/` 承载 React Native Android/iOS；`packages/app-core/` 承载跨端契约与纯逻辑；`backend/` 承载接口与持久化；`services/` 加 `apps/gateway-bff/` 承载拆分后的运行时服务；`vocabulary_data/` 承载词书资产；`docs/` 承载可持久化的计划、审计与 runbook。
- 未来的客户端请放在 `apps/*`：待开工的微信小程序用 `apps/miniprogram/`；仅当 iOS 不再共用 React Native app 时才新增 `apps/ios/`。
- 运行时把拆分后端视为本地规范路径：预览 UI 在 `3002`，浏览器 API 入口在 `8000`，下游服务在 `8101-8108`，语音 Socket.IO 在 `5001`。

## 工作约定
- 仓库文本文件均按 UTF-8 处理，除非文件本身另有声明。
- 使用 `apply_patch` 之前，先读取精确的目标行，并以稳定的 ASCII 或代码结构为锚点。
- 当文件出现编码损坏时，重写整个逻辑块，而不是堆叠小补丁去打 mojibake。
- 跟踪的手编辑文本文件保持 `<= 500` 行，除非被已 check-in 的超长基线覆盖。
- 把 `vocabulary_data/**` 与 `pnpm-lock.yaml` 视为生成产物，免于 `500` 行上限。
- 提交前保持 `pnpm check:file-lines` 与 `pnpm lint` 绿灯；`pnpm build` 与 `pnpm test` 现在会自动跑 guardrail 套件。
- 在移动端或共享客户端提交前保持 `pnpm verify:clients` 绿灯。
- Android 移动端工作时，不要让用户去启动模拟器。直接启动或复用本地 AVD `ielts_vocab_api35`，在 `8081` 启动 Metro，执行 `adb reverse tcp:8081 tcp:8081`，安装或启动 debug APK，并用前台 Activity、`logcat` 和模拟器截图来验证。仅在模拟器 / SDK 损坏或场景需要真机时才指出该缺口。
- 后端或文本密集改动后，保持 `pytest backend/tests/test_source_text_integrity.py -q` 绿灯。
- 把远程云端链路视为域 / 运行时问题的标准答案：`axiomaticworld.com -> nginx(:443/:80) -> active HTTP slot gateway-bff(:18000|:28000) -> downstream services(:18101-18108|:28101-28108)`，`/socket.io` 代理到 `:5001` 的 ASR Socket.IO。
- 本地拆分运行时仅用于复现：预览 UI 在 `3002`，浏览器 API 入口在 `8000`，下游服务在 `8101-8108`，语音 Socket.IO 在 `5001`。
- 改动运行时启动流程时，让 `start-project.sh`、`start-microservices.sh`、`start-monolith-compat.sh` 与 `frontend/vite.config.ts`、`nginx.conf.example` 以及真实服务端口保持一致。

## 当前焦点
- 保持 Wave 后微服务基线稳定：正常拆分启动不再暴露共享 `SQLite` 覆盖开关，服务启动的环境变量加载由文件驱动，tts/asr 迁移基线已登记，gateway / internal 鉴权更严，OSS 制品校验为绿，`scripts/repo_summary.py` 已恢复。
- 语音服务拆分后，保持生产形态本地启动和代理行为稳定。
- 让 Ebbinghaus 到期复习、错词恢复与基础练习模式（`smart`、`listening`、`meaning`、`dictation`、`follow`、`quickmemory`、`errors`）与统计、学习者画像、复习队列计数直接对齐。
- 把五维游戏与 AI 口语评测视作独立的进阶模式族，不要把基础 Ebbinghaus 或错词恢复路由进 `/game`。
- 继续打磨学习中心与首页视觉，且不破坏桌面 / 移动端布局。
- 切流后剩余的工作以运维为主：代码侧 `admin / notes / ai` 边界清理已就位、正常拆分运行时的表审计已清，剩下未完成的是最终的远程 release / 部署 / 预检 / 冒烟 / 存储演练收尾。

## 同步最新备注
- Wave 收尾又前进了一步：[identity_transport.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/identity_transport.py) 与 [identity_admin_application.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/identity_admin_application.py) 现在为 `admin-ops-service` 暴露一条内部 `set-admin` 契约，[identity_admin_internal_client.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/identity_admin_internal_client.py)、[admin_user_management_application.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/admin_user_management_application.py) 与 [admin_user_management_service.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/admin_user_management_service.py) 现在都通过该契约路由 admin 开关，兼容模式才走 legacy fallback，[admin_projection_repository_support.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/admin_projection_repository_support.py) 现在把缺失的 admin projection 标记视作严格边界、不再静默落到共享行，[ai_context_application.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/ai_context_application.py) 现在在严格 AI 运行时下返回空的 learner-profile 快照、不再做本地共享表回退，[service_table_plan.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/service_table_plan.py) 现在把 `admin-ops-service`、`notes-service`、`ai-execution-service` 报告为 `transitional_tables: []`，用于正常拆分运行时审计。
- 收尾 Wave 5：[notes_summary_context_repository.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/notes_summary_context_repository.py) 现在在严格 `notes-service` 运行时下阻断共享学习会话 / 错词回退，只在显式 legacy 模式下保留回退，[notes_summary_jobs_application.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/notes_summary_jobs_application.py) 与 [notes_summary_job_service.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/notes_summary_job_service.py) 现在在同步 / 异步摘要生成上呈现同样的 `503 strict-internal-contract` 边界，[search_cache_repository.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/search_cache_repository.py) 现在把通用网络搜索的缓存键优先存到 Redis，数据库仅作回退，关闭了 Wave 5 缓存键的最后一个口子。
- 继续 Wave 5 Redis 化语音状态：[realtime_session_state_runtime.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_session_state_runtime.py) 现在把带 transcript 感知的会话快照持久化到 Redis，并对 `partial_transcript` / `final_transcript` 摘要设长度上限，[realtime_sessions.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_sessions.py) 与 [realtime_socketio.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_socketio.py) 在所有 realtime ASR 事件中保持这些 transcript 字段同步更新，[socketio_service.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/socketio_service.py) 现在把 `/internal/sessions/<session_id>` 暴露给运维读取实时会话快照。
- 继续 Wave 5 共享读退役，落在 `admin` HTTP 面上：[admin_user_detail_repository.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/admin_user_detail_repository.py) 现在在严格拆分运行时下，当 `learning-core-service` 内部读取失败时，不再静默读共享 `UserBookProgress` / `UserChapterProgress` / `UserFavoriteWord` / `UserLearningEvent`，而是抛出服务边界错误，[admin_overview_service.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/admin_overview_service.py)、[admin_user_management_service.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/admin_user_management_service.py)、[admin_overview_application.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/admin_overview_application.py) 与 [admin_user_management_application.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/admin_user_management_application.py) 现在在 `/api/admin/users` 与 `/api/admin/users/<id>` 上把这个情况显式呈现为 `503 strict-internal-contract` 响应。
- 新增受控的 Wave 5 projection 切流套件：[wave5_projection_cutover.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/wave5_projection_cutover.py) 现在统一跑 `admin / notes / ai` bootstrap 流程并核对 marker 就绪度以及源 / 投影行数对账，[run-wave5-projection-cutover.py](/Volumes/code/workspace/products/ielts-vocab/scripts/run-wave5-projection-cutover.py) 把它暴露为运维命令，本地一次跑通得到 `admin users=2 study_sessions=578 wrong_words=1644`、`notes study_sessions=578 wrong_words=1644`、`ai wrong_words=1644 daily_summaries=0`。
- 继续 Wave 5 共享读退役，落在 `notes-service` fallback 路径上：[learning_core_notes_context_application.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_notes_context_application.py) 与 [learning_core_transport.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_transport.py) 现在暴露 `/internal/learning/notes-context/study-sessions` 与 `/internal/learning/notes-context/wrong-words`，[learning_core_notes_context_internal_client.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_notes_context_internal_client.py) 现在为 `notes-service` 提供这些路由的类型化快照，[notes_summary_context_repository.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/notes_summary_context_repository.py) 在严格拆分运行时下优先 `projection -> internal`，仅在显式 legacy fallback 开启时才退回到共享行。
- 继续 Wave 5 projection 切流硬化，落在 `notes` 与 `ai` 的读侧：[notes_projection_bootstrap.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/notes_projection_bootstrap.py) 与 [ai_projection_bootstrap.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/ai_projection_bootstrap.py) 现在会回填 notes 的 study-session / wrong-word 和 AI 的 wrong-word / daily-summary 投影，并写入 service 拥有的 cursor 与 bootstrap marker 行，[bootstrap-notes-projections.py](/Volumes/code/workspace/products/ielts-vocab/scripts/bootstrap-notes-projections.py) 与 [bootstrap-ai-projections.py](/Volumes/code/workspace/products/ielts-vocab/scripts/bootstrap-ai-projections.py) 暴露这些流程作为运维脚本，[notes_summary_context_repository.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/notes_summary_context_repository.py)、[ai_wrong_word_projection_support.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/ai_wrong_word_projection_support.py) 与 [ai_daily_summary_projection_support.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/ai_daily_summary_projection_support.py) 现在改由显式 bootstrap marker 切换，不再依赖行数对账。
- 硬化 AI 内部调用 fallback，抵御本地端口干扰：[learning_core_internal_client.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_internal_client.py) 与 [catalog_content_internal_client.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/catalog_content_internal_client.py) 现在在边界层 `401/403/404/5xx` 响应上抛错，让 `run_with_legacy_cross_service_fallback` 在本地运行时与测试期间依然能落到本地兼容路径。
- 继续 Wave 5 `admin detail` 共享读退役，落在个性化侧：[learning_core_admin_detail_application.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_admin_detail_application.py) 与 [learning_core_transport.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_transport.py) 现在暴露 `/internal/learning/admin/favorite-words`，[learning_core_admin_detail_internal_client.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_admin_detail_internal_client.py) 现在拥有 admin-detail 的 learning-core 客户端快照，[admin_user_detail_repository.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/admin_user_detail_repository.py) 与 admin user-management application / service 现在优先走内部读取收藏词，仅在 `learning-core-service` 不可用时才走共享行回退。
- 把旧的超长 admin-detail 客户端 / 测试文件拆回 `500` 行护栏之内：[learning_core_internal_client.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_internal_client.py) 现在只保留通用 learning-core 客户端面，admin-detail 快照迁到 [learning_core_admin_detail_internal_client.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_admin_detail_internal_client.py)，learning-core admin-detail 的内部路由覆盖迁到 [test_internal_service_auth_admin_favorites.py](/Volumes/code/workspace/products/ielts-vocab/backend/tests/test_internal_service_auth_admin_favorites.py)，`pnpm check:file-lines` 重新转绿且没有新增基线豁免。
- 继续 Wave 5 `admin detail` 共享读退役，落在学习侧：[learning_core_admin_detail_application.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_admin_detail_application.py)、[learning_core_transport.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_transport.py) 与 [learning_core_internal_client.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/learning_core_internal_client.py) 现在暴露 / 使用 book progress、chapter progress、session word-sample events 的窄内部读端点，[admin_user_detail_repository.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/admin_user_detail_repository.py) 现在优先用这些内部读，仅在 `learning-core-service` 不可用时回退到本地共享读。
- 继续 Wave 5 `admin` 共享读退役，落在用户目录侧：[admin_user_directory_repository.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/admin_user_directory_repository.py) 现在一旦存在 bootstrap marker，就从 `AdminProjectedUser` 服务目录读，owner 写入仍走共享 `User`，[auth_repository.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/auth_repository.py) 与 `set-admin` 在写入时刷新投影用户快照，[test_wave5_identity_admin_event_flow.py](/Volumes/code/workspace/products/ielts-vocab/backend/tests/test_wave5_identity_admin_event_flow.py) 锁住"projection 优先"目录读以及 profile / admin 更新时刷新 projection 的行为。
- 收紧 Wave 5 `admin` projection 切流契约：[admin_projection_repository_support.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/admin_projection_repository_support.py) 现在按显式 bootstrap marker cursor 切换 user / session / wrong-word 读模型，不再用 projection 行数与共享表对账，相关 Wave 5 测试也锁住 marker 驱动的行为。
- 新增安全的 Wave 5 admin projection bootstrap 路径：[admin_projection_bootstrap.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/admin_projection_bootstrap.py) 现在从当前共享表回填 `AdminProjectedUser`、`AdminProjectedStudySession`、`AdminProjectedWrongWord` 并写入相关 `AdminProjectionCursor` 行，[bootstrap-admin-projections.py](/Volumes/code/workspace/products/ielts-vocab/scripts/bootstrap-admin-projections.py) 把该流程暴露为运维脚本，[test_admin_projection_bootstrap.py](/Volumes/code/workspace/products/ielts-vocab/backend/tests/test_admin_projection_bootstrap.py) 锁住回填与幂等刷新契约。
- 新增第一块 Redis 化 ASR 临时状态：[realtime_session_state_runtime.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_session_state_runtime.py) 现在把 realtime 会话元数据镜像到 Redis，提供 TTL 快照与活跃会话计数，[realtime_socketio.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_socketio.py) 与 [realtime_sessions.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/asr_runtime/realtime_sessions.py) 在会话生命周期切换时同步该状态，[test_asr_realtime_session_state_runtime.py](/Volumes/code/workspace/products/ielts-vocab/backend/tests/test_asr_realtime_session_state_runtime.py) 锁住 Redis 快照契约。
- 上线第一份真正 Redis 化的 Wave 5 工作负载：[identity_rate_limit_runtime.py](/Volumes/code/workspace/products/ielts-vocab/packages/platform-sdk/platform_sdk/identity_rate_limit_runtime.py) 现在用 `Redis-first` 计数器驱动 auth / email 限流，数据库作回退，[auth_repository.py](/Volumes/code/workspace/products/ielts-vocab/backend/services/auth_repository.py) 现在让 login、bind-email code、forgot-password 检查都走这条路径，[test_auth_rate_limiting.py](/Volumes/code/workspace/products/ielts-vocab/backend/tests/test_auth_rate_limiting.py) 锁住 Redis 与 DB 回退两种行为。
- 把 Wave 5 worker-aware 部署契约纳入常规发布路径：[run-service.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/run-service.sh)、[release-common.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/release-common.sh)、[smoke-check.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/smoke-check.sh) 不再等未来的 rollout 步骤，剩余的 Wave 5 收尾工作是更广的共享读退役与 Redis 化工作负载落地。
- 在 [deploy-release.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/deploy-release.sh) 与 [run-service-schema-migrations.py](/Volumes/code/workspace/products/ielts-vocab/scripts/run-service-schema-migrations.py) 中加入部署时的拆分服务 schema 迁移支持，然后把迁移 runner 与 app 密钥解耦，使部署 bootstrap 能在加载 service-specific 密钥材料前先跑。
- 通过收紧 [AuthContext.tsx](/Volumes/code/workspace/products/ielts-vocab/frontend/src/contexts/AuthContext.tsx) 与 [index.ts](/Volumes/code/workspace/products/ielts-vocab/frontend/src/lib/index.ts) 中的共享存储 helper，在部署重启间保留前端 auth 会话；回归覆盖在 [AuthContext.test.tsx](/Volumes/code/workspace/products/ielts-vocab/frontend/src/contexts/AuthContext.test.tsx) 与 [index.test.ts](/Volumes/code/workspace/products/ielts-vocab/frontend/src/lib/index.test.ts)。
- 新增 Wave 5 远程 worker 部署契约：[run-service.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/run-service.sh) 现在把所有 outbox / projection worker 都路由到 `ielts-service@<worker>`，[release-common.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/release-common.sh) 现在仅在目标 release 支持 worker 时才启用 worker，回滚到旧 release 时禁用 worker，[smoke-check.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/smoke-check.sh) 现在在当前 release 支持 worker 时检查 worker 的 systemd 活动。
- 在 `119.29.182.134` 上执行 Wave 5 远程 broker 上线：`/etc/ielts-vocab/microservices.env` 现已包含 Redis / RabbitMQ 基线，`redis` 与 `rabbitmq-server` 已安装并处于 active，新的 broker 校验、preflight 与 smoke 链路都在部署主机上远程通过。
- 修复 [provision-broker-runtime.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/provision-broker-runtime.sh) 的首次安装 bug：脚本现在在要求 `redis-cli`、`rabbitmqctl`、`rabbitmq-diagnostics` 之前安装 broker 包，使干净远程主机可以成功 bootstrap。
- 新增 Wave 5 远程 broker 上线基线：[provision-postgres.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/provision-postgres.sh) 现在把规范的 `REDIS_*` 与 `RABBITMQ_*` 写入 `/etc/ielts-vocab/microservices.env`，[install-cloud-runtime.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/install-cloud-runtime.sh) 现在安装并启用 `redis` 与 `rabbitmq-server`，[provision-broker-runtime.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/provision-broker-runtime.sh) 现在搭建远程本地主机的 broker 基线，[validate-broker-runtime.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/validate-broker-runtime.sh) 接入远程校验。
- 收紧 Wave 5 broker 校验，让缺失的 broker env 不再被代码默认掩盖：[validate_wave5_broker_runtime.py](/Volumes/code/workspace/products/ielts-vocab/scripts/validate_wave5_broker_runtime.py) 现在要求显式的 broker 设置，[backend/.env.microservices.local](/Volumes/code/workspace/products/ielts-vocab/backend/.env.microservices.local) 现承载本地 Redis / RabbitMQ 基线，远程 [preflight-check.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/preflight-check.sh) 与 [smoke-check.sh](/Volumes/code/workspace/products/ielts-vocab/scripts/cloud-deploy/smoke-check.sh) 在进入 HTTP smoke 路径前先校验 broker env、systemd unit 与运行时连通性。
- 收尾代码侧 Wave 4 存储 / 制品对账工具：共享 `SQLite` scoped-override 重启记录、远程存储演练与回滚证据流、以及 `notes export`、`example-audio`、`word-audio` 的 `OSS` 校验 / 修复 operator 全部已纳入远程 runbook。
- 新增 Wave 5 `notes-service <- learning.wrong_word.updated` consumer 路径：`notes_projected_wrong_words` 现在从事件物化错词事实，`start-microservices.sh` 启动分组的 `notes-domain-worker`，`notes_summary_context_repository` 在 per-user 状态追平后优先使用该 projection。
- 新增 Wave 5 `ai-execution-service <- notes.summary.generated` consumer 路径：`ai_projected_daily_summaries` 现在从事件物化 notes 摘要事实，`start-microservices.sh` 启动分组的 `ai-execution-domain-worker`，`/internal/notes/summaries` 可供 service-auth 读取，AI context 在 `notes-service` 不可用时回退到投影摘要。
- 新增 Wave 5 `ai-execution-service <- learning.wrong_word.updated` consumer 路径：`ai_projected_wrong_words` 现在从事件物化错词事实，`start-microservices.sh` 启动分组的 `ai-execution-domain-worker`，AI 错词读与 `get_wrong_words` 工具在 `learning-core-service` 不可用时回退到该 projection。
- 新增 Wave 5 `notes-service <- ai.prompt_run.completed` consumer 路径：`notes_projected_prompt_runs` 现在从事件物化 AI prompt-run 事实，notes 摘要生成把该 projection 读到一个新的 `当天 AI 使用痕迹` 区段，`start-microservices.sh` 启动分组的 `notes-domain-worker`。
- 新增 Wave 5 `notes-service <- learning.session.logged` consumer 路径：`notes_projected_study_sessions` 现在从事件物化学习会话上下文，`notes_summary_context_repository` 在追平后优先使用该 projection，`start-microservices.sh` 启动分组的 `notes-domain-worker`。
- 新增 Wave 5 `tts.media.generated` 与 `ai.prompt_run.completed` 端到端本地事件流，含 service 拥有的物化表、真实 outbox publisher worker 与 admin projection worker，并在 admin overview 中暴露近期的 prompt-run 与 TTS-media 指标。
- `start-microservices.sh` 现在启动规范分组后的 worker 集合：`core-eventing-worker`、`notes-domain-worker`、`ai-execution-domain-worker`、`admin-ops-domain-worker`。
- 把语音处理从主 Flask app 拆出到 `backend/speech_service.py`，端口 `5001`，并相应更新代理 / 启动流程。
- 在拉取 learning-stats 之前先做 quick-memory 对账，让较新的本地记录先到达后端，再做 dashboard 读。
- 修复 `learning-stats` 与 `learner-profile` 中漏算刚到期词的到期复习时区偏移问题。

## 编码与补丁策略
- 仓库文本文件均按 UTF-8 处理，除非文件本身另有声明。
- 使用 `apply_patch` 之前，先用行号读取精确的目标行，并以附近的干净 ASCII 或稳定代码结构为锚点。
- 当文件出现任何文本损坏时，倾向于重写整段逻辑块，而不是匹配单行可疑内容。
- 在同一区域 `apply_patch` 匹配失败两次，就别再用字面 mojibake 去匹配了。改用干净上下文做锚，或者直接重写整个函数 / 组件 / 文档块。
- 不要在已经出现编码损坏的文件上继续堆叠部分编辑。先恢复 / 重读一份干净基线，再回放预期改动。
- 任何与编码相关的修复完成后，检视 diff，确认文件没有夹带无关的文本损坏。
- 让文本完整性回归保持绿灯：`pytest backend/tests/test_source_text_integrity.py -q`。

## 文件行数护栏
- 跟踪的手编辑文本文件（应用代码、后端代码、测试、脚本、文档、配置）硬上限为 `500` 行。
- `vocabulary_data/**` 与 `pnpm-lock.yaml` 显式豁免，它们是生成数据或 lockfile。
- 历史超长文件在 `scripts/file-line-limit.config.json` 中冻结。它们是临时豁免，**不得**超过记录基线，并应随时间被拆分下来。
- `scripts/check-file-line-limits.mjs` 是执行闸口。出现新的超长文件、基线文件再涨、或者文件降到 `<= 500` 行后基线文件未清理时，它都会失败。
- `frontend/eslint.config.mjs` 对跟踪的 JS/TS 文件同样落 `500` 行上限，同时让超长基线在文件被拆分前临时豁免。
- `.github/workflows/ci.yml` 在前端测试 / 构建前显式跑文件行数脚本与 ESLint，使规则在 CI 而非仅本地被强制。

## 技术栈
- Web：React 19 + TypeScript + Vite
- 移动端：`apps/mobile` 下的 React Native，Android 与 iOS 除非显式选择未来原生拆分，否则同属一个 app
- 共享客户端核心：`packages/app-core`，承载平台无关的 schema、API 客户端、auth / session 契约与练习逻辑
- 样式：SCSS + CSS 变量
- 校验：`frontend/src/lib/schemas.ts` 中的 Zod 运行时 schema
- 后端：Python Flask + SQLite
- 鉴权：JWT + localStorage
- 实时：用于语音的 Socket.IO / WebSocket

## 项目结构
```text
frontend/
- package.json              # 前端 package manifest
- vite.config.ts            # 前端 build / proxy 配置
- vitest.config.ts          # 前端单元测试配置
- playwright.config.ts      # 前端 e2e 配置
- index.html                # Vite HTML 入口
- assets/                   # 静态资源
- src/
  - app/                    # App router 入口
  - components/
    - ui/                   # 基础 UI 组件
    - layout/               # 共享 shell / layout
    - practice/             # 练习特性组件
  - contexts/               # Auth / Settings / Toast / AIChat
  - features/
    - vocabulary/hooks/     # books、words、progress、stats 的数据 hook
    - ai-chat/              # AI 聊天特性
    - speech/               # 语音识别特性
  - hooks/                  # 共享 hook
  - lib/                    # schema、helper、sync 逻辑、格式化
  - styles/                 # 全局与页面 SCSS
 - tests/
   - e2e/                   # Playwright 端到端覆盖

backend/
- app.py                    # :5000 的兼容单体 API
- speech_service.py         # :5001 的兼容语音 Socket.IO 服务
- models.py                 # 数据库模型
- routes/                   # API 路由模块
- services/                 # 后端服务逻辑
- tests/                    # 后端测试

apps/
- gateway-bff/              # :8000 上的规范浏览器入口
- mobile/                   # React Native Android/iOS app

packages/
- app-core/                 # 共享的平台无关 TypeScript 客户端契约与逻辑

services/
- */main.py                 # :8101-8108 上的拆分后端服务
- asr-service/socketio_main.py # :5001 上的规范 Socket.IO 运行时

docs/
- architecture/             # 规范与审计
- governance/               # 产品与 UI 治理日志
- milestone/               # 可持久化的交付快照
- operations/               # runbook 与运维文档
- planning/                 # 设计与实施计划
- logs/submit/              # append-only 提交记录

pnpm-workspace.yaml         # 根 workspace 编排
```

## Zod 校验
- schema 位置：`frontend/src/lib/schemas.ts`
- 校验工具：`frontend/src/lib/validation.ts`
- 表单 hook：`frontend/src/lib/useForm.ts`
- auth、settings、toast、AI chat 与 vocabulary 的 hook 都通过 Zod 驱动的 helper 校验输入或 API 负载。

## 关键功能
1. 鉴权与用户资料管理
2. 词书、章节与进度跟踪
3. 基础练习模式：`smart`、`listening`、`meaning`、`dictation`、`follow`、`radio`、`quickmemory`、`errors`
4. Ebbinghaus 到期复习与错词恢复，直接联动统计与学习者画像
5. 独立的进阶五维 / AI 口语模式族，用于付费或 2.0 推广
6. 引导式学习首页与学习者画像驱动的推荐
7. AI 助手、日记与每日摘要流程
8. 独立的语音识别服务与 TTS 工具链

## 后端 API
- `/api/auth`：register、login、logout、avatar、current user
- `/api/books`：books、chapters、words、progress
- `/api/progress`：旧的按天进度
- `/api/ai`：learning stats、learner profile、quick memory、AI 助手、练习 helper
- `/api/notes`：notes、summaries、exports
- `/api/tts`：TTS 音频与生成状态
- `/api/admin`：admin 能力

## 开发
```bash
# 前端
pnpm install
pnpm dev
pnpm build
pnpm preview
pnpm test:e2e

# 移动端与共享客户端核心
pnpm mobile:typecheck
pnpm mobile:test
pnpm app-core:typecheck
pnpm app-core:test
pnpm verify:clients

# 后端
cd backend
pip install -r requirements.txt

# 规范拆分后端启动
./start-microservices.sh

# 单体兼容回滚演练
./start-monolith-compat.sh

# 一键本地生产形态启动
./start-project.sh
```

## 测试账号
- 专用于本地 / 手工验证的测试账号：用户名 `admin`
- 密码：`admin123456`

## 生产 SSH 访问
- 生产 SSH 连接元数据已经登记在 `backend/.env`；当 Codex 需要远程访问时，先从该文件读 `PROD_SSH_HOST`、`PROD_SSH_USER`、`PROD_SSH_KEY_PATH` 或 `PROD_SSH_PRIVATE_KEY_PATH`，而不是假设本地 shell 没有凭据。
- 把 `backend/.env` 视为敏感：仅用它来解析 SSH host、用户名与本地 key 文件路径，不要把私钥内容或无关密钥回显给用户。
- 推荐的 PowerShell 发现片段：
```powershell
$envPath = 'backend/.env'
$sshKey = (Get-Content $envPath | Where-Object { $_ -match '^PROD_SSH_(PRIVATE_)?KEY_PATH=' } | Select-Object -First 1).Split('=', 2)[1].Trim()
$remoteHost = (Get-Content $envPath | Where-Object { $_ -match '^PROD_SSH_HOST=' } | Select-Object -First 1).Split('=', 2)[1].Trim()
$remoteUser = (Get-Content $envPath | Where-Object { $_ -match '^PROD_SSH_USER=' } | Select-Object -First 1).Split('=', 2)[1].Trim()
ssh -i $sshKey -o StrictHostKeyChecking=accept-new "$remoteUser@$remoteHost" "hostname"
```
- 连上后推荐的生产日志命令：
```bash
sudo journalctl -u 'ielts-service@gateway-bff' -u 'ielts-service@learning-core-service' -u 'ielts-service@ai-execution-service' -n 200 --no-pager
sudo journalctl -u 'ielts-service@catalog-content-service' -n 200 --no-pager
```
- 当浏览器请求只在登录用户上失败时，**先**一起检视 `gateway-bff`、`learning-core-service`、`ai-execution-service`、`catalog-content-service`，再下结论说前端 auth 流有错。

## 远程生产拓扑
1. `https://axiomaticworld.com/` 终结在云端 nginx 入口 `119.29.182.134`
2. nginx 从 `/var/www/ielts-vocab/current` 下的活跃 release 软链提供前端 build
3. nginx 把 `/api/*` 代理到活跃 HTTP slot `gateway-bff` 的 `127.0.0.1:18000` 或 `127.0.0.1:28000`
4. `gateway-bff` 把浏览器 API 流量分发给同 slot 的微服务 `18101-18108` 或 `28101-28108`
5. nginx 把 `/socket.io/*` 直接代理到 ASR Socket.IO `127.0.0.1:5001`

排查域问题时，把上述远程链路视作部署上下文，不要假设有本地隧道介入。

## 本地复现拓扑
1. Vite preview 在 `http://127.0.0.1:3002` 提供浏览器 UI
2. 本地浏览器 API 入口在 `http://127.0.0.1:8000`
3. 拆分后端服务在 `127.0.0.1:8101-8108`
4. 本地 `/socket.io/*` 流量走到 ASR Socket.IO `127.0.0.1:5001`

## 浏览器接口
- `speechSynthesis`：发音播放
- `localStorage`：auth、settings、progress、quick-memory 缓存
- `WebSocket` / Socket.IO：实时语音识别
