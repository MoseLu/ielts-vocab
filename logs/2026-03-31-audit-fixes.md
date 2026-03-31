# 2026-03-31 Audit Fixes

## Scope

针对 `docs/project-audit-2026-03-31.md` 中已核实属实的问题，完成本轮定向修复与仓库级验证。

## Fixed

- `A1` 不再向客户端返回邮箱验证码，开发环境仅通过后端日志查看验证码。
- `A2` 新增代理头信任配置，并在 Flask 入口接入 `ProxyFix`，让限流与客户端来源识别可读取转发后的 IP / 协议。
- `A3` 为 AI 工具调用补齐 `get_wrong_words`、`get_chapter_words`、`get_book_chapters` 的参数白名单与校验路径。
- `A4` 修复 `generate_book` 将 LLM 字典响应当作字符串处理导致的类型错误。
- `B1` 修复错词查询工具对不存在 `book_id` 字段的错误过滤，避免运行时异常；收到 `book_id` 时改为安全降级提示。
- `B4` 前端邮箱绑定 / 找回密码文案改为明确提示“开发环境验证码写入后端日志”，避免误导为真实邮件已发送。
- `B7` 新增 GitHub Actions CI，接入前端构建与后端测试。
- `B8` 重写 `playwright.config.ts`，移除本机 Chromium 硬编码路径，并支持自动启动本地前后端。
- `C1` 收紧头像输入校验，仅接受受控的 `data:` 图片或 `http/https` URL，避免任意长文本直接入库。

## Added Tests

- 后端新增 AI 工具与生成词书回归测试。
- 认证测试更新为断言接口不再泄露 `dev_code`。
- 代理链场景下的限流识别新增覆盖。
- 前端学习日志页测试改为使用运行时当天日期，避免生成任务进度断言受固定日期影响。

## Verification

- `pytest backend/tests -q`
- `npm run build`
- `PLAYWRIGHT_SKIP_WEBSERVER=true npx playwright test --list`

以上命令已通过。

## Notes

- `npm test` 在本轮修复前存在一个学习日志页测试与当前日期逻辑不一致的问题，本轮已一并校正，目的是让新增 CI 默认可执行。
