# E2E 测试文档

## 环境准备

1. **安装依赖：**
   ```bash
   pnpm install
   ```

2. **安装 Playwright 浏览器：**
   ```bash
   pnpm --dir frontend exec playwright install chromium
   ```

3. **启动 split backend：**
   ```bash
   ./start-microservices.sh
   ```

4. **启动前端服务：**
   ```bash
   pnpm dev
   ```

## 运行测试

### 运行全部测试：
```bash
pnpm test:e2e
```

`frontend/playwright.config.ts` 现在只自动启动前端开发服务器。启动套件前请保持 split backend 在 `gateway-bff:8000` 上运行。

### 运行 CI 冒烟子集：
```bash
pnpm --dir frontend exec playwright test tests/e2e/smoke.spec.ts
```

### 运行指定测试文件：
```bash
pnpm --dir frontend exec playwright test auth.spec.ts
```

### 以有头模式运行（显示浏览器）：
```bash
pnpm --dir frontend exec playwright test --headed
```

### 以 UI 模式运行：
```bash
pnpm --dir frontend exec playwright test --ui
```

### 以调试模式运行：
```bash
pnpm --dir frontend exec playwright test --debug
```

### 查看测试报告：
```bash
pnpm --dir frontend exec playwright show-report
```

## 测试覆盖

### 测试文件：

1. **auth.spec.ts** - 认证流程（登录、注册、校验）
2. **navigation.spec.ts** - 路由跳转与重定向
3. **vocab-books.spec.ts** - 词书与章节
4. **practice.spec.ts** - 练习页面的控件与 UI
5. **practice-modes.spec.ts** - 全练习模式（smart、listening、meaning、dictation、radio、quickmemory）
6. **errors.spec.ts** - 错词本/Errors 页面
7. **stats.spec.ts** - 统计与分析
8. **profile.spec.ts** - 用户资料与设置
9. **ai-chat.spec.ts** - AI 聊天助手面板
10. **admin.spec.ts** - 管理员面板
11. **settings.spec.ts** - 练习设置与偏好
12. **integration.spec.ts** - 完整用户旅程的集成测试
13. **smoke.spec.ts** - CI 冒烟子集，覆盖登录页、重定向、注册与登出

### 已覆盖的路由：

- `/login` - 登录/注册页
- `/` - 首页/词书页
- `/plan` - 学习计划页
- `/practice` - 练习页（所有模式）
- `/errors` - 错词页
- `/stats` - 统计页
- `/profile` - 用户资料页
- `/vocab-test` - 词汇测试页
- `/journal` - 学习日志页
- `/admin` - 管理员面板

### 已测试的功能：

- ✅ 用户认证（登录、注册、登出）
- ✅ CI 冒烟路径（登录页、未登录重定向、注册 -> 框架页 -> 登出）
- ✅ 路由跳转与重定向
- ✅ 词书与章节选择
- ✅ 练习模式（smart、listening、meaning、dictation、radio、quickmemory）
- ✅ 练习控件（暂停、继续、跳过、回退）
- ✅ 单词列表面板
- ✅ 设置面板与持久化
- ✅ 错词管理
- ✅ 学习统计与分析
- ✅ 用户资料管理
- ✅ AI 聊天助手
- ✅ 管理员面板（仅管理员用户）
- ✅ 集成工作流

## 配置

修改 `frontend/playwright.config.ts` 可调整：
- 基础 URL（`baseURL`）
- 测试目录（`testDir`）
- 浏览器选项
- 超时设置

## 故障排查

### 测试报“找不到元素”：
- 确认前端与后端都已启动
- 检查 `frontend/playwright.config.ts` 中的基础 URL
- 使用 `--headed` 标志查看实际执行情况

### 鉴权相关问题：
- 测试使用 mock token 完成鉴权
- 若要做真实鉴权测试，请在 auth.spec.ts 中填入真实凭据

### 找不到浏览器：
- 运行 `pnpm --dir frontend exec playwright install chromium`
- 确认磁盘空间充足

## CI/CD 集成

加入 CI 流水线：

```yaml
- name: Install dependencies
  run: pnpm install --frozen-lockfile

- name: Install Playwright
  run: pnpm --dir frontend exec playwright install --with-deps chromium

- name: Run E2E tests
  run: pnpm test:e2e

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

本仓库中 Mac split-runtime 冒烟路径使用：

- `scripts/ci/mac-split-runtime-smoke.sh`
- `frontend/tests/e2e/smoke.spec.ts`
