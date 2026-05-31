# luo 学习进度修复记录

- 执行日期：2026-05-15 Asia/Shanghai
- 目标用户：`luo`（生产 `user_id=3`）
- 执行边界：只修 `luo`；不删除 legacy 错词章节；生产 SSH 直连并禁用代理链路。

## 变更口径

- `book_id=''` 且 `chapter_id=''` 的 ledger/session 视为 user-scope，不再算章节漂移。
- `local_storage_migration_*` 迁移标记不再进入实践模式或学习模式。
- `quickmemory` 和 session-only 证据在 backfill 时补写章节 snapshot：`current_index`、`words_learned`、`is_completed`。
- `wrong_words_{user_id}` 以系统 A-Z 章节作为 canonical 完成口径；legacy 章节只作为 P2 历史残留。
- game mastery 不参与普通章节完成度判断。

## 生产执行结果

第一阶段复用 cutover/backfill/sync 链路：

```text
repair.sessions_checked=186
repair.sessions_repaired=0
backfill.ledger_writes=37321
backfill.rebuilt_scopes=217
purge.user_progress=0
purge.user_book_progress=0
purge.user_chapter_progress=0
purge.user_chapter_mode_progress=0
wrong_word_sync.synced=1
```

第二阶段补写章节 snapshot：

```text
snapshots_written=196
completed_snapshots=137
rebuilt_scopes=196
snapshot_sources.quickmemory=130
snapshot_sources.session=196
```

## 最终审计

最终两次只读复审摘要一致：

```text
books_audited=14
chapters_audited=470
P0=0
P1=0
P2=288
```

错词本专项：

```text
book_id=wrong_words_3
source_rows=3424
source_unique=3410
system_unique=3410
legacy_unique=42
catalog_chapters=27
book_word_count=3410
```

最终报告路径：

- `/tmp/luo-learning-progress-audit-final-p2-20260514T193205Z/luo-learning-progress-audit-20260514T193233Z.json`
- `/tmp/luo-learning-progress-audit-final-repeat-20260514T193312Z/luo-learning-progress-audit-20260514T193337Z.json`

## 剩余 P2

- `catalog_mismatch=1`：`awl_academic` 标称词数和实际词表不一致。
- `ledger_rollup_drift=4` 与 `session_event_drift=237`：历史事件、直接 user/mode scope ledger 与当前 rollup 汇总口径不同，不影响 canonical 完成态。
- `word_context_drift=43`：同一批词在其他词书/章节上下文里学过，不计入当前章节 canonical 完成。
- `unknown_modes_or_books=2`：历史未知 mode/book 证据保留。
- `wrong_word_drift=1`：legacy 错词章节保留为历史内容，不参与默认进度。

## 验证

```text
python -m py_compile ...
pnpm check:file-lines
uv run --with-requirements backend/requirements.txt --with pytest --with oss2 pytest backend/tests/test_learning_activity_backfill_snapshots.py backend/tests/test_learning_activity_rollups.py backend/tests/test_practice_mode_registry.py backend/tests/test_audit_learning_progress.py -q
```

结果：

```text
File line limit check passed.
18 passed
```

备注：`pytest backend/tests/test_source_text_integrity.py -q` 被未跟踪目录 `packages/mac-bridge-mcp/.venv` 内的第三方包文本触发失败；该目录不属于本次变更。
