# 付费词书助记重生成 PRD

Last updated: 2026-05-02

## Background

两本付费词书 `ielts_listening_premium` 和 `ielts_reading_premium` 当前使用
`vocabulary_data/premium_word_mnemonics.json` 提供单词详情页的记忆提示。现有结果中大量
文本是“先抓核心义”“放回句子判断”“核心义仍是”这类模板句，缺少真实助记效果。

本轮目标是在参考 `idictation.cn/home` 的单词列表样式后，用
`MiniMax-M2.7-highspeed` 全量重生成付费词书助记内容。MiniMax 调用使用官方 OpenAI 兼容
接口：`POST https://api.minimaxi.com/v1/chat/completions`，请求字段使用
`model=MiniMax-M2.7-highspeed` 和 `max_completion_tokens`。

## Reference Sampling

2026-05-02 在 Chrome 已打开的 `https://www.idictation.cn/home` 中抽样查看了右侧单词列表
和详情弹层。可见样本特征如下：

- 谐音：`contrary` 用短音近提示绑定“相反”；`abolish` 用“暴力史”绑定“废除”。
- 串记：`biography` 串 `geography / geology / biography / biology`，用近形词群帮助区分；
  `distortion` 串 `distort / distorted / distortionist` 和近义词。
- 词根词缀：`unemployment` 拆 `un + employ + ment`；`flourishing` 拆 `flourish + ing`，
  同时补充 `flo / flora / floral / florist / flower`。
- 扩展：`extension` 列 `extent / extend / extensive / extension / expansion`；
  `conditioner` 列 `condition / conditioner / air conditioner`；
  `amenable` 列 `amiable / amicable / amenable / affable / affinity / amenity`。
- 联想：`sibling` 用“姐妹、兄弟、拎着手”的画面绑定“兄弟姐妹”。
- 辨析：`gigantic` 对比 `huge / titanic / enormous / immense / giant / gigantic / vast /
  massive / colossal / tremendous`，每个词说明差异。
- 助记：本次可见列表未命中“助记”标签样本。生成规范中将其定义为短场景或动作钩子，
  用于没有可靠词根、词族、形近串记、谐音或辨析时，不能写成释义复述。

## User Goals

1. 每个付费词书词条都有能帮助记忆的 `badge` 和 `text`。
2. 生成结果按不同助记类型写出不同结构，而不是所有类型都套同一种模板。
3. 词根词缀、扩展、串记、辨析、联想、谐音、助记的类型边界清楚。
4. 输出可以直接被当前 `premium_word_mnemonics.json` 消费，不改前端数据契约。

## Non-Goals

- 不改两本付费词书的单词、释义、音标、章节结构。
- 不新增前端字段或 UI。
- 不把第三方样本文案原样搬入词书，只抽取写法模式。
- 不用低俗、暴力、自伤、人名地名硬编、伪词根或拗口音译制造记忆点。

## Output Contract

生成文件仍为 `vocabulary_data/premium_word_mnemonics.json`：

```json
{
  "manifest_version": 1,
  "book_ids": ["ielts_listening_premium", "ielts_reading_premium"],
  "generated_at": "ISO-8601 UTC",
  "items": {
    "word": {
      "word": "word",
      "badge": "词根词缀",
      "text": "短中文助记内容",
      "book_ids": ["ielts_reading_premium"],
      "source": "premium_word_mnemonics"
    }
  }
}
```

`badge` 只能取以下值之一：`词根词缀`、`扩展`、`串记`、`辨析`、`联想`、`谐音`、`助记`、
`词源`、`口诀`。本轮优先使用前七类；`词源` 和 `口诀` 仅在确有证据或表达非常自然时使用。

## Type Rules

### 词根词缀

适用：目标词有真实、常见、可解释的词根词缀或透明派生结构。

写法：
- 用 `前缀/词根/后缀 -> 中文义` 的短链条说明。
- 必须落回目标释义，不只列拆分。
- 可以补 1 到 3 个同根词，但不要写成长词典条。

示例形态：
- `un + employ + ment：un 表否定，employ 是雇佣，合起来就是“不被雇佣”的失业状态。`

### 扩展

适用：目标词适合通过词族、派生、复合词、固定搭配建立记忆。

写法：
- 列 2 到 5 个相关词或搭配。
- 每个相关词都要服务目标词义，不做无关堆砌。
- 可用一行总结目标词在词族中的位置。

示例形态：
- `extend 是延伸，extension 是延伸出的部分；extensive 是广泛的，三者都围绕“向外展开”。`

### 串记

适用：形近词、同根近形词、易混拼写组。

写法：
- 把 2 到 5 个近形词排成一组。
- 明确目标词和其他词的差异点。
- 不制造不存在的词根。

示例形态：
- `bio 是生命，graphy 是书写；biography 写人的一生，biology 学生命本身。`

### 辨析

适用：近义词、考试中常混的含义或使用场景。

写法：
- 对比 2 到 5 个近义词即可，优先短而清楚。
- 必须说出目标词的独特使用边界。
- 禁止只列同义词。

示例形态：
- `gigantic 强调面积或体积巨大；huge 更泛，vast 偏空间辽阔，massive 偏规模和重量。`

### 联想

适用：可以用词形、画面、考试场景或自然动作把词义挂住，但不是严格词根词缀。

写法：
- 需要一个可视化或动作化钩子。
- 可以轻度拆词形，但必须说明这是联想，不冒充词根。
- 文案要短，重点是“看到词能想起义”。

示例形态：
- `sibling 想成姐妹和兄弟手拉手站在一起，记“兄弟姐妹”。`

### 谐音

适用：读音和中文提示自然、顺口、不会低俗或误导。

写法：
- 一句话完成，不长篇解释。
- 谐音必须服务中文义。
- 不使用拗口音译、羞辱性、低俗或暴力画面。

示例形态：
- `abolish 可借“暴力史”记：一段不该存在的暴力历史要被废除。`

### 助记

适用：没有可靠词根、扩展、串记、辨析、谐音时，用短场景/动作绑定核心义。

写法：
- 1 个具体场景或动作。
- 必须包含目标中文义关键词。
- 禁止“先抓核心义”“放回句子判断”“这个词表示……”。

示例形态：
- `ferry 想成码头一班船来回摆渡，把人和车渡过去，记“渡船；渡运”。`

## Generation Policy

1. 先为每个词选择最合适的单一 `badge`，不要强行平均分布。
2. 类型优先级：真实词根词缀 > 辨析 > 扩展 > 串记 > 联想 > 谐音 > 助记。
3. 对派生词和复数词不要只写“是某词的复数/现在分词”，必须说明它在原词义上的变化。
4. 短语必须用场景或搭配记，禁止逐词硬拆。
5. 每条 `text` 12 到 90 个中文字符左右，必要时可到 120，但不能写成长篇词典。
6. 每条必须显式包含至少一个中文释义关键词。
7. 如果模型不确定真实词根，必须降级到扩展、联想或助记，不能编造。

## Quality Gates

生成后必须通过：

- 覆盖两本付费词书去重并集，无缺失、无陈旧词。
- `backend/tests/test_premium_vocab_books.py`。
- `backend/tests/test_word_memory_note_llm_client.py`。
- `backend/tests/test_word_detail_llm_client.py`。
- 模板句扫描为 0：`先抓核心义`、`放回句子判断`、`核心义仍是`、`记住它常落在`。
- 抽样人工检查至少覆盖七类：`词根词缀`、`扩展`、`串记`、`辨析`、`联想`、`谐音`、`助记`。

## Implementation Plan

1. 更新 MiniMax 调用兼容层：使用 `max_completion_tokens`，解析前移除 `<think>` 块。
2. 将本 PRD 的类型规则压缩进 `word_memory_note_llm_client` 的系统提示词。
3. 用 `MiniMax-M2.7-highspeed` 重跑 `premium_word_mnemonics.json`，覆盖现有结果。
4. 跑质量扫描和相关测试。
5. 如果某一类质量明显偏弱，按失败样本补充提示词或局部重跑。
