# 本地路由 Web Vitals 报告

- 采样时间：2026/5/5 04:29:41 Asia/Shanghai
- 目标：http://127.0.0.1:3002
- 工具：Playwright Chromium，桌面视口 1365x768，无网络/CPU 节流
- 口径：每个路由 2 次新上下文冷启动采样；LCP/CLS 取中位数，INP 取合成点击/Tab 交互最大值
- 登录态：公共页未登录；受保护页使用本地 admin 用户的一次性 cookie；未修改数据库
- 动态数据：发现主题 8 个，使用 themeId=study-campus；发现考试 0 个，/exams/:paperId 使用占位 /exams/1?section=reading
- 代表路由：/practice 使用 ielts_reading_premium chapter=1；/practice/confusable 使用 ielts_confusable_match chapter=1

## 结论

- 所有采样路由 LCP 均在 good 阈值内。
- CLS 有风险路由 11 个：/stats 0.127；/errors 0.109；/ 0.109；/plan 0.109；/books 0.109；/books/create 0.109；/exams 0.109；/profile 0.109；/vocab-test 0.109；/admin 0.109；/journal 0.109
- 合成交互下所有采样路由 INP 均在 good 阈值内。
- 有 4 个路由采样期间出现 4xx/5xx、请求失败或 console error，详见下方“异常记录”。

## 路由明细

| Route | Sample URL | Final URL | LCP | CLS | INP | LCP node | 状态 |
|---|---|---|---:|---:|---:|---|---|
| /login | /login | /login | 72 ms | 0.000 | 176 ms |  | good / good / good |
| /register | /register | /register | 84 ms | 0.000 | 80 ms |  | good / good / good |
| /forgot-password | /forgot-password | /forgot-password | 76 ms | 0.000 | 80 ms |  | good / good / good |
| /terms | /terms | /terms | 392 ms | 0.000 | 48 ms | p | good / good / good |
| /404 | /404 | /404 | 388 ms | 0.000 | 40 ms | span.not-found-code | good / good / good |
| / | / | /plan | 192 ms | 0.109 | 80 ms | span.study-todo-subtitle | good / needs-improvement / good |
| /plan | /plan | /plan | 488 ms | 0.109 | 40 ms | span.study-todo-subtitle | good / needs-improvement / good |
| /books | /books | /books | 440 ms | 0.109 | 88 ms | span.vb-card-desc | good / needs-improvement / good |
| /books/create | /books/create | /books/create | 400 ms | 0.109 | 32 ms | h1 | good / needs-improvement / good |
| /practice | /practice?book=ielts_reading_premium&chapter=1&mode=smart | /practice?book=ielts_reading_premium&chapter=1&mode=smart | 144 ms | 0.000 | 152 ms | span.word-meaning-group__text | good / good / good |
| /game | /game | /game | 100 ms | 0.000 | 80 ms | p.loading-text | good / good / good |
| /game/themes | /game/themes | /game/themes | 412 ms | 0.000 | 72 ms | h1 | good / good / good |
| /game/themes/:themeId | /game/themes/study-campus | /game/themes/study-campus | 96 ms | 0.000 | 64 ms | p.loading-text | good / good / good |
| /game/themes/:themeId/mission | /game/themes/study-campus/mission | /game/themes/study-campus/mission | 436 ms | 0.000 | 72 ms | strong | good / good / good |
| /game/mission | /game/mission | /game/mission | 732 ms | 0.000 | 72 ms | strong | good / good / good |
| /practice/confusable | /practice/confusable?book=ielts_confusable_match&chapter=1 | /practice/confusable?book=ielts_confusable_match&chapter=1 | 440 ms | 0.000 | 96 ms | p | good / good / good |
| /exams | /exams | /exams | 412 ms | 0.109 | 32 ms | div.empty-state-description | good / needs-improvement / good |
| /exams/:paperId | /exams/1?section=reading | /exams/1?section=reading | 408 ms | 0.000 | 80 ms | div.empty-state-description | good / good / good |
| /errors | /errors | /errors | 428 ms | 0.109 | 40 ms | span.errors-faq-question-text | good / needs-improvement / good |
| /stats | /stats | /stats | 412 ms | 0.127 | 56 ms | p.stats-section-hint | good / needs-improvement / good |
| /profile | /profile | /profile | 400 ms | 0.109 | 32 ms | img.profile-avatar-img | good / needs-improvement / good |
| /speaking | /speaking | /game | 100 ms | 0.038 | 80 ms | p.loading-text | good / good / good |
| /vocab-test | /vocab-test | /vocab-test | 412 ms | 0.109 | 56 ms | span | good / needs-improvement / good |
| /admin | /admin | /admin | 436 ms | 0.109 | 24 ms | div.admin-stat-value.admin-stat-value--amber | good / needs-improvement / good |
| /journal | /journal | /journal | 408 ms | 0.109 | 32 ms | p | good / needs-improvement / good |
| * | /__missing_local_route__ | /404 | 84 ms | 0.000 | 72 ms | span.not-found-code | good / good / good |

## 异常记录

- /practice: badResponses=0, failedRequests=8, consoleErrors=0
  - failed /api/tts/word-audio?w=according&cache_only=1 net::ERR_ABORTED
  - failed /api/tts/word-audio?w=understanding&cache_only=1 net::ERR_ABORTED
  - failed /api/tts/word-audio?w=allow&cache_only=1 net::ERR_ABORTED
  - failed /api/tts/word-audio?w=activities&cache_only=1 net::ERR_ABORTED
  - failed /api/tts/word-audio?w=according&cache_only=1 net::ERR_ABORTED
- /game/themes: badResponses=0, failedRequests=18, consoleErrors=0
  - failed https://axi-shared-public-47fe2a1c6e.oss-cn-hangzhou.aliyuncs.com/projects/ielts-vocab/game-assets/campaign-v2/themes/environment-nature/desktop/select-card.png net::ERR_BLOCKED_BY_ORB
  - failed https://axi-shared-public-47fe2a1c6e.oss-cn-hangzhou.aliyuncs.com/projects/ielts-vocab/game-assets/campaign-v2/themes/science-tech/desktop/select-card.png net::ERR_BLOCKED_BY_ORB
  - failed https://axi-shared-public-47fe2a1c6e.oss-cn-hangzhou.aliyuncs.com/projects/ielts-vocab/game-assets/campaign-v2/themes/society-culture/desktop/select-card.png net::ERR_BLOCKED_BY_ORB
  - failed https://axi-shared-public-47fe2a1c6e.oss-cn-hangzhou.aliyuncs.com/projects/ielts-vocab/game-assets/campaign-v2/themes/study-campus/desktop/map.png net::ERR_BLOCKED_BY_ORB
  - failed https://axi-shared-public-47fe2a1c6e.oss-cn-hangzhou.aliyuncs.com/projects/ielts-vocab/game-assets/campaign-v2/themes/work-business/desktop/select-card.png net::ERR_BLOCKED_BY_ORB
- /exams/:paperId: badResponses=2, failedRequests=0, consoleErrors=2
  - 404 /api/exams/1
  - console Failed to load resource: the server responded with a status of 404 (Not Found)
  - 404 /api/exams/1
  - console Failed to load resource: the server responded with a status of 404 (Not Found)
- /vocab-test: badResponses=0, failedRequests=2, consoleErrors=0
  - failed /api/tts/word-audio?w=east&cache_only=1 net::ERR_ABORTED
  - failed /api/tts/word-audio?w=east&cache_only=1 net::ERR_ABORTED

## 原始数据

- JSON: /Volumes/code/projects/projects/ielts-vocab/docs/logs/performance/local-web-vitals-20260504T202910Z.json
