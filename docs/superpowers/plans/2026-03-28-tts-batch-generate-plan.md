# TTS 词书例句音频批量预生成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 管理员通过后台触发词书例句音频批量预生成，异步执行并实时显示进度，用户听写时直接命中本地缓存。

**Architecture:** 后端新增 admin TTS 接口 + eventlet 后台任务，前端 AdminDashboard 新增 TTS Tab。DictationMode 和现有 TTS 缓存逻辑保持不变。

**Tech Stack:** Flask (eventlet), React, MiniMax TTS API

---

## File Map

### Backend
- `backend/routes/tts.py` — 新增 3 个 admin 路由（不在 admin.py，在 tts.py，通过 admin_bp 引用）
- `backend/app.py` — 注册 admin_tts 蓝本（或在 admin.py 中引用）

### Frontend
- `src/components/AdminDashboard.tsx` — 新增 TTS Tab
- `src/styles/pages/admin.css` — TTS Tab 样式

---

## Task 1: 后端 - `tts.py` 新增 admin 路由

**Files:**
- Modify: `backend/routes/tts.py` (末尾追加)

**路由：**
1. `GET /api/admin/tts/books-summary` — 所有词书 TTS 进度摘要
2. `POST /api/admin/tts/generate/{book_id}` — 触发后台生成任务
3. `GET /api/admin/tts/status/{book_id}` — 查询单个词书进度

**关键函数：**
- `_get_book_examples(book_id)` — 加载词书所有有例句的单词及其例句
- `_count_cached_examples(book_id, examples)` — 扫描 tts_cache/ 统计已缓存数
- `_generate_for_book(book_id)` — eventlet 后台生成任务
- `_cache_key(sentence, voice_id)` — 计算缓存文件 hash 路径

```python
# 追加到 backend/routes/tts.py 末尾

def _get_book_examples(book_id):
    """返回词书中所有有例句的单词及例句."""
    from routes.books import load_book_vocabulary
    words = load_book_vocabulary(book_id)
    result = []
    for w in words:
        examples = w.get('examples', [])
        if examples:
            result.append({'word': w['word'], 'sentence': examples[0]['en']})
    return result

def _cache_file_path(sentence: str, voice_id: str) -> Path:
    import hashlib
    key = hashlib.md5(f"ex:{sentence}:{voice_id}".encode()).hexdigest()[:16]
    return _cache_dir() / f'{key}.mp3'

def _count_cached(book_id: str, examples: list) -> int:
    """返回已缓存的句子数（两个 voice 任一存在即算已缓存）."""
    cached = 0
    for ex in examples:
        sentence = ex['sentence']
        for vid in _ALTERNATING_VOICES:
            if _cache_file_path(sentence, vid).exists():
                cached += 1
                break  # 任一 voice 存在即算一条
    return cached

@tts_bp.route('/admin/books-summary', methods=['GET'])
@admin_required
def admin_books_summary():
    from routes.books import VOCAB_BOOKS
    result = []
    for book in VOCAB_BOOKS:
        examples = _get_book_examples(book['id'])
        total = len(examples)
        cached = _count_cached(book['id'], examples)
        result.append({
            'book_id': book['id'],
            'title': book['title'],
            'total': total,
            'cached': cached,
        })
    return jsonify({'books': result}), 200

@tts_bp.route('/admin/generate/<book_id>', methods=['POST'])
@admin_required
def admin_generate_book(book_id):
    from routes.books import VOCAB_BOOKS
    if not any(b['id'] == book_id for b in VOCAB_BOOKS):
        return jsonify({'error': 'Book not found'}), 404
    examples = _get_book_examples(book_id)
    if not examples:
        return jsonify({'error': 'No examples found'}), 400
    # 已在生成中则返回 409
    if book_id in _generating_books:
        return jsonify({'error': 'Already generating', 'total': len(examples)}), 409
    _generating_books.add(book_id)
    total = len(examples)
    eventlet.spawn(_generate_for_book, book_id, examples)
    return jsonify({'message': 'Generation started', 'total': total}), 202

@tts_bp.route('/admin/status/<book_id>', methods=['GET'])
@admin_required
def admin_tts_status(book_id):
    examples = _get_book_examples(book_id)
    total = len(examples)
    cached = _count_cached(book_id, examples)
    generating = book_id in _generating_books
    return jsonify({
        'book_id': book_id,
        'total': total,
        'cached': cached,
        'generating': generating,
    }), 200
```

**新增模块级变量：**
```python
_generating_books: set = set()  # 正在生成的 book_id 集合
```

**新增后台任务函数：**
```python
def _generate_for_book(book_id: str, examples: list):
    """后台批量生成任务（eventlet spawn）. 对每个缺失缓存的例句调用 TTS."""
    global _generating_books
    try:
        for ex in examples:
            sentence = ex['sentence']
            for voice_id in _ALTERNATING_VOICES:
                cache_path = _cache_file_path(sentence, voice_id)
                if cache_path.exists():
                    continue
                try:
                    _call_tts_api(sentence, voice_id, cache_path)
                except Exception as e:
                    print(f'[TTS Gen Error] {sentence[:30]}: {e}')
                eventlet.sleep(0.2)  # 速率控制
    finally:
        _generating_books.discard(book_id)
```

**新增内部 API 调用函数：**
```python
def _call_tts_api(sentence: str, voice_id: str, save_path: Path):
    """调用 MiniMax TTS 并保存到 save_path."""
    import requests
    api_key = _get_api_key()
    url = f"{MINIMAX_BASE_URL}/v1/t2a_v2"
    sentence_with_pauses = add_pause_tags(sentence, pause_seconds=0.4)
    payload = {
        "model": "speech-2.8-hd",
        "text": sentence_with_pauses,
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": 0.9,
            "vol": 1.0,
            "pitch": 0,
            "emotion": "neutral"
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1
        }
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"TTS API error: {resp.status_code}")
    resp_data = resp.json()
    audio_hex = resp_data.get('data', {}).get('audio')
    if not audio_hex:
        raise Exception("No audio in response")
    audio_bytes = bytes.fromhex(audio_hex)
    with open(save_path, 'wb') as f:
        f.write(audio_bytes)
```

**注意：** `add_pause_tags`、`_ALTERNATING_VOICES`、`_get_api_key`、`MINIMAX_BASE_URL` 均已在文件中定义，直接使用。`@admin_required` 从 `routes.middleware` 导入。

- [ ] **Step 1: 在 `tts.py` 末尾追加 admin 路由代码**

- [ ] **Step 2: 验证语法正确**（在 backend 目录运行 `python -c "import routes.tts"`）

- [ ] **Step 3: Commit**

---

## Task 2: 后端 - 在 `admin.py` 中引用 TTS 路由

**Files:**
- Modify: `backend/routes/admin.py`

**在 `admin.py` 顶部 import 区域追加：**
```python
from routes.tts import tts_bp
```

**在 `register_routes()` 函数中（`admin_bp.register_routes(app)` 之后）追加：**
```python
    app.register_blueprint(tts_bp, url_prefix='/api/admin/tts')
```

- [ ] **Step 1: 修改 `admin.py` 导入并注册 tts_bp**

- [ ] **Step 2: 验证无路由冲突**（`python -c "from routes.admin import register_routes; print('ok')"`）

- [ ] **Step 3: Commit**

---

## Task 3: 前端 - AdminDashboard TTS Tab

**Files:**
- Modify: `src/components/AdminDashboard.tsx`
- Modify: `src/styles/pages/admin.css`

**在 AdminDashboard 中新增 TTS Tab 组件：**

### Tab 状态
```typescript
const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'tts'>('overview');
```

### Tab 切换按钮（在"用户管理"按钮旁添加）
```tsx
<button
  className={`admin-tab-btn ${activeTab === 'tts' ? 'active' : ''}`}
  onClick={() => setActiveTab('tts')}
>
  词书音频
</button>
```

### TTS Tab 内容（条件渲染 activeTab === 'tts'）
```tsx
<div className="admin-tts-panel">
  <h2 className="admin-section-title">词书 TTS 音频</h2>
  <p className="admin-section-desc">为词书预生成例句音频，用户听写时直接命中本地缓存。</p>
  <div className="tts-books-grid">
    {ttsBooks.map(book => (
      <div key={book.book_id} className={`tts-book-card ${book.cached === book.total ? 'done' : ''}`}>
        <div className="tts-book-title">{book.title}</div>
        <div className="tts-book-progress">
          <div className="tts-progress-bar">
            <div
              className="tts-progress-fill"
              style={{ width: `${book.total > 0 ? (book.cached / book.total) * 100 : 0}%` }}
            />
          </div>
          <span className="tts-progress-text">
            {book.cached} / {book.total} 条
          </span>
        </div>
        <button
          className={`tts-generate-btn ${book.generating ? 'loading' : ''} ${book.cached === book.total ? 'done' : ''}`}
          onClick={() => handleGenerate(book.book_id)}
          disabled={book.generating || book.cached === book.total}
        >
          {book.generating ? '生成中...' : book.cached === book.total ? '已完成' : '生成'}
        </button>
      </div>
    ))}
  </div>
</div>
```

### 数据获取
```typescript
const [ttsBooks, setTtsBooks] = useState<TtsBook[]>([]);

useEffect(() => {
  if (activeTab === 'tts') {
    fetchTtsBooks();
  }
}, [activeTab]);

const fetchTtsBooks = async () => {
  const res = await fetch('/api/admin/tts/books-summary', {
    headers: { ...authHeaders },
  });
  const data = await res.json();
  setTtsBooks(data.books);
};

const handleGenerate = async (bookId: string) => {
  await fetch(`/api/admin/tts/generate/${bookId}`, {
    method: 'POST',
    headers: { ...authHeaders },
  });
  // 轮询进度
  const interval = setInterval(async () => {
    const res = await fetch(`/api/admin/tts/status/${bookId}`, {
      headers: { ...authHeaders },
    });
    const data = await res.json();
    setTtsBooks(prev =>
      prev.map(b => b.book_id === bookId ? { ...b, ...data } : b)
    );
    if (!data.generating) clearInterval(interval);
  }, 2000);
};
```

### 类型定义
```typescript
interface TtsBook {
  book_id: string;
  title: string;
  total: number;
  cached: number;
  generating?: boolean;
}
```

- [ ] **Step 1: 添加 TtsBook 类型和状态**

- [ ] **Step 2: 新增 Tab 切换按钮**

- [ ] **Step 3: 编写 TTS Tab 内容组件**

- [ ] **Step 4: 编写 fetchTtsBooks 和 handleGenerate 函数**

- [ ] **Step 5: 添加 useEffect 触发数据加载**

- [ ] **Step 6: Commit**

---

## Task 4: 前端样式

**Files:**
- Modify: `src/styles/pages/admin.css`

```css
.admin-tts-panel {
  padding: 24px;
}

.admin-section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.admin-section-desc {
  color: #6b7280;
  font-size: 14px;
  margin-bottom: 24px;
}

.tts-books-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.tts-book-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tts-book-card.done {
  border-color: #10b981;
  background: #f0fdf4;
}

.tts-book-title {
  font-weight: 600;
  font-size: 15px;
}

.tts-book-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tts-progress-bar {
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.tts-progress-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.tts-book-card.done .tts-progress-fill {
  background: #10b981;
}

.tts-progress-text {
  font-size: 13px;
  color: #6b7280;
}

.tts-generate-btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  background: #3b82f6;
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.tts-generate-btn:hover:not(:disabled) {
  background: #2563eb;
}

.tts-generate-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tts-generate-btn.done {
  background: #10b981;
}

.tts-generate-btn.loading {
  background: #9ca3af;
}
```

- [ ] **Step 1: 追加 CSS 样式到 admin.css**

- [ ] **Step 2: Commit**

---

## Task 5: 端到端验证

**验证步骤：**

1. 启动后端：`python app.py`
2. 启动前端：`npm run dev`
3. 访问 `/admin`，登录
4. 切换到「词书音频」Tab
5. 确认 5 本词书的进度卡片正常显示（total/cached 数字）
6. 点击任意词书的「生成」按钮
7. 确认进度条实时更新
8. 生成完成后确认按钮变为绿色「已完成」

- [ ] **执行端到端验证**
- [ ] **修复发现的问题**
- [ ] **最终 Commit**

---

## 依赖顺序

Task 1 → Task 2 → Task 3 → Task 4 → Task 5
