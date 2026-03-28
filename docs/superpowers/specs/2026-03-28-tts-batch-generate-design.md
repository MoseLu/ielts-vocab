# TTS 词书例句音频批量预生成设计

## 背景

目前听写模式的例句音频在用户首次访问时实时生成（just-in-time），依赖 MiniMax TTS API，可能因网络延迟导致播放卡顿。大型词书（如 `ielts_comprehensive`，约 3500 条有例句）需要预生成音频文件到本地缓存目录 `backend/tts_cache/`，管理员通过管理后台手动触发。

## 目标

- 管理员可在 `/admin` 后台手动触发词书的例句音频批量生成
- 生成过程在后台异步执行，不阻塞前端请求
- 前端实时显示生成进度（已生成 / 总数）
- 用户听写时直接命中本地缓存，无 API 调用延迟

---

## 现有系统

### 数据

- **词书**：`routes/books.py` 中 `VOCAB_BOOKS` 定义 5 本词书，词汇数据存储在 `vocabulary_data/` JSON/CSV 文件
- **例句**：`vocabulary_examples.json`，key = 单词小写，value = `[{en, zh}]`，约 9063 条
- **TTS 缓存**：`backend/tts_cache/{hash}.mp3`，hash = `md5("ex:{sentence}:{voice_id}")[:16]`
- **Voice 轮换**：两个 voice 交替使用 `English_Trustworthy_Man` / `Serene_Woman`

### 现有 TTS API

- `POST /api/tts/example-audio` — 生成单条例句音频，cache-first（命中直接返回文件）

---

## 设计

### 进度判断

- **总任务数**：词书中**有例句的单词**数量（每词一条例句）
- **已完成数**：分别用两个 voice_id 计算缓存路径，**任一存在**即算已生成
- **状态**：`cached == total` → 已完成，否则显示"已生成 X / Y 条"

### 后端

#### 1. `POST /api/admin/tts/generate/{book_id}`

- 鉴权：Admin JWT
- 加载词书所有有例句的单词，计算任务列表
- 用 `eventlet.spawn()` 后台异步生成（200ms 间隔控速率）
- 检查 `tts_cache/` 中已存在的文件，跳过已有缓存
- 返回 `202 { message: "生成已启动", total: N }`

#### 2. `GET /api/admin/tts/status/{book_id}`

- 鉴权：Admin JWT
- 加载词书有例句的单词总数，扫描 tts_cache/ 中对应缓存文件数
- 返回 `{ book_id, total: N, cached: M, generating: bool }`

#### 3. `GET /api/admin/tts/books-summary`

- 鉴权：Admin JWT
- 返回所有 5 本词书的 TTS 进度摘要
- 返回 `[{ book_id, title, total, cached, generating }]`

#### 后台生成任务逻辑

```
for word in book_words_with_examples:
    sentence = word.example.en
    for voice_id in [English_Trustworthy_Man, Serene_Woman]:
        cache_key = md5(f"ex:{sentence}:{voice_id}")[:16]
        cache_file = tts_cache / f"{cache_key}.mp3"
        if cache_file.exists(): continue
        call MiniMax TTS API
        save to cache_file
        sleep 0.2  # 速率控制
```

### 前端

#### AdminDashboard 新增 Tab：「词书 TTS 音频」

- 显示 5 本词书的 TTS 进度卡片
- 每张卡片：词书名、进度条、"已生成 X / Y 条"、状态标签（已完成/生成中/未开始）
- 「生成」按钮：点击后轮询 status 接口，更新进度条
- 按钮状态：生成中禁用，完成变绿色勾

---

## 缓存策略（不变）

- `DictationMode.handlePlayExample` 调用 `/api/tts/example-audio`
- 后端 cache-first 逻辑不变：命中缓存直接返回文件，未命中调用 API 并写入缓存
- 预生成提前写入缓存文件，用户无感

---

## 文件改动

### 后端

- `backend/routes/tts.py` — 新增 `books_summary`、`generate_book_tts`、`tts_status` 三个路由
- `backend/routes/admin.py` — 引用 tts 模块的三个新路由

### 前端

- `src/components/AdminDashboard.tsx` — 新增 TTS Tab
- `src/styles/pages/admin.css` — TTS Tab 样式

---

## 无需改动

- `DictationMode.tsx` — 播放逻辑不变
- `PracticePage.tsx` — 流程不变
- `vocabulary_examples.json` — 数据不变
