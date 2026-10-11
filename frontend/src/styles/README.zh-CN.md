# 样式 README

本目录是前端样式的唯一入口。

根入口是:

- [index.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/index.scss)

导入顺序固定且必须保持:

1. `base`
2. `layout`
3. `components`
4. `pages`
5. `utils`

## 目录规则

### `base/`

基础设计令牌、主题变量、reset、排版、间距、圆角、阴影、z-index。

主要文件:

- [base.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/base.scss)

修改时:

- 优先在此处编辑设计令牌。
- 如果可以使用令牌,请勿在页面文件中重新定义全局颜色或间距。

### `layout/`

仅承载全局外壳与导航。

文件:

- [app.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/layout/app.scss)
- [header-base.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/layout/header-base.scss)
- [header-selectors.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/layout/header-selectors.scss)

修改时:

- 在此层处理页面外壳、header、sidebar、底部导航、共享页面容器。
- 不要在此放置特性专属的卡片/表格样式。

### `components/`

可复用的组件样式。

文件:

- [avatar.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/avatar.scss)
- [complete.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/complete.scss)
- [dropdowns.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/dropdowns.scss)
- [empty-state.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/empty-state.scss)
- [global-word-search-detail.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/global-word-search-detail.scss)
- [global-word-search.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/global-word-search.scss)
- [popover.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/popover.scss)
- [scrollbar.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/scrollbar.scss)
- [settings.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/settings.scss)
- [toast.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/toast.scss)
- [ui-primitives.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/components/ui-primitives.scss)

修改时:

- 同一 UI 模式若出现在多个页面,请迁移到此处。
- 组件样式不应感知页面路由上下文。
- button、card、input、modal、global search 等共享 UI 原子应放在此处,而不是写在 TSX 工具字符串或 `layout/` 层。

### `pages/`

页面组合与页面级视觉。

当前文件:

- [admin.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/admin.scss)
- [ai-chat.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/ai-chat.scss)
- [auth.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/auth.scss)
- [chapter-modal.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/chapter-modal.scss)
- [day-card.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/day-card.scss)
- [errors.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/errors.scss)
- [home-banner.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/home-banner.scss)
- [home-sections.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/home-sections.scss)
- [journal.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/journal.scss)
- [plan-modal.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/plan-modal.scss)
- [practice-complete.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/practice-complete.scss)
- [practice-dictation.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/practice-dictation.scss)
- [practice-layout.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/practice-layout.scss)
- [practice-options.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/practice-options.scss)
- [practice-quickmemory.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/practice-quickmemory.scss)
- [practice-radio.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/practice-radio.scss)
- [practice-spelling.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/practice-spelling.scss)
- [practice-wordlist.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/practice-wordlist.scss)
- [profile.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/profile.scss)
- [stats.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/stats.scss)
- [study-center.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/study-center.scss)
- [vocab-book-grid.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/vocab-book-grid.scss)
- [vocab-cards.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/vocab-cards.scss)
- [vocab-filters.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/vocab-filters.scss)
- [vocab-test.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/vocab-test.scss)

修改时:

- 在此层处理仅限页面的布局与视觉。
- 请勿在此重新定义令牌。
- 若某条规则成为通用规则,请迁移到 `components` 或 `layout`。
- 页面 partial 文件名必须描述其承载的切片,例如 `_dashboard-overview.scss`、`_learning-curve.scss`、`_user-detail-modal.scss`。
- 请勿创建 `_part-1.scss`、`_part-2.scss` 之类的匿名顺序命名或类似的非语义编号。

### `utils/`

最后加载的工具层。

文件:

- [\_mixins.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/utils/_mixins.scss)
- [utilities.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/utils/utilities.scss)
- [responsive.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/utils/responsive.scss)

修改时:

- 用于工具类、辅助状态以及响应式覆盖。
- 除非该规则确实全局通用,否则请避免在此处使用特性专属选择器。
- 当相同的 layout/panel/progress 模式在多个页面出现时,把可复用的 SCSS mixin 放在此处。

## 复用优先的 SCSS 规则

在新增页面规则之前,请先确认以下既有 mixin 是否已满足需求:

- `page-stack`
- `page-shell-fill`
- `page-content-fill`
- `panel-surface`
- `toolbar-surface`
- `table-shell`
- `metric-card`
- `data-table-base`
- `data-table-head-cell`
- `data-table-body-cell`
- `control-button`
- `accent-button`
- `input-control`
- `pill-badge`
- `native-progress`
- `flex-center-column`

当前 mixin 入口:

- [\_mixins.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/utils/_mixins.scss)

已使用它们的页面:

- [admin.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/admin.scss)
- [errors.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/errors.scss)
- [journal.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/journal.scss)
- [practice-complete.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/practice-complete.scss)
- [stats.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/stats.scss)
- [study-center.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/study-center.scss)
- [vocab-book-grid.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/vocab-book-grid.scss)
- [vocab-cards.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/pages/vocab-cards.scss)

## 如何找到正确的文件

若你想修改:

- 主题色、间距、圆角、阴影:从 [base.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/base.scss) 入手
- 浅色/深色语义面层令牌:从 [base.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/base.scss) 入手
- header、页面外壳、顶层间距:从 [app.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/layout/app.scss) 或 [header-base.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/layout/header-base.scss) 入手
- 可复用小组件样式:查看 `components/`
- 单一路由/页面的外观:查看 `pages/`
- 工具类或最后一层覆盖:查看 `utils/`

## 编辑规则

- 请勿重新引入 `index.css`。
- 在 TSX 中,普通的视觉样式请勿使用 inline `style={{ ... }}`。
- 优先使用令牌,而不是裸值。
- 在 [base.scss](/Volumes/code/workspace/products/ielts-vocab/frontend/src/styles/base.scss) 之外,不要引入裸 `#hex`、裸 `rgb(...)` / `rgba(...)` / `hsl(...)`、`color: white` 或 `color-mix(... white)`。
- 若某个主题页面需要特殊颜色,先在页面根部附近定义页面级语义 CSS 变量,然后在子元素中消费这些变量,而不是在各处散落一次性颜色值。
- 除明确批准外,优先使用纯橙色强调面层,而不是渐变。
- 间距节奏默认基于 `10px`,除非令牌另有定义。
- 若样式需要动态几何,优先使用由 refs 设置的 CSS 变量,而不是临时的 JSX inline 样式。
- 深色主题应优先由语义令牌驱动。优先使用 `surface-*`、`border-*`、`focus-ring`、`chart-*`、`text-*` 令牌,而不是页面级 `[data-theme="dark"]` 覆盖。
- 页面级 `[data-theme="dark"]` 覆盖应保留给数据可视化语义或真正特殊的状态;共享 UI 面层、输入框、下拉、模态、按钮应自动继承自令牌层。
- 当页面需要 toolbar、数据外壳或指标卡片时,优先复用 `toolbar-surface`、`table-shell`、`metric-card`,而不是新增页面专属的容器模式。
- 当页面需要表格尺寸或共享 head/body 单元格处理时,优先使用 `data-table-base`、`data-table-head-cell`、`data-table-body-cell`,而不是在本地重新定义表格排版与单元格内边距。
- 当页面需要按钮、输入框或徽标时,优先使用 `control-button`、`accent-button`、`input-control`、`pill-badge`,而不是新增路由专属的变体。
