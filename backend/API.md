# IELTS Vocabulary API 文档

## 架构索引

- 后端总览: [README.md](/F:/enterprise-workspace/projects/ielts-vocab/backend/README.md)
- 后端分层架构: [backend-layered-architecture.md](/F:/enterprise-workspace/projects/ielts-vocab/docs/architecture/backend-layered-architecture.md)

## 基础信息

- **Base URL**: `http://localhost:8000/api`
- **认证方式**: JWT Token (Bearer Token)
- **请求格式**: JSON
- **响应格式**: JSON

浏览器兼容入口默认通过 `gateway-bff` 暴露；`backend/app.py` 的 `5000` 端口只保留为兼容 monolith 参考路径。

## 认证接口

### 注册用户

```
POST /api/auth/register
```

**请求体:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "username": "username"
}
```

**响应:**
```json
{
  "message": "Registration successful",
  "token": "eyJhbGci...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "created_at": "2026-03-13T05:58:57"
  }
}
```

**状态码:**
- 201: 注册成功
- 400: 输入验证失败
- 400: 邮箱已被注册

---

### 登录

```
POST /api/auth/login
```

**请求体:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应:**
```json
{
  "message": "Login successful",
  "token": "eyJhbGci...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "created_at": "2026-03-13T05:58:57"
  }
}
```

**状态码:**
- 200: 登录成功
- 400: 缺少邮箱或密码
- 401: 邮箱或密码错误

---

### 登出

```
POST /api/auth/logout
```

**请求头:**
```
Authorization: Bearer <token>
```

**响应:**
```json
{
  "message": "Logout successful"
}
```

**状态码:**
- 200: 登出成功
- 401: 未认证或Token无效

---

### 获取当前用户

```
GET /api/auth/me
```

**请求头:**
```
Authorization: Bearer <token>
```

**响应:**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "created_at": "2026-03-13T05:58:57"
  }
}
```

**状态码:**
- 200: 成功
- 401: 未认证或Token无效

---

## 进度接口

### 获取所有进度

```
GET /api/progress
```

**请求头:**
```
Authorization: Bearer <token>
```

**响应:**
```json
{
  "progress": [
    {
      "id": 1,
      "user_id": 1,
      "day": 1,
      "current_index": 50,
      "correct_count": 45,
      "wrong_count": 5,
      "updated_at": "2026-03-13T05:59:24"
    }
  ]
}
```

**状态码:**
- 200: 成功
- 401: 未认证或Token无效

---

### 保存进度

```
POST /api/progress
```

**请求头:**
```
Authorization: Bearer <token>
```

**请求体:**
```json
{
  "day": 1,
  "current_index": 50,
  "correct_count": 45,
  "wrong_count": 5
}
```

**说明:**
- `day`: 必需，学习天数 (1-30)
- `current_index`: 当前单词索引
- `correct_count`: 正确数量
- `wrong_count`: 错误数量

**响应:**
```json
{
  "message": "Progress saved",
  "progress": {
    "id": 1,
    "user_id": 1,
    "day": 1,
    "current_index": 50,
    "correct_count": 45,
    "wrong_count": 5,
    "updated_at": "2026-03-13T05:59:24"
  }
}
```

**状态码:**
- 200: 保存成功
- 400: 缺少必要参数
- 401: 未认证或Token无效

---

### 获取指定天数进度

```
GET /api/progress/<day>
```

**请求头:**
```
Authorization: Bearer <token>
```

**响应:**
```json
{
  "progress": {
    "id": 1,
    "user_id": 1,
    "day": 1,
    "current_index": 50,
    "correct_count": 45,
    "wrong_count": 5,
    "updated_at": "2026-03-13T05:59:24"
  }
}
```

**状态码:**
- 200: 成功
- 404: 未找到该天进度
- 401: 未认证或Token无效

---

## 词汇接口

### 获取所有词汇

```
GET /api/vocabulary
```

**响应:**
```json
{
  "vocabulary": [
    {
      "id": 1,
      "day": 1,
      "word": "abandon",
      "phonetic": "/əˈbændən/",
      "pos": "v.",
      "definition": "放弃；遗弃"
    }
  ]
}
```

---

### 获取指定天词汇

```
GET /api/vocabulary/day/<day>
```

**响应:**
```json
{
  "vocabulary": [
    {
      "id": 1,
      "day": 1,
      "word": "abandon",
      "phonetic": "/əˈbændən/",
      "pos": "v.",
      "definition": "放弃；遗弃"
    }
  ]
}
```

**状态码:**
- 200: 成功
- 400: 天数无效 (1-30)

---

## 错误响应格式

所有错误响应都遵循以下格式:

```json
{
  "error": "错误信息描述"
}
```

**常见状态码:**
- 200: 成功
- 201: 创建成功
- 400: 客户端错误 (验证失败)
- 401: 未认证 (Token无效)
- 404: 资源不存在
- 500: 服务器错误
