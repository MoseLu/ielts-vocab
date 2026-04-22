# IELTS Vocabulary API

## 架构索引

- 后端总览: [README.md](./README.md)
- 后端分层架构: [backend-layered-architecture.md](../docs/architecture/backend-layered-architecture.md)
- 网关契约: [gateway-service-contracts.md](../docs/architecture/gateway-service-contracts.md)

## 当前浏览器契约

- Browser Base URL: `http://127.0.0.1:8000/api`
- 浏览器入口: `gateway-bff -> /api/* -> split services`
- 浏览器鉴权: `HttpOnly Cookie + JWT access/refresh session`
- 请求格式: 绝大多数接口是 `JSON`；音频、导出、流式接口会返回二进制或流
- 兼容说明: `backend/app.py :5000` 仅保留给 rollback drill / monolith compatibility，不再是默认浏览器 API 路径

浏览器端不应自行持有浏览器侧 access token，也不应手动拼装 `Authorization` 头。认证 cookie 由服务端设置，前端统一通过 `credentials: include` 发送。

## 认证链路

### 注册与登录

- `POST /api/auth/register`
- `POST /api/auth/login`

成功时服务端会：

1. 设置 `access_token` 与 `refresh_token` 两个 HttpOnly cookies。
2. 返回当前用户快照。
3. 返回 `access_expires_in`，供前端做会话保活。

### 会话探测与刷新

- `GET /api/auth/me`
- `POST /api/auth/refresh`

前端在以下场景使用这条链路：

1. 页面加载时用 `/api/auth/me` 验证 cookie 会话。
2. 遇到业务接口 `401` 时，先走一次 silent refresh。
3. refresh 成功后重试原请求；失败则清理本地用户状态。

### 登出

- `POST /api/auth/logout`

登出会撤销相关 token 并清理 cookie；浏览器侧不需要也不应该额外携带 header token。

## 主要接口分组

- `/api/auth`: 注册、登录、登出、当前用户、邮箱绑定与密码恢复
- `/api/books`: 词书、章节、单词详情、进度、收藏、熟词、易混词
- `/api/progress`: 兼容进度接口，仍保留给旧学习流
- `/api/ai`: AI 助手、学习统计、学习画像、错词、练习支持与口语评分
- `/api/notes`: 日志、总结、导出、任务
- `/api/tts`: 单词/例句音频、批量生成状态、媒体探针
- `/api/admin`: 管理员运营接口
- `/socket.io/*`: 独立 ASR Socket.IO 通道，由 nginx 直接代理到 `:5001`

## 响应与错误约定

常规错误响应仍采用：

```json
{
  "error": "错误信息描述"
}
```

常见状态码：

- `200`: 成功
- `201`: 创建成功
- `400`: 参数错误或校验失败
- `401`: 会话无效或已过期
- `403`: 权限不足
- `404`: 资源不存在
- `429`: 速率限制
- `503`: 下游服务或严格内部契约暂时不可用

## 进一步参考

- 生产部署与运维: [cloud-microservices-deployment.md](../docs/operations/cloud-microservices-deployment.md)
- Release closeout: [release-closeout-checklist.md](../docs/operations/release-closeout-checklist.md)
