# IELTS Vocabulary

> 文档编号：PRD-IELTS-VOCAB　层级：L2 项目 PRD
> 文档状态：Active（promoted AXI product）
> Owner：AxiomaticWorld solo owner（libu）　创建：2026-06-07　最后更新：2026-09-25
> 所属产品线：Axi Spun-out Product（axiomaticworld.com 旗下独立产品）
> 上层文档：[`01-AxiomaticWorld-Personal-OS-PRD.md`](../../docs/prd/01-AxiomaticWorld-Personal-OS-PRD.md)
> 受众：维护者 / 接手的 agent / dev / prod 运维 / 用户（雅思备考者）

## 1. 一句话定位

IELTS Vocabulary 是 **雅思词汇学习全栈产品**：Web（frontend/）+ React Native mobile（apps/mobile/）+ 共享 TypeScript 客户端核心（packages/app-core/）+ 后端（backend/，含兼容 monolith + services/ 微服务）+ 边缘网关（apps/gateway-bff/），配 ASR / TTS / 语音 / 笔记 / 管理运维。

### 1.1 它是什么 / 不是什么（边界）

| 它是 | 它不是 |
|---|---|
| 全栈雅思词汇学习产品（Web + Mobile + 共享核心 + 后端） | 通用英语学习平台（专攻雅思词汇） |
| split backend（identity / learning / catalog / ai / notes / tts / asr / admin）+ gateway-bff + 兼容 monolith | 单体 Flask monolith（已拆分；monolith 仅作兼容与回滚） |
| 生产级本地启动 `start-project.sh` + readiness checks | demo / 教学示例 |

## 2. 背景与问题

- 雅思词汇备考需要 Web 端刷词 + Mobile 端离线复习 + 真实语音评测（ASR 实时 + TTS 后端），单一 monolith 难以承载多端 + 多协议。
- split backend（identity / learning / catalog / ai / notes / tts / asr / admin-ops）已落地，但需要 gateway-bff 屏蔽内部分裂、保留兼容 monolith 作为回滚通道。
- 不解决会怎样：跨端数据不同步、ASR/TTS 走第三方昂贵且延迟高、产品稳定性无法保证。

## 3. 用户与核心场景

- **用户**：雅思备考者（Web + Mobile）；owner / dev 维护者。

| 场景 | 描述 | 频率 / 重要性 |
|---|---|---|
| Web 端刷词 | frontend :3002 → gateway-bff :8000 → split services :8101-8108 | 日常 |
| Mobile 离线复习 | apps/mobile → gateway-bff（共享 backend 协议） | 日常 |
| ASR 实时评测 | 前端录音 → ASR Socket.IO :5001 → AI / catalog 服务 | 评测高频 |
| TTS 单词发音 | TTS 后端 (Azure / Volcengine) | 评测高频 |
| 笔记 | notes 服务 | 周期 |
| 管理员运维 | admin-ops 服务 + Redis + RabbitMQ | 周期 |

## 4. 目标与非目标

- **目标 G1**：成为 owner 雅思词汇产品的**唯一全栈入口**；264/264 测试全绿（Phase 5）。
- **目标 G2**：split backend 稳定运行；gateway-bff 是浏览器 API 唯一入口；兼容 monolith 保留作为回滚通道。
- **目标 G3**：生产级本地启动 `start-project.sh` 含 readiness checks；ASR Socket.IO 实时通道稳定。
- **非目标 N1**：不做通用英语学习 / 语法 / 写作；专攻词汇。
- **非目标 N2**：不替代第三方 ASR / TTS（仍走 Azure / Volcengine）；不离开微信生态。
- **非目标 N3**：不做端到端加密；TLS 即可。

## 5. 功能需求（FR）

| ID | 需求陈述 | 优先级 | 对应验收 |
|---|---|---|---|
| FR-1 | 系统应提供 Web frontend（React + Vite，端口 3002）+ pnpm build + tsc | P0 | AC-1 |
| FR-2 | 系统应提供 React Native mobile 客户端（apps/mobile） | P0 | AC-2 |
| FR-3 | 系统应提供共享 TypeScript 客户端核心（packages/app-core） | P0 | AC-3 |
| FR-4 | 系统应提供 split backend：identity / learning / catalog / ai / notes / tts / asr / admin-ops（端口 8101-8108） | P0 | AC-4 |
| FR-5 | 系统应提供 gateway-bff（端口 8000）作为浏览器唯一 API 入口 | P0 | AC-5 |
| FR-6 | 系统应保留兼容 monolith backend/app.py 作为回滚通道 | P0 | AC-6 |
| FR-7 | 系统应提供 ASR Socket.IO（端口 5001）实时通道 | P0 | AC-7 |
| FR-8 | 系统应提供 `start-project.sh` 生产级本地启动 + readiness checks | P0 | AC-8 |
| FR-9 | 系统应 Phase 5 264/264 测试全绿 | P0 | AC-9 |

## 6. 架构与数据模型

### 6.1 结构 / 模块划分

```
products/ielts-vocab/
├── frontend/                       # Web (React + Vite)
├── apps/mobile/                    # React Native mobile
├── apps/gateway-bff/               # 浏览器唯一 API 入口
├── packages/app-core/              # 共享 TypeScript 客户端核心
├── packages/platform-sdk/platform_sdk/asr_runtime
├── backend/app.py                  # 兼容 monolith（保留回滚）
├── backend/services/asr_service.py
├── services/                       # split backend
│   ├── identity-service/
│   ├── learning-core-service/
│   ├── catalog-content-service/
│   ├── ai-execution-service/
│   ├── notes-service/
│   ├── tts-media-service/
│   ├── asr-service/                # main.py
│   ├── asr-socketio/               # 实时通道
│   └── admin-ops-service/
├── vocabulary_data/                # 词库 / 释义 / 例句
├── docs/                           # 架构 + governance + state + planning
├── scripts/setup-mac-runtime.sh
└── start-project.sh                # 生产级本地启动
```

### 6.2 核心对象

词库（vocabulary_data）、用户档案、学习进度、笔记、ASR 会话；持久化 PostgreSQL + Redis 缓存 + RabbitMQ 异步任务。

## 7. 对外契约与依赖

- **Provides**：`ielts-learning-app`, `upload-asr-api`, `realtime-asr-socket`, `tts-backend`
- **Consumes**：`ai-capability`, `minimax-tokenplan`, `ollama-local`
- **关键契约文档**：`AGENTS.md`, `packages/platform-sdk/platform_sdk/asr_runtime`, `backend/services/asr_service.py`, `services/asr-service/main.py`
- **被谁消费 / 影响面**：雅思备考用户（Web + Mobile）；改 split 边界 / 改 ASR 协议 = 改 gateway-bff 路由；需先跑 `workspace-project consumers ielts-vocab`。

## 8. 关键决策（指向 ADR）

| 决策 | 摘要 | ADR |
|---|---|---|
| split backend + gateway-bff + 兼容 monolith | monolith 保留回滚；split 是常态 | （待发） |
| ASR Socket.IO 实时通道 | 优于轮询；前端实时反馈 | （待发） |
| 共享 TypeScript 客户端核心 packages/app-core | 避免 Web/Mobile 重复实现 | （待发） |
| 走 Azure / Volcengine TTS | 不自研；产品聚焦词汇 | （待发） |
| 微信小程序入口 | 复用微信生态；登录走 WECHAT_MOBILE_APP_SECRET | （待发） |

## 9. 验收标准（AC）

- **AC-1**：`pnpm --dir frontend build` exit 0；`pnpm --dir frontend tsc` 0 错误。
- **AC-2**：`apps/mobile` README 启动说明可执行；冷启动无白屏。
- **AC-3**：`packages/app-core` 单测全绿；可被 frontend + mobile 共享导入。
- **AC-4**：split 8 服务各自健康检查 `curl --fail http://127.0.0.1:8101-8108/health` 全绿。
- **AC-5**：`curl --fail http://127.0.0.1:8000/health` exit 0；浏览器访问 :3002 走 gateway-bff 不报错。
- **AC-6**：`backend/app.py` 兼容路径可启动；与 split 并存时由 gateway-bff 路由隔离。
- **AC-7**：ASR Socket.IO :5001 连接成功；前端录音 → 实时返回。
- **AC-8**：`./start-project.sh` 完成所有 readiness check；打印"ready"。
- **AC-9**：Phase 5 264/264 测试全绿（用户记忆）；owner 重新跑确认。

## 10. 验证命令

```bash
# Setup
./scripts/setup-mac-runtime.sh && pnpm install

# Start (生产级本地启动)
./start-project.sh

# Health
curl --fail http://127.0.0.1:8000/health

# Verify
pnpm --dir frontend verify:repo-guards

# Backend
pytest products/ielts-vocab/backend/tests

# 工作区级
node /Volumes/code/workspace/scripts/workspace-project validate
```

## 11. 未决问题（Open Questions / Unknowns）

- 视觉回归覆盖未建立；`Known failure` 已在 HANDOFF 记录。
- 最终远程发布 + bounded storage drill 待 owner 排期。
- 内部客户端 no-proxy 路径需要持续维护（防 `HTTP_PROXY` 泄漏）。

## 12. 当前状态与路线图

- **当前进度**：Phase 5 264/264 测试全绿（用户记忆）；`status: verified`；最近 verify 2026-08-23。
- **里程碑**：见 `docs/project-audit-2026-03-31.md`。
- **下一步**：
  1. 完成最终远程发布 + bounded storage drill + closeout 文档。
  2. 建立视觉回归覆盖（frontend components）。
  3. 维护 no-proxy 内部客户端回归。

## 13. 变更记录

| 日期 | 变更 | Owner |
|---|---|---|
| 2026-06-07 | 项目首版（Web + Mobile + 后端） | libu |
| 2026-06-18 | Manifest v2 迁移 | libu |
| 2026-08-22 | 上次 verify | libu |
| 2026-08-23 | Manifest v2 path-fix-up（移除不存在的 PRD.md / TDD.md / root TODO.md / root MILESTONE.md） | governance auto-remediation |
| 2026-09-24 | ahead-batch 快照（5 commits ahead of origin/dev） | libu |
| 2026-09-25 | 升级为正式 PRD（原 stub 由 audit-remediation 2026-09-25 生成） | libu |
