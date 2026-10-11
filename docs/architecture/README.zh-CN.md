# 架构文档

本目录用于存放描述系统结构本身的文档。

## 子目录

- `audits/`：结构风险评审、技术债务评审与架构评估
- `specs/`：已实现或计划中系统的技术设计文档
- `specs/templates/`：可复用的架构规范模板

## 规则

- 一份规范只承载一个技术主题。
- 不要在本目录放置计划类内容；执行计划请放入 `docs/planning/`。
- 当实现发生重大设计变更时，请同步更新对应的规范。
- 新建规范请从 `specs/templates/architecture-spec-template.md` 起步。

## 当前规范

- `Architecture.md`：完整的系统架构总览 — 微服务拓扑、服务间通信、代码分层、数据库、前端架构、部署架构和迁移状态。
- `backend-layered-architecture.md`：后端分层、能力模块、数据流与依赖规则。
- `frontend-boundaries.md`：Web、移动端与共享 client-core 的前端架构边界规则。
- `multi-client-monorepo.md`：针对 Web、移动端以及未来小程序端的 monorepo、应用边界、共享包与提交规则。
- `service-ownership-matrix.md`：首版权威写权限归属与服务拆分矩阵。
- `service-table-boundary-audit.md`：Wave 4 表级归属审计，包含只读与过渡期共享访问。
- `gateway-service-contracts.md`：首轮抽取阶段的网关到服务契约骨架。
- `specs/2026-05-05-practice-mode-data-flow-roadmap.md`：练习模式、复习模式、小游戏、进度、掌握度、会话、统计与 todo 的数据流路线图。
