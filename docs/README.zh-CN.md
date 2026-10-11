# 文档架构
最后更新：2026-04-19 00:00:00 +08:00

本目录是项目的持久化文档层。

请用它承载那些在多次会话、多位贡献者以及未来功能开发中都需要长期有用的资料。未经挑选目标域目录就往 `docs/` 里丢随手笔记是不合适的。

## 结构

```text
docs/
- README.md                        # 本索引与归位规则
- agents/                          # 局部需要时使用的子级 AGENTS/索引文档
- architecture/
  - audits/                        # 架构与风险审计
  - specs/                         # 技术设计规范
- governance/                      # 产品与 UI 治理日志
- milestone/                      # 跨发布里程碑与完成快照
- operations/                      # 工具、自动化与运维运行手册
- planning/
  - implementation/                # 具体实施计划
- todo/                            # 根 TODO 需要细分时的子级 TODO 分解
- logs/
  - submit/                        # 仅追加的提交记录
```

## 归位规则

- 长寿命的技术决策放入 `architecture/specs/`。
- 仅当根级 `AGENTS.md` 会过于冗长时，才在 `agents/` 下放置子级范围说明。
- 结构或风险评审放入 `architecture/audits/`。
- 工具配置与运维运行手册放入 `operations/`。
- 产品需求基线、阶段性功能规划与上线检查表放入 `planning/`。
- 治理历史与跨领域 UI 清理日志放入 `governance/`。
- 跨功能交付检查点与发布快照放入 `milestone/`。
- 当根 TODO 中某条目需要独立检查表时，将其子级任务分解放入 `todo/`。
- 仅追加的执行记录放入 `logs/submit/`。

## 命名规则

- 优先使用小写 kebab-case 形式的文件名。
- 当时间顺序重要时使用日期前缀。
- 一份文档只承载一个主题。
- 把计划、规范与执行历史拆分到独立文件，而非混在同一篇笔记中。

## 当前索引

### 架构

- [architecture-audit.md](./architecture/audits/architecture-audit.md)
- [multi-client-monorepo.md](./architecture/multi-client-monorepo.md)
- [2026-03-28-tts-batch-generation-design.md](./architecture/specs/2026-03-28-tts-batch-generation-design.md)
- [architecture-spec-template.md](./architecture/specs/templates/architecture-spec-template.md)

### 治理

- [ui-governance-log.md](./governance/ui-governance-log.md)

### 里程碑

- [README.md](./milestone/README.md)
- [2026-q1-platform-foundation.md](./milestone/2026-q1-platform-foundation.md)
- [milestone-template.md](./milestone/templates/milestone-template.md)

### 运维

- [agent-browser-guide.md](./operations/agent-browser-guide.md)
- [release-closeout-checklist.md](./operations/release-closeout-checklist.md)
- [frontend-automation-setup.md](./operations/frontend-automation-setup.md)

### 规划

- [product-requirements-document.md](./planning/product-requirements-document.md)
- [ui-redesign-plan.md](./planning/ui-redesign-plan.md)
- [2026-03-28-tts-batch-generation-plan.md](./planning/implementation/2026-03-28-tts-batch-generation-plan.md)
- [implementation-plan-template.md](./planning/implementation/templates/implementation-plan-template.md)

### 日志

- [20260331-084123-batch-submit.md](./logs/submit/20260331-084123-batch-submit.md)
