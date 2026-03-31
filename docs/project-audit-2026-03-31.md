# IELTS Vocabulary App 全面审计报告

审计日期：2026-03-31

## 1. 审计范围与方法

本次审计覆盖以下维度：

- 项目成熟度与工程治理
- 安全性与权限边界
- 用户体验与产品一致性
- 健壮性、稳定性与可运维性
- 测试体系与发布可靠性

本次审计基于代码静态审查完成，主要证据来自仓库 `dev` 分支源码，包括前端 React/Vite、后端 Flask/SQLite、测试目录与部署配置。

本次审计未完成本地运行验证。原因是本会话中的本地 shell 执行器异常，无法直接在当前工作树运行 `build`、`test`、`pytest`、`playwright` 等命令。因此，本文结论以源码级证据为主。如果本地工作树存在未推送改动，本文可能无法覆盖那部分差异。

## 2. 总体结论

这是一个功能密度较高、业务意图明确、已经具备一定产品雏形的项目，但距离“成熟可控、可稳定上线”的状态还有明显差距。

优势在于：

- 前端大量使用 Zod 做运行时校验，基础数据防线比普通原型项目更强。
- 认证体系已经从“裸 token”演进到 HttpOnly Cookie、刷新令牌、撤销表、基础限流，方向是对的。
- 前后端都有成规模测试文件，说明团队已有质量意识，而不是纯堆功能。
- 学习画像、AI 助教、统计、错词、词书、TTS 等能力已经形成产品闭环。

核心问题在于：

- 生产安全边界仍有明显破口，最严重的是验证码直接回传客户端。
- 若按当前本地代理链部署，限流与风控很可能失真，甚至把所有用户串成同一个 IP。
- AI 侧承诺的若干关键工具实际上处于“代码写了但跑不通”的状态。
- 若干对外功能已经挂上 UI，但从源码看并未真正达到可用级别。
- 工程治理与运维自动化不足，CI、文档、环境适配、发布验证链路都偏弱。

## 3. 维度评分

| 维度 | 结论 | 评分 |
| --- | --- | --- |
| 安全性 | 有正确方向，但存在可直接利用的高风险缺陷 | 4/10 |
| 成熟度 | 功能丰富，但工程治理与产品完成度不稳定 | 6/10 |
| 用户体验 | 主流程和界面投入较多，但若干功能与真实能力不一致 | 7/10 |
| 健壮性 | 有校验与兜底，但跨模块一致性不足 | 5/10 |
| 稳定性 | 单机可跑，规模和异常场景下风险较高 | 5/10 |
| 可运维性 | 文档、CI、环境抽象和部署约束仍偏弱 | 4/10 |

## 4. 关键问题清单

### A. 严重问题

#### A1. 验证码直接回传客户端，账号接管门槛极低

严重级别：Critical

证据位置：

- `backend/routes/auth.py::send_bind_email_code()`
- `backend/routes/auth.py::forgot_password()`
- `backend/tests/test_auth.py::TestSendCode.test_send_code_success`
- `backend/tests/test_auth.py::TestForgotPassword.test_forgot_password_known_user`

问题说明：

- 绑定邮箱接口直接返回 `dev_code`
- 忘记密码接口也直接返回 `dev_code`
- 测试用例还显式断言该字段必须存在，说明这不是临时调试残留，而是当前系统行为的一部分

影响：

- 任意拿到会话的人都能直接完成邮箱绑定或密码重置
- 即便用户收不到真实邮件，只要接口可调用，验证码就已经泄露给前端
- 这是标准的认证闭环失效，属于上线前必须清零的问题

建议：

- 生产环境彻底移除 `dev_code`
- 仅在显式 `DEBUG=true` 且本地环境下允许开发回显
- 为邮箱验证码流程增加环境开关和集成测试，确保生产分支永不回传验证码

#### A2. 代理链部署下，登录限流极可能失真或误伤全体用户

严重级别：High

证据位置：

- `backend/routes/auth.py::_check_rate_limit()`
- `backend/routes/auth.py::login()`
- `backend/routes/auth.py::forgot_password()`
- `backend/routes/auth.py::send_bind_email_code()`
- `backend/app.py`
- `nginx.conf.example`

问题说明：

- 限流完全依赖 `request.remote_addr`
- `nginx.conf.example` 已经在反向代理里传了 `X-Forwarded-For`
- 但 Flask 侧没有看到任何 `ProxyFix`、可信代理解析或显式的来源 IP 还原
- 在 `natapp -> nginx -> Flask` 的链路里，后端很可能只能看到 `127.0.0.1`

影响：

- 所有外部用户可能共用一个限流桶
- 某个用户输错密码过多，可能把整站真实用户一起锁住
- 反过来，风控日志里的来源 IP 也失真，后续审计与封禁都不可靠

建议：

- 在 Flask 入口明确接入 `werkzeug.middleware.proxy_fix.ProxyFix`
- 只在受信代理链下开启转发头解析
- 为登录、找回密码、发码接口补充“代理模式下真实 IP 识别”的集成测试

#### A3. AI 宣称可用的关键工具实际上被输入校验层整体拦死

严重级别：High

证据位置：

- `backend/routes/ai.py::_TOOL_INPUT_SCHEMA`
- `backend/routes/ai.py::_validate_tool_input()`
- `backend/routes/ai.py::_chat_with_tools()`
- `backend/routes/ai.py::ask()`

问题说明：

- 系统 prompt 明确要求 AI 调用 `get_wrong_words`、`get_chapter_words`、`get_book_chapters`
- 但白名单 `_TOOL_INPUT_SCHEMA` 只定义了 `web_search` 和 `remember_user_note`
- 对未登记工具，`_validate_tool_input()` 直接返回 `None`
- 结果是这三个工具虽然有 handler，但永远会在执行前被判定为“校验失败”

影响：

- AI 助教无法真正读取错词、章节和词书结构
- 用户看到的是“看起来懂业务”的 AI，实际上大量回答只能靠模型猜
- 这会直接削弱学习计划、错词复习、章节规划等核心产品价值

建议：

- 把三个工具补进 `_TOOL_INPUT_SCHEMA`
- 给每个工具增加单元测试，覆盖“模型请求 -> 参数校验 -> handler 执行 -> tool_result 回注”全链路

#### A4. 自定义词书生成接口从源码看大概率不可用

严重级别：High

证据位置：

- `backend/routes/ai.py::generate_book()`
- `backend/services/llm.py::chat()`

问题说明：

- `chat()` 返回的是字典结构，如 `{"type": "text", "text": "..."}`
- `generate_book()` 却把 `raw = chat(...)` 当作字符串直接传入 `re.search(...)`
- 这会触发类型错误，而不是正常提取 JSON

影响：

- “AI 生成自定义词书”是一个已挂在产品能力里的卖点，但后端实现与 LLM 返回契约不一致
- 该接口极可能在真实调用时直接 500

建议：

- 先读 `raw.get("text", "")` 再做 JSON 提取
- 为该接口补充最小 happy-path 测试和异常结构测试

### B. 中高优先级问题

#### B1. `get_wrong_words(book_id)` 过滤条件引用了不存在的模型字段

严重级别：Medium

证据位置：

- `backend/routes/ai.py::_make_get_wrong_words()`
- `backend/models.py::class UserWrongWord`

问题说明：

- `UserWrongWord` 模型没有 `book_id` 字段
- 但工具 handler 里却存在 `q.filter_by(book_id=book_id)`

影响：

- 一旦未来把工具白名单修好，这里会继续在运行时抛错
- 说明 AI 相关实现目前存在“看起来闭环，实际上跨模块契约没对齐”的问题

建议：

- 要么给错词表补齐来源维度
- 要么移除 `book_id` 过滤参数，避免虚假能力

#### B2. API 基地址抽象不一致，跨域/代理部署易出隐性故障

严重级别：Medium

证据位置：

- `src/lib/index.ts::buildApiUrl()`
- `src/lib/index.ts::apiFetch()`
- `src/contexts/AuthContext.tsx::logout()`
- `src/features/vocabulary/hooks/useVocabBooks.ts`
- `src/features/vocabulary/hooks/useBookWords.ts`

问题说明：

- 代码里定义了 `VITE_API_URL` 和 `buildApiUrl()`
- 但 `apiFetch()` 实际并不调用 `buildApiUrl()`
- 刷新令牌、退出登录、若干 hooks 仍然直接写死 `/api/...`
- 这使得“可配置 API 基地址”名义上存在，实际上并未贯彻

影响：

- 代理前缀变化、前后端分离部署、预发环境切换时，容易出现局部接口正常、局部接口失败的隐性问题
- 问题会集中出现在登录续期、注销、公开接口等最难排查的位置

建议：

- 统一所有请求走一个 API client
- 删除无效抽象，或者把它真正接通
- 用一条集成测试覆盖 `VITE_API_URL` 非空时的登录、刷新、登出链路

#### B3. 管理员引导方式不够安全，启动日志中会出现高权限密码

严重级别：Medium

证据位置：

- `backend/app.py::_ensure_admin_user()`

问题说明：

- 当未设置 `ADMIN_INITIAL_PASSWORD` 时，系统会自动生成随机密码并打印到标准输出
- 这虽然避免了默认弱密码，但也把高权限凭据暴露给了日志系统、宿主终端或运维转储

影响：

- 在共享日志、容器平台、托管面板等环境中，管理员密码可能被旁路获取

建议：

- 默认不自动创建管理员
- 或只在显式初始化命令中创建，并把密码写到一次性、安全可见的输出渠道

#### B4. 邮箱相关能力仍处于“开发模拟态”，但产品文案按正式能力对外表达

严重级别：Medium

证据位置：

- `backend/routes/auth.py::_send_code_mock()`
- `backend/routes/auth.py::send_bind_email_code()`
- `backend/routes/auth.py::forgot_password()`
- `src/components/AuthPage.tsx`
- `src/components/ProfilePage.tsx`

问题说明：

- 当前发码逻辑只是 `print` 到日志
- 前端却展示“验证码已发送，请查收邮件”“绑定邮箱后可用于找回密码和账号安全验证”
- 产品承诺与实际能力不一致

影响：

- 如果移除 `dev_code` 但不接入真实邮件服务，这两条用户路径会立即不可用
- 当前属于“靠漏洞维持可用性”的状态

建议：

- 二选一：要么接入真实邮件服务，要么在 UI 中明确标注为开发中并临时下线入口

#### B5. 当前后端组合更像单机原型，稳定性天花板明显

严重级别：Medium

证据位置：

- `backend/config.py`
- `backend/app.py`
- `backend/models.py`
- `backend/routes/ai.py`

问题说明：

- 主数据库仍是 SQLite
- AI 对话、学习日志、错词、画像、摘要、撤销令牌、限流桶都共享同一个库
- 还叠加了 Socket.IO、事件协程、后台摘要生成、TTS 任务

影响：

- 单机少量用户场景可接受
- 一旦并发上升，锁竞争、响应抖动、长尾延迟、任务阻塞都会更明显
- WAL 能缓解，但不能把 SQLite 变成真正的多用户服务端数据库

建议：

- 至少把生产目标明确为“单机轻量服务”还是“多人长期使用”
- 若面向真实用户，尽快规划 PostgreSQL/MySQL，并把限流状态迁到 Redis

#### B6. 文档与真实项目状态明显脱节，直接影响维护和交接

严重级别：Medium

证据位置：

- `README.md`
- `package.json`
- `src/`
- `backend/requirements.txt`

问题说明：

- README 仍描述为“原生 HTML + CSS + JavaScript + Vite”
- 目录结构说明也停留在旧版，和当前 React 19 + TypeScript + 大量组件/上下文/特性模块不一致
- 后端安装示例与当前依赖文件也不完全一致

影响：

- 新成员会被误导
- 部署、调试、排障、交接成本显著增加

建议：

- 以当前代码为准重写 README
- 补齐“本地开发、环境变量、测试、部署拓扑、常见故障”说明

#### B7. 缺少 CI 工作流，测试存在但没有强制执行机制

严重级别：Medium

证据位置：

- 仓库树中未见 `.github/workflows/`
- `package.json`
- `backend/tests/`
- `src/**/*.test.tsx`
- `tests/e2e/README.md`

问题说明：

- 项目已有较多前后端测试文件
- 但当前看不到自动化 CI 入口
- 这意味着测试质量高度依赖人工自觉

影响：

- 回归风险高
- 修复旧 bug 时容易引入新问题
- 审计发现的高风险问题很可能在未来再次出现

建议：

- 最少补两条流水线：前端单测 + 后端 pytest
- 第二阶段再接入 Playwright 冒烟测试

#### B8. Playwright 配置对本机环境耦合过重，不利于团队和 CI 复用

严重级别：Medium

证据位置：

- `playwright.config.ts`
- `tests/e2e/README.md`

问题说明：

- Chromium 路径硬编码为 Windows 本地 `LOCALAPPDATA/ms-playwright/chromium-1208/...`
- 没有 `webServer` 配置，要求人工先起前后端
- README 写了可接 CI，但配置本身并未做到真正可移植

影响：

- 换机器、换系统、进 CI 都容易碎
- E2E 很可能长期存在、实际不跑

建议：

- 改为标准 Playwright browser 管理
- 增加 `webServer` 或测试专用启动脚本
- 让本地与 CI 使用同一套入口

### C. 中低优先级问题

#### C1. 头像数据直接以大体积字符串入库，缺少真正的资源治理

严重级别：Low

证据位置：

- `backend/models.py::User.avatar_url`
- `backend/routes/auth.py::update_avatar()`
- `src/components/ProfilePage.tsx`

问题说明：

- 头像字段直接使用文本列
- 后端仅按字符串长度做限制，没有做 MIME、尺寸、压缩、存储位置治理

影响：

- 数据库膨胀
- 前端渲染内存开销不稳定
- 未来迁移 CDN/对象存储时成本更高

建议：

- 头像改为对象存储 URL
- 上传时做真正的文件校验与压缩

#### C2. 客户端本地状态仍承担较多业务责任，服务端与客户端事实源存在分裂

严重级别：Low

证据位置：

- `src/components/HomePage.tsx`
- `src/hooks/useAIChat.ts`
- `src/contexts/AuthContext.tsx`
- `src/contexts/SettingsContext.tsx`

问题说明：

- 词书选择、章节选择、学习计划、模式表现、错词增强数据都较依赖 localStorage
- 后端也在同步其中一部分

影响：

- 多端一致性弱
- 本地污染数据会影响 AI 上下文和统计结果

建议：

- 划清哪些状态必须服务端持久化，哪些只属于本地 UI 偏好

## 5. 测试与质量观察

正向观察：

- `backend/tests/` 已覆盖认证、图书、AI 记忆、笔记、TTS 等多个模块
- `src/` 下也存在较多组件级和 hook 级测试

关键缺口：

- 当前测试把 `dev_code` 回传当成正确行为，这会固化安全漏洞
- 未看到针对 `generate_book()` 的契约测试
- 未看到针对 AI tool 调用白名单的回归测试
- 未看到代理链下真实 IP 识别的集成验证
- 未看到 CI 自动运行这些测试

## 6. 建议整改顺序

### 24 小时内必须完成

1. 移除所有生产路径里的 `dev_code` 回传
2. 修复代理链真实 IP 获取，重做限流验证
3. 修复 AI 工具白名单，打通 `get_wrong_words` / `get_chapter_words` / `get_book_chapters`
4. 修复 `generate_book()` 与 `chat()` 返回契约不一致的问题

### 1 周内应完成

1. 刷新 README、环境变量说明、部署说明
2. 建立最小 CI：前端单测 + 后端 pytest
3. 统一 API client，消除硬编码请求路径
4. 下线或补全邮箱真实发送能力
5. 收敛管理员初始化流程，避免日志输出敏感凭据

### 1 个迭代内建议完成

1. 评估从 SQLite 升级到更适合服务端并发的数据库
2. 为 AI、认证、运维关键路径补齐契约测试与冒烟测试
3. 为 TTS、摘要生成、后台任务加入更清晰的状态与失败观测
4. 统一“前端文案承诺”和“后端实际可用能力”

## 7. 结论

如果把这个项目定位为“功能型原型”或“内部试用版”，它已经具备不错的业务完整度。

如果把它定位为“可对外稳定提供服务的成熟产品”，当前还不够。最优先的阻断项不是 UI，而是认证闭环、代理链风控、AI 工具链可靠性和工程治理自动化。

建议先做一轮“安全与稳定性收口”，再继续叠加新功能。否则后续开发只会在不稳定地基上继续放大复杂度。
