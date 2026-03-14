# 雅思词汇冲刺 - IELTS Vocabulary

一款基于 Web 的雅思词汇学习应用，30 天学习 3000 个雅思核心词汇。

![IELTS Vocabulary](assets/images/logo.png)

## 功能特点

- **30 天学习计划**：每天 100 个单词，30 天搞定雅思词汇
- **双模式学习**：
  - 释义模式：根据英文单词选择中文释义
  - 听力模式：听发音后选择正确释义
- **进度追踪**：记录正确/错误次数，自动保存学习进度
- **用户系统**：支持注册登录，数据云端同步
- **离线支持**：无网络时自动使用本地存储

## 技术栈

- **前端**：原生 HTML + CSS + JavaScript
- **后端**：Python Flask + SQLite
- **认证**：JWT Token
- **字体**：Inter + Noto Sans SC

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd ielts-vocab
```

### 2. 安装后端依赖

```bash
cd backend
pip install flask flask-cors flask-sqlalchemy flask-jwt-extended
```

### 3. 启动后端服务器

```bash
python app.py
```

后端将运行在 `http://localhost:5000`

### 4. 运行前端

直接在浏览器中打开 `index.html` 即可使用。

## 项目结构

```
ielts-vocab/
├── index.html          # 主页面
├── css/style.css       # 样式文件
├── js/main.js          # 应用逻辑
├── backend/            # Flask 后端
│   ├── app.py          # 应用入口
│   ├── config.py       # 配置文件
│   ├── models.py       # 数据模型
│   └── routes/         # API 路由
│       ├── auth.py     # 认证接口
│       ├── progress.py # 进度接口
│       └── vocabulary.py # 词汇接口
└── assets/images/      # 图片资源
```

## API 接口

### 认证接口
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/me` - 获取当前用户信息

### 进度接口
- `GET /api/progress` - 获取所有学习进度
- `POST /api/progress` - 保存学习进度
- `GET /api/progress/<day>` - 获取指定天的进度

### 词汇接口
- `GET /api/vocabulary` - 获取所有词汇
- `GET /api/vocabulary/day/<day>` - 获取指定天的词汇

## 使用说明

1. 首次使用需要注册账号（或使用本地离线模式）
2. 选择学习日期（Day 1-30）
3. 开始学习：
   - 查看英文单词和音标
   - 点击播放按钮听发音（听力模式自动播放）
   - 从 4 个选项中选择正确释义
   - 答题后自动进入下一题
4. 完成当天学习后可进入下一 Day

## 键盘快捷键

- `1-4`：选择选项

## 浏览器兼容性

- Chrome (推荐)
- Firefox
- Safari
- Edge

需要支持 Web Speech API（用于听力模式）。

## License

MIT
