# Mobile Visual Resource List

Last updated: 2026-06-04

## Summary

移动端视觉统一不能只替换首页背景或页面横幅。目标是把非首页页面、练习页、弹窗、卡片、列表、输入框、按钮、徽章、小图标全部纳入同一套手绘资源体系，避免出现手绘背景上叠加浏览器式白卡、裸标题、Lucide 图标、默认控件的割裂感。

风格基准：

- 以首页小女孩和书房场景为主风格，不以旧粉色背景或通用卡片为准。
- 参考 `apps/mobile/hyperframes/sticker-library/DESIGN.md`：奶油纸感、暖色、深棕手绘线、柔和阴影。
- PNG 素材不烘焙中文 UI 文案，所有文字和数字由 React Native 渲染。
- 禁止靶子、枪战联想、通用 3D、emoji 风、冷色科技风、浏览器原生卡片感。

## P0 Resource List

### Generated And Accepted

| Resource | Status | Notes |
| --- | --- | --- |
| `ui-screen-paper-bg.png` | accepted | 1536x2732 full-screen paper background; no text, no UI chrome |
| `ui-section-title-plaque.png` | accepted | 900x284 transparent title plaque; clean alpha after tightened crop |
| `ui-card-frame-large.png` | accepted | 1080x1920 paper panel for large content surfaces |
| `ui-card-frame-small.png` | accepted | 900x284 transparent-backed small card surface for rows and shortcuts |

### Global UI Skin

| Resource | Usage | Notes |
| --- | --- | --- |
| `ui-screen-paper-bg.png` | 非首页页面背景 | 替代纯色背景，适配整屏裁切 |
| `ui-section-title-plaque.png` | Section 标题底板 | 替代裸 `Heading` / h2 式标题 |
| `ui-card-frame-large.png` | 大内容卡片 | 透明中心，用于词书、统计、资料卡 |
| `ui-card-frame-small.png` | 小卡片 | 透明中心，用于列表项、快捷入口 |
| `ui-card-frame-compact.png` | 指标卡片 | 用于统计数字、进度摘要 |
| `ui-list-row-frame.png` | 列表行 | 替代普通白色 row |
| `ui-modal-frame.png` | Modal 弹窗 | 统一协议、确认、提示弹窗 |
| `ui-bottom-sheet-frame.png` | 底部 Sheet | 练习范围、模式选择等 |
| `ui-toast-bubble.png` | Toast/状态提示 | 成功、失败、加载提示 |
| `ui-empty-cloud-panel.png` | 空状态文字底板 | 空状态插图下方承载文案 |

### Controls

| Resource | Usage |
| --- | --- |
| `ui-button-primary-frame.png` | 主按钮 |
| `ui-button-secondary-frame.png` | 次按钮 |
| `ui-button-danger-frame.png` | 危险按钮 |
| `ui-icon-button-round.png` | 顶部圆形图标按钮 |
| `ui-input-frame.png` | 普通输入框 |
| `ui-search-input-frame.png` | 搜索框 |
| `ui-chip-frame.png` | 标签/chip |
| `ui-count-badge.png` | 数字徽章 |
| `ui-progress-track.png` | 进度条轨道 |
| `ui-progress-fill-orange.png` | 进度条填充 |

### Functional Icons

替换当前直接使用的 Lucide 图标，全部绘制成同一笔触的小图标：

| Resource | Usage |
| --- | --- |
| `icon-back.png` | 返回 |
| `icon-close.png` | 关闭 |
| `icon-chevron-right.png` | 进入详情 |
| `icon-search.png` | 查词 |
| `icon-ai.png` | AI 助手 |
| `icon-settings.png` | 设置 |
| `icon-check.png` | 成功/确认 |
| `icon-error.png` | 错误/不认识 |
| `icon-mic.png` | 跟读/语音 |
| `icon-volume.png` | 听音 |
| `icon-heart.png` | 收藏 |
| `icon-list.png` | 列表 |
| `icon-slider.png` | 练习设置 |
| `icon-clock.png` | 复习/时间 |
| `icon-chart.png` | 统计 |
| `icon-brain.png` | 掌握度 |
| `icon-sparkle.png` | 智能/推荐 |
| `icon-user.png` | 我的 |
| `icon-lock.png` | 安全 |
| `icon-message.png` | 反馈 |

### Page Heroes

| Resource | Page |
| --- | --- |
| `hero-books-vocab-shelf.png` | 词书页 |
| `hero-errors-word-repair.png` | 错词本 |
| `hero-stats-progress-board.png` | 学习统计 |
| `hero-search-word-window.png` | 全局查词 |
| `hero-journal-study-diary.png` | 学习日志 |
| `hero-exams-ielts-desk.png` | 真题页 |
| `hero-profile-learner-card.png` | 我的页 |
| `hero-custom-book-crafter.png` | 自定义词书 |
| `hero-ai-study-assistant.png` | AI 助手 |
| `hero-feedback-wish-mailbox.png` | 意见反馈 |
| `hero-security-lock-envelope.png` | 账号安全 |

## P1 Resource List

### Business Components

| Resource | Usage |
| --- | --- |
| `word-card-front-frame.png` | 练习单词卡 |
| `word-card-answer-frame.png` | 释义/答案卡 |
| `book-item-frame.png` | 词书列表项 |
| `chapter-item-frame.png` | 章节列表项 |
| `wrong-word-item-frame.png` | 错词列表项 |
| `summary-item-frame.png` | 学习日志卡 |
| `exam-item-frame.png` | 真题列表项 |
| `profile-menu-item-frame.png` | 我的页菜单项 |
| `stat-metric-frame.png` | 统计指标卡 |
| `stat-chart-panel.png` | 图表承载底板 |
| `chat-bubble-ai.png` | AI 回复气泡 |
| `chat-bubble-user.png` | 用户提问气泡 |

### Empty And Feedback States

| Resource | Usage |
| --- | --- |
| `empty-books.png` | 没有词书/章节 |
| `empty-errors.png` | 没有错词 |
| `empty-search.png` | 没有搜索结果 |
| `empty-journal.png` | 没有日志 |
| `empty-exams.png` | 没有真题内容 |
| `empty-ai.png` | AI 初始状态 |
| `empty-feedback.png` | 反馈空/成功状态 |
| `loading-pencil-loop.png` | 加载状态 |
| `success-stamp.png` | 成功反馈 |
| `warning-note.png` | 警告反馈 |

## P2 Resource List

### Decorative Stickers

| Resource | Usage |
| --- | --- |
| `decor-orange-flower.png` | 卡片角落装饰 |
| `decor-leaf-pin.png` | 标签/标题装饰 |
| `decor-pencil-small.png` | 学习类小装饰 |
| `decor-sticky-note.png` | 提示便签 |
| `decor-paperclip.png` | 列表装饰 |
| `decor-star-spark.png` | 推荐/完成态 |
| `decor-corner-ribbon.png` | 卡片角标 |
| `decor-mini-girl-reading.png` | 阅读/词书状态 |
| `decor-mini-girl-thinking.png` | 思考/AI/错词状态 |
| `decor-mini-girl-celebrate.png` | 完成/统计状态 |

## Drawing Rules

- 页面 hero 建议 `1200x520`，透明 PNG，移动端显示约 `330-360w x 145-170h`。
- 卡片、弹窗、按钮框架必须中间留空，不画死真实内容。
- 小图标建议 `256x256` 或 `360x360`，透明背景。
- 列表、卡片、弹窗素材要允许九宫格或 `ImageBackground` 拉伸，不因内容长度变形。
- 词书页可以使用词卡/书架，但导航、练习模式、其他页面不要重复书本语素。
- 素材命名进入 `apps/mobile/src/assets/stickers/` 后同步登记到 sticker catalog。
- 所有资源必须避免内置中文 UI 文案、品牌水印、乱码拟文案和不可本地化文本。

## Implementation Notes

- 资源接入点优先统一到 `apps/mobile/src/components/stickers/catalog.ts`、`sources.ts`、`presets.ts`。
- 基础组件层需要同步改造：`Card`、`Heading`、`PrimaryButton`、`Field`、`Pill`、Modal、Sheet、ListRow、IconButton。
- 页面层只消费统一皮肤组件，避免每个 screen 继续手写白卡、裸标题、边框和阴影。
- 现有首页和练习选择页素材先保留，不作为第一轮重绘对象。
- 第一轮落地应先覆盖 P0 资源，再逐页替换 P1 内容卡片和 P2 装饰。

## Acceptance Checklist

- 非首页页面不再直接露出旧粉色背景。
- 主要内容区域没有浏览器式白卡或默认 row。
- 标题区没有裸 `Heading` / h2 式文本块。
- 功能按钮不直接显示 Lucide 原始线性图标。
- Modal、Sheet、Toast 与首页手绘风格一致。
- 数字、标题、说明文字仍由 RN 渲染，可本地化、可动态变化。

## Test Plan

- `pnpm mobile:typecheck`
- `pnpm mobile:test`
- Android emulator smoke：检查首页、词书、练习、错词、统计、搜索、AI、日志、真题、我的页。
- 视觉验收重点：无裸白卡、无裸 h2 风格标题、无未替换 Lucide 功能图标、弹窗和底部 Sheet 与首页手绘风格一致。
