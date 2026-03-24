# 架构审查 TODO

> 以架构师视角审查，涵盖安全漏洞、架构缺陷、风险决策。
> 严重程度：🔴 危急 | 🟠 高 | 🟡 中 | 🔵 低

---

## 🔴 危急问题（上线前必须修复）

### 1. JWT 密钥硬编码兜底值
**文件：** `backend/config.py`
```python
SECRET_KEY = os.environ.get('SECRET_KEY') or 'ielts-vocab-secret-key-2024'
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'ielts-vocab-jwt-secret-2024'
```
**风险：** 未配置环境变量时使用公开可知的固定密钥，任何人都能伪造合法 JWT Token。
**修复：** 去掉 `or '...'` 兜底，若未配置则启动时抛出异常强制失败。

```python
SECRET_KEY = os.environ['SECRET_KEY']  # 缺失则启动失败，强制配置
JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']
```

---

### 2. WebSocket CORS 全域名开放
**文件：** `backend/app.py`
```python
socketio = SocketIO(app, cors_allowed_origins="*", ...)
```
**风险：** REST API 的 CORS 已限制到指定域名，但 WebSocket 对所有域名开放，任意第三方站点均可建立 WebSocket 连接，造成跨站攻击面。
**修复：** 与 REST CORS 保持一致，使用 `app.config['CORS_ORIGINS']`。

```python
socketio = SocketIO(app, cors_allowed_origins=app.config['CORS_ORIGINS'], ...)
```

---

### 3. 默认管理员账号硬编码在启动代码中
**文件：** `backend/app.py`
```python
admin.set_password('admin123')
print("[Admin] Default admin user created (admin / admin123)")
```
**风险：** 弱密码 `admin123` 写入代码并打印到日志，任何能看到日志的人都知道初始凭据。
**修复：** 从环境变量读取初始密码，或删除自动创建逻辑，改为文档说明 CLI 手动初始化。

---

## 🟠 高风险问题

### 4. 邮件验证码无频率限制，可暴力破解
**文件：** `backend/routes/auth.py`
密码重置、邮箱验证等接口未加 Rate Limit，而登录接口有保护。6 位纯数字验证码（100 万种组合）在无限制下可被快速枚举。
**修复：** 在 `/forgot-password`、`/verify-email` 等端点应用相同的 `_check_rate_limit` 逻辑，并对验证码错误次数单独计数（每码最多尝试 5 次）。

---

### 5. Rate Limiting 依赖进程内存，多进程部署失效
**文件：** `backend/routes/auth.py`
```python
_rate_buckets: dict = defaultdict(...)  # 进程内全局变量
```
**风险：** 生产环境通常启动多个 worker（Gunicorn、uWSGI），各进程拥有独立 bucket，攻击者将请求分散到不同 worker 即可绕过限制，实际门槛是配置值 × worker 数量。
**修复：** 改用 Redis 作为共享存储（`redis-py` + `flask-limiter`）。

---

### 6. Token 被盗检测处置不足
**文件：** `backend/routes/auth.py` refresh 端点注释
```python
# Possible token theft — revoke all user tokens would be ideal,
# but for simplicity we just reject and force re-login.
```
**风险：** 检测到 Refresh Token 重放（可能被盗）时仅拒绝该次请求，已颁发的 Access Token 仍有最长 2 小时有效期，攻击者可继续操作。
**修复：** 检测到重放时立即吊销该用户全部 Token，并触发告警（邮件通知用户）。

---

### 7. Access Token 有效期过长
**文件：** `backend/config.py`
```python
JWT_ACCESS_TOKEN_EXPIRES = 60 * 120  # 2 小时
```
**风险：** 注释表明原本是 15 分钟，为减少刷新频率改为 2 小时（以安全换体验），Token 泄漏后窗口期过大。
**修复：** 恢复 15 分钟，前端改用静默刷新（Background Refresh）以保证学习体验连续性，而不是直接加长有效期。

---

## 🟡 中风险问题

### 8. 邮件发送为 Mock，生产环境静默失效
**文件：** `backend/routes/auth.py`
```python
def _send_code_mock(email, code, purpose):
    print(f"[Email Code] To: {email}...")
```
**风险：** 所有验证码仅打印到控制台，生产部署后注册/密码重置等流程将静默失败，用户永远收不到邮件。
**修复：** 集成真实邮件服务（SendGrid / SES / SMTP），并对发送失败返回明确错误。

---

### 9. 前端多处直接 `JSON.parse` 绕过 Zod 验证
**文件：** `src/hooks/useAIChat.ts`
```typescript
const stored = JSON.parse(localStorage.getItem('mode_performance') || '{}')
const raw = JSON.parse(localStorage.getItem('chapter_progress') || '{}')
```
**风险：** localStorage 数据可被用户篡改，跳过 Zod 验证导致运行时类型错误或潜在注入。
**修复：** 统一通过 `getStorageItem()` + Zod schema 读取所有 localStorage 数据。

---

### 10. 邮箱格式校验过于宽松
**文件：** `backend/routes/auth.py`
```python
if '@' not in email:
    return jsonify({'error': '邮箱格式不正确'}), 400
```
`a@b`、`@x.com` 等无效格式均通过校验。
**修复：** 使用 `email-validator` 库或正则表达式进行合规校验。

---

### 11. apiFetch 无超时设置
**文件：** `src/lib/index.ts`
所有 API 请求无超时限制，网络故障时请求可无限挂起，导致 UI 卡死。
**修复：**
```typescript
signal: AbortSignal.timeout(30_000)  // 30 秒超时
```

---

### 12. 生产构建开启 sourcemap
**文件：** `vite.config.js`
```javascript
build: { sourcemap: true }
```
**风险：** 生产环境暴露 TypeScript 源码，方便逆向分析业务逻辑。
**修复：** 仅在 CI 调试构建中开启，生产关闭或使用 hidden sourcemap（上传到错误监控服务）。

---

### 13. Flask 调试日志在生产开启
**文件：** `backend/app.py`
```python
socketio = SocketIO(..., logger=True, engineio_logger=True)
```
**风险：** 可能泄漏请求内容、内部路径、用户信息到日志。
**修复：** 根据 `app.config['DEBUG']` 条件开启。

---

### 14. 无请求体大小限制（DoS 风险）
**文件：** `backend/config.py` / `backend/app.py`
Flask 默认无请求体大小上限，攻击者可发送 GB 级请求耗尽内存。
**修复：**
```python
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB
```

---

## 🔵 低风险 / 架构改进

### 15. AIChatContext 使用模块级全局变量（反模式）
**文件：** `src/contexts/AIChatContext.tsx`
```typescript
let _currentContext: LearningContext = {}
let _setContextRef: ((ctx: LearningContext) => void) | null = null

export function setGlobalLearningContext(ctx: Partial<LearningContext>) {
  _currentContext = { ..._currentContext, ...ctx }
  _setContextRef?.(_currentContext)
}
```
**风险：** 绕过 React 数据流，在模块级存储状态，多处调用无法被 React 感知，可能导致状态不同步。
**修复：** 改为纯 React Context + `useReducer`，或使用 Zustand 等轻量状态管理库。

---

### 16. 数据库迁移为手写过程式 SQL，无版本管理
**文件：** `backend/app.py`
```python
def _migrate_db(app):
    # Migration 1...
    # Migration 2...
```
**风险：** 每次启动都重新执行所有迁移（无幂等保证），无法回滚，团队协作时迁移冲突难以解决。
**修复：** 引入 **Alembic**（SQLAlchemy 官方迁移工具）管理版本化迁移。

---

### 17. SQLite 不适合生产多并发场景
**文件：** `backend/config.py`
```python
SQLALCHEMY_DATABASE_URI = 'sqlite:///database.sqlite'
```
**风险：** SQLite 写操作加文件锁，高并发写入时严重竞争；无内置主从复制，数据丢失风险高；Token 吊销表每次请求查询加剧 I/O。
**修复：** 生产环境迁移至 **PostgreSQL**，开发保留 SQLite。

---

### 18. Token 吊销查询每次请求都命中数据库
**文件：** `backend/models.py`
```python
@classmethod
def is_revoked(cls, jti: str) -> bool:
    return db.session.query(cls.query.filter_by(jti=jti).exists()).scalar()
```
**风险：** 100 并发用户 × 每请求 1 次查询 = 数据库持续压力，结合 SQLite 写锁更严重。
**修复：** 引入 Redis 缓存吊销列表（TTL = Token 有效期），减少 99% 的 DB 查询。

---

### 19. AI 上下文每次消息都重新构建，重复解析 localStorage
**文件：** `src/hooks/useAIChat.ts`
```typescript
const buildContext = useCallback(() => {
  const raw = JSON.parse(localStorage.getItem('chapter_progress') || '{}')
  // 再次 parse mode_performance, quick_memory_records...
}, [])  // 依赖数组为空但实际每次都重新执行
```
**修复：** 将聚合统计缓存到 `useMemo` / `useRef`，仅在相关数据变化时重算。

---

### 20. 全词汇库全量加载到进程内存
**文件：** `backend/routes/ai.py`
```python
_global_vocab_pool: list | None = None  # 全量词汇 in-memory
```
**风险：** 词库增长时内存占用线性增加，多 worker 时每个进程独立持有全量数据。
**修复：** 使用数据库索引查询 + 分页，或限定加载频率最高词汇的子集。

---

### 21. LLM 响应无缓存，每次重复调用 AI API
**文件：** `backend/routes/ai.py`（`/api/ai/greet` 端点）
每次打开 AI 面板都调用外部 LLM，完全相同的上下文会生成不同响应，浪费 API 配额。
**修复：** 对打招呼等低变化请求按 `(user_id, book_id, day)` 缓存 1 小时。

---

### 22. 无用户数据删除接口（GDPR 合规缺失）
当前无 `/api/user/delete` 端点，用户无法行使"被遗忘权"。
**修复：** 实现账号注销接口，级联删除用户数据（或标记软删除保留统计）。

---

### 23. AI 上下文将用户学习数据发送至第三方 LLM（隐私）
**文件：** `src/hooks/useAIChat.ts`
`buildContext()` 包含书名、章节进度、正确率等，明文发送至 MiniMax API。
**修复：** 隐私政策中披露，提供用户选项关闭上下文增强，或在发送前匿名化。

---

## 优先级行动清单

| 优先级 | 任务 |
|--------|------|
| P0（上线前） | #1 JWT 密钥、#2 WebSocket CORS、#3 默认 admin 密码 |
| P1（上线前） | #4 验证码无限制、#12 sourcemap、#14 请求大小限制 |
| P2（上线后 1 周） | #8 真实邮件、#9 Zod 覆盖、#11 请求超时 |
| P3（上线后 1 月） | #5 Redis Rate Limit、#16 Alembic、#17 PostgreSQL |
| P4（长期优化） | #15 Context 重构、#19 缓存优化、#21 LLM 缓存 |
