# TODO
Last updated: 2026-04-04 21:09:41 +08:00

## 进行中
- [进行中] 完成首页学习中心首屏视觉清理，并在桌面端和移动端各做一轮 UI 验证。
- [进行中] 持续校准 `start-project`、`nginx`、Vite preview、Flask `:5000` 和 speech service `:5001` 的联动启动与健康检查。

## 待完成
- [待完成] 为 `/favicon.ico` 补齐静态资源或代理处理，避免当前预览链路下继续返回 `404`。
- [待完成] 补回或替换 `scripts/repo_summary.py`，让仓库总结文档可以按固定流程自动同步。
- [待完成] 用真实浏览器再走一轮 LUO 的统计页和去复习链路，确认页面层不再出现旧缓存导致的数字跳变。

## 已完成
- [已完成] 将语音 Socket.IO 服务拆到独立的 `backend/speech_service.py`，并同步更新启动脚本、代理配置和测试覆盖。
- [已完成] 在统计抓取前增加 quick-memory 对账，同步本地更新到后端后再读取学习统计。
- [已完成] 修复 due-review 时间戳换算偏移，统一 `learning-stats`、`learner-profile` 和 `review-queue` 的到期统计口径。
