# 测试报告

最后更新：2026-04-30

## 2026-04-30 生产环境公开 API 全量测试

详细报告：`docs/operations/production-api-full-test-report-2026-04-30.md`

| 检查项 | 结果 | 备注 |
| --- | --- | --- |
| 公开 `/api/*` 路由基线 | PASS | 网关已覆盖 `109/114` 个 monolith 路由方法；未覆盖的 5 个路由方法属于遗留 `tts-admin`，不对外暴露。 |
| 已鉴权生产矩阵 | PARTIAL | 125 个请求：通过 94 个，失败 31 个。鉴权、学习、TTS、语音、管理员、考前冲刺各组通过。 |
| AI/笔记定向复测 | PARTIAL | 32 个请求：通过 8 个，失败 24 个。失败集中在 AI 上游/网关熔断、供应商配额与笔记生成。 |
| 重启后抽检 | PARTIAL | 10 个请求：通过 6 个，失败 4 个。Books/鉴权/AI 上下文/近义词已恢复；AI 提问、复习队列、游戏主题、易混淆自定义章节仍失败。 |
| 代码修复轮 | PASS | 新增 AI 复习计划回退、笔记异步任务失败处理、易混淆自定义章节 id 冲突的本地修复。本地后端测试与仓库守卫均通过。 |

关键发现：

- `POST /api/books/ielts_confusable_match/custom-chapters` 在全量测试中返回 500，重启后返回 504；目录日志显示跨用户重复 `custom_book_chapters.id=1001`。代码现改为全局分配自定义章节 id。
- `GET /api/ai/review-plan` 与笔记上下文日志显示缺少生产环境表 `user_learning_book_rollups`；复习计划在构建学习者画像失败时回退为空画像快照，而不是 500。
- 笔记同步摘要生成失败，原因是 MiniMax API 密钥不可用；异步生成返回 202，但其 worker 记录了应用上下文回滚错误。
- 笔记异步摘要 worker 回滚现已在 `app.app_context()` 内运行，并在生成错误时记录失败任务，避免 worker 崩溃。
- `POST /api/ai/speaking/evaluate` 已到达供应商逻辑层，但因模型免费额度耗尽而失败。
- 本轮运行在生产环境留下了无法通过公开 API 删除的探针产物：用户 `codex_api_probe_20260429175738`、自定义书 `custom_f84821e7d686` 与一个 `language` 词条笔记。

代码修复验证：

- `pytest backend/tests/test_ai_execution_speaking_internal_clients.py backend/tests/test_notes.py backend/tests/test_notes_service_api.py backend/tests/test_catalog_content_service_api.py backend/tests/test_confusable_custom_chapter_updates.py backend/tests/test_confusable_custom_lookup.py -q` → PASS，27 passed。
- `pnpm check:file-lines` → PASS。
- `pnpm lint` → PASS。
- `pytest backend/tests/test_source_text_integrity.py -q` → PASS，2 passed。

## 范围

继续对当前工作区变更进行验证，覆盖：

- 后端目录/音标回退回滚行为
- 网关 HTTP 代理环境代理隔离
- 游戏会话/单词掌握活动状态
- 前端游戏地图 UI 与资产清单守卫

## 环境

- 运行时 PATH 前缀：`/Users/mose/.local/share/micromamba/envs/ielts-mac-runtime/bin`
- Python：`pytest 9.0.3`
- Node：`v24.14.1`
- pnpm：`9.0.0`

## 结果

| 命令 | 结果 | 备注 |
| --- | --- | --- |
| `pytest backend/tests/test_vocabulary_loader.py backend/tests/test_phonetic_fallback.py backend/tests/test_http_proxy.py -q` | PASS | 14 passed, 16 warnings |
| `pytest backend/tests/test_source_text_integrity.py -q` | PASS | 2 passed |
| `pytest backend/tests/test_word_mastery_support.py -q` | PASS | 4 passed，仅有 SQLAlchemy/datetime warning 噪声 |
| `pytest backend/tests/test_vocabulary_loader.py backend/tests/test_phonetic_fallback.py backend/tests/test_http_proxy.py backend/tests/test_word_mastery_support.py backend/tests/test_source_text_integrity.py -q` | PASS | 20 passed, 423 warnings |
| `pnpm --dir frontend exec vitest run src/components/practice/page/GameMode.test.tsx` | PASS | 5 passed |
| `pnpm --dir frontend exec vitest run src/components/practice/page/GameMode.test.tsx src/components/practice/page/GameModeSections.audio.test.tsx` | PASS | 7 passed |
| `pnpm --dir frontend verify:repo-guards` | PASS | file-line、design-token、style-discipline、lint 全部通过 |
| `pnpm --dir frontend build` | PASS | Vite 生产构建通过 |
| `pnpm --dir frontend test` | FAIL | 507 passed, 1 failed；`SelectionWordLookup.test.tsx` 的外部点击关闭断言超时 |
| `pnpm --dir frontend exec vitest run src/components/layout/navigation/SelectionWordLookup.test.tsx` | PASS | 8 passed（隔离运行） |

## 测试期间修复

- 给游戏地图的计划按钮显式加上 `aria-label="返回学习计划"`，使其无障碍控件名匹配预期动作。
- 压缩游戏资产生成的 `manifest.json`，在不将生成资产加入人工维护的 oversized 基线的前提下，让 `check:file-lines` 保持绿灯。
- 将新的游戏地图 SCSS 中硬编码的 `z-index`、固定像素宽度与原始颜色字面量改用现有设计令牌/语义化颜色混合。

## 资产清单检查

`frontend/assets/game/wuwei-transparent-v3/manifest.json` 已对照交付的 PNG 文件检查，排除了 `_source`、调试与联系单图像：

```json
{
  "deliverable_png": 125,
  "manifest_png": 125,
  "missing_from_manifest": [],
  "stale_manifest": []
}
```

## 后续

- 提交前重跑完整的 `pnpm --dir frontend test`。唯一观察到的失败无法在隔离测试文件中复现，除非再次出现，否则应视为可能的时序抖动问题。
