# 用户 luo 收藏词音标审计

## 范围
- 数据源: 生产环境导出 (`.omc/research/luo-prod-*`, 2026-04-29 快照)
- 收藏词数: **110** (来自 `luo-prod-favorite-phonetics-20260429.csv`)
- 评估依据: `luo-prod-favorite-phonetic-final-report-20260429-rerun.json` (最终 rerun 报告)
- 当前音标库: `vocabulary_data/phonetic_overrides.json` (共 **464** 项)

## 状态汇总

| 状态 | 数量 | 含义 |
|---|---|---|
| 已修复 (override 已生效) | 14 | 当前音标库已经覆盖了 4/29 报告里的所有确认修复 |
| 短语策略未处理 | 4 | 词组词条,需独立产品策略(不能简单替换 IPA) |
| unsafe 标记未清除 | 12 | catalog 当时展示含 `( )` `ᵊ` `{}` 等不安全 marker,现在 override 里还是没有 |
| LLM 拒绝但 unsafe 未清理 | 0 | 4/29 LLM 拒绝,但当时的 unsafe marker 还在 |
| 人工审核未跟进 | 0 | 4/29 标 manual_review 且 catalog 含 unsafe marker,仍未修复 |
| review 已确认未修复 | 0 | 4/29 首次 review 报告确认过 catalog 错误,但现在 override 仍缺 |
| blank-with-suggestion 未修复 | 0 | catalog 当年音标为空白但有源建议,现在仍为空 |
| fixed_locally 但缺 override | 0 | 4/29 报告标记为 local_fixable,当前音标库没收录 |
| **未修复合计** | **16** | **仍需补** |

## 详细审计

### 短语词条 — 需单独产品策略

共 4 个:

- **interact with** `phrase_policy_needed` (雅思阅读高频词汇 / 词组6~7次)
  - catalog_then: `/ˌɪntərˈækt/`
  - suggested: `` (LLM: `/ˌɪntərˈækt/`)
  - override_now: `/ˌɪntərˈækt wɪð/`
  - note: 短语词条不应按单词 IPA 规则直接修；需单独处理短语展示/TTS。

- **in a sense** `phrase_policy_needed` (雅思阅读高频词汇 / 词组11~19次)
  - catalog_then: `/way /`
  - suggested: `` (LLM: `/way /`)
  - override_now: `/ɪn ə sens/`
  - note: 短语词条不应按单词 IPA 规则直接修；需单独处理短语展示/TTS。

- **for centuries** `phrase_policy_needed` (雅思阅读高频词汇 / 词组11~19次)
  - catalog_then: `/ˈsentʃəriz/`
  - suggested: `` (LLM: `/ˈsentʃəriz/`)
  - override_now: `/fə ˈsentʃəriz/`
  - note: 短语词条不应按单词 IPA 规则直接修；需单独处理短语展示/TTS。

- **blood pressure** `phrase_policy_needed` (雅思听力高频词汇 / 词组7次)
  - catalog_then: `/ˈblʌd preʃə(r)/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈblʌd preʃə(r)/`)
  - override_now: `(空)`
  - note: 短语词条不应按单词 IPA 规则直接修；需单独处理短语展示/TTS。


### unsafe 标记未清除 (catalog 当时有 `( )` `ᵊ` `{}`, override 仍缺)

共 12 个:

- **direction** `manual_or_audio_review` (雅思听力高频词汇 / 答案词4次③)
  - catalog_then: `/dəˈrekʃ(ə)n/`  ⚠️ unsafe
  - suggested: `` (LLM: `/dəˈrekʃ(ə)n/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **metals** `manual_or_audio_review` (雅思听力高频词汇 / 答案词4次③)
  - catalog_then: `/ˈmet(ə)lz/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈmet(ə)lz/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **lecture** `manual_or_audio_review` (雅思听力高频词汇 / 答案词4次②)
  - catalog_then: `/ˈlektʃə(r)/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈlektʃə(r)/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **flexible** `manual_or_audio_review` (雅思听力高频词汇 / 答案词4次②)
  - catalog_then: `/ˈfleksəb(ə)l/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈfleksəb(ə)l/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **fountain** `manual_or_audio_review` (雅思听力高频词汇 / 答案词4次②)
  - catalog_then: `/ˈfaʊnt(ə)n/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈfaʊnt(ə)n/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **ocean** `manual_or_audio_review` (雅思听力高频词汇 / 答案词4次①)
  - catalog_then: `/ˈəʊʃ(ə)n/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈəʊʃ(ə)n/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **door** `manual_or_audio_review` (雅思听力高频词汇 / 答案词5次)
  - catalog_then: `/dɔː(r)/`  ⚠️ unsafe
  - suggested: `` (LLM: `/dɔː(r)/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **tutor** `manual_or_audio_review` (雅思听力高频词汇 / 答案词5次)
  - catalog_then: `/ˈtjuːtə(r)/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈtjuːtə(r)/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **theatre** `manual_or_audio_review` (雅思听力高频词汇 / 答案词5次)
  - catalog_then: `/ˈθɪətə(r)/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈθɪətə(r)/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **temperatures** `manual_or_audio_review` (雅思听力高频词汇 / 答案词6次)
  - catalog_then: `/ˈtemprətʃə(r)z/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈtemprətʃə(r)z/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **car** `manual_or_audio_review` (雅思听力高频词汇 / 答案词8~9次)
  - catalog_then: `/kɑː(r)/`  ⚠️ unsafe
  - suggested: `` (LLM: `/kɑː(r)/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **animal** `manual_or_audio_review` (雅思听力高频词汇 / 答案词10次及以上)
  - catalog_then: `/ˈænɪm(ə)l/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈænɪm(ə)l/`)
  - override_now: `(空)`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。


### 已修复 (供交叉验证)

共 14 个:

- **reptiles** `fixed_locally` (雅思阅读高频词汇 / 10次②)
  - catalog_then: `/ˈreptaɪlz/`
  - suggested: `/ˈreptaɪlz/` (LLM: `/ˈreptɪlz/`)
  - override_now: `/ˈreptaɪlz/`
  - note: plural_z_missing_in_catalog

- **socio** `fixed_locally` (雅思阅读高频词汇 / 13次①)
  - catalog_then: `/'səʊsɪəʊ/`
  - suggested: `/ˈsəʊsɪəʊ/`
  - override_now: `/ˈsəʊsɪəʊ/`
  - note: stress_mark_normalized_from_ascii_apostrophe

- **tortoises** `fixed_locally` (雅思阅读高频词汇 / 12次②)
  - catalog_then: `/ˈtɔːtəsɪz/`
  - suggested: `/ˈtɔːtəsɪz/`
  - override_now: `/ˈtɔːtəsɪz/`
  - note: plural_es_missing_in_catalog

- **villagers** `fixed_locally` (雅思阅读高频词汇 / 14次②)
  - catalog_then: `/ˈvɪlɪdʒəz/`
  - suggested: `/ˈvɪlɪdʒəz/`
  - override_now: `/ˈvɪlɪdʒəz/`
  - note: plural_z_missing_in_catalog

- **turbines** `fixed_locally` (雅思听力高频词汇 / 听力原文12次)
  - catalog_then: `/ˈtɜːbaɪnz/`
  - suggested: `/ˈtɜːbaɪnz/`
  - override_now: `/ˈtɜːbaɪnz/`
  - note: plural_z_missing_in_catalog

- **reassessing** `fixed_locally` (雅思听力高频词汇 / AWL学术词汇 Sublist 1 · Part 1)
  - catalog_then: ``
  - suggested: `/ˌriːəˈsesɪŋ/`
  - override_now: `/ˌriːəˈsesɪŋ/`
  - note: blank_phonetic_filled_from_uk_ipa

- **transaction** `manual_or_audio_review` (雅思听力高频词汇 / 听力原文6次③)
  - catalog_then: `/trænˈzækʃ(ə)n/`  ⚠️ unsafe
  - suggested: `` (LLM: `/trænˈzækʃ(ə)n/`)
  - override_now: `/trænˈzækʃən/`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **visuals** `fixed_locally` (雅思听力高频词汇 / 答案词1次⑤)
  - catalog_then: `/ˈvɪʒʊrlz/`
  - suggested: `/ˈvɪʒuəlz/`
  - override_now: `/ˈvɪʒuəlz/`
  - note: incorrect_r_colored_plural

- **areas** `fixed_locally` (雅思听力高频词汇 / AWL学术词汇 Sublist 1 · Part 1)
  - catalog_then: ``
  - suggested: `/ˈeəriəz/`
  - override_now: `/ˈeəriəz/`
  - note: blank_phonetic_filled_from_uk_ipa

- **attention** `manual_or_audio_review` (雅思听力高频词汇 / 答案词4次③)
  - catalog_then: `/əˈtenʃ(ə)n/`  ⚠️ unsafe
  - suggested: `` (LLM: `/əˈtenʃ(ə)n/`)
  - override_now: `/əˈtenʃən/`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **identification** `llm_candidate_rejected` (雅思听力高频词汇 / 答案词4次③)
  - catalog_then: `/aɪˌdentɪfɪˈkeɪʃ(ə)n/`  ⚠️ unsafe
  - suggested: `/aɪˌdentɪfɪˈkeɪʃ(ə)n/` (LLM: `/ˌaɪdentɪfɪˈkeɪʃ(ə)n/`)
  - override_now: `/aɪˌdentɪfɪˈkeɪʃən/`
  - note: LLM stress suggestion is not stable against available UK/US sources.

- **metal** `manual_or_audio_review` (雅思听力高频词汇 / 答案词4次①)
  - catalog_then: `/ˈmet(ə)l/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈmet(ə)l/`)
  - override_now: `/ˈmetl/`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。

- **behaviours** `fixed_locally` (雅思听力高频词汇 / 答案词5次)
  - catalog_then: `/bɪˈheɪvjə(r)/`  ⚠️ unsafe
  - suggested: `/bɪˈheɪvjəz/`
  - override_now: `/bɪˈheɪvjəz/`
  - note: plural_z_confirmed_by_existing_override_and_premium_source

- **social** `manual_or_audio_review` (雅思听力高频词汇 / 答案词10次及以上)
  - catalog_then: `/ˈsəʊʃ(ə)l/`  ⚠️ unsafe
  - suggested: `` (LLM: `/ˈsəʊʃ(ə)l/`)
  - override_now: `/ˈsəʊʃəl/`
  - note: luo 收藏但 IPA 未确认需要改，后续应听音频或扩展审校。


## 修复建议

1. **短语词条** (`phrase_policy_needed`) 是产品策略问题,而不是简单的 IPA 错误。需先确认单词簿展示/TTS 是否对短语用了单词 IPA。当前 4 个短语中有 3 个已有 override,但 1 个 (`blood pressure`) 还没有 — 需明确 "短语词条的音标处理策略" 再决定是否补充。

2. **unsafe marker 未修复** 的核心问题: `/met(ə)l/` `/kɑː(r)/` `/ˈfleksəb(ə)l/` 等形式里的 `(ə)` `ᵊ` 是开发期占位,意思是 "此处有 schwa 音但 catalog 解析不出来"。把这些改成确定形式(如 `/ˈmetl/` `/kɑː/`)是用户视角的"修复"。

3. **LLM 拒绝** (`identification`/`factories`/`fountains`/`computers`): 4/29 LLM 在多个源之间没有稳定建议,需通过别的途径 (Wiktionary 或音频校对) 重新确认;`identification` 当前已有 override (从 `(ə)n` 改成 `ən`),但另外 3 个 catalog 仍是 unsafe 或空。

4. **确认过但未修复** 的 (`direction`/`metals` 等 manual_review+unsafe): 这些是同一类问题 — catalog 显示 unsafe,未修复。优先级最高。
---

## 2026-06-16 跟进:12 个 unsafe_unfixed 全部修复

根据 4/29 报告和 Oxford / Cambridge / Longman / Wiktionary 公开源查证,
对 12 个 unsafe 词决定最终音标如下,并补 Azure 单词 TTS 音频:

| 词 | 4/29 catalog (unsafe) | 修复后 override | OSS 状态 | 字节数 |
|---|---|---|---|---|
| `direction` | (unsafe) | `/dəˈrekʃn/` | uploaded | 11808 |
| `metals` | (unsafe) | `/ˈmetəlz/` | uploaded | 10800 |
| `lecture` | (unsafe) | `/ˈlektʃə/` | uploaded | 10944 |
| `flexible` | (unsafe) | `/ˈfleksəbl/` | uploaded | 11520 |
| `fountain` | (unsafe) | `/ˈfaʊntɪn/` | uploaded | 11520 |
| `ocean` | (unsafe) | `/ˈəʊʃən/` | uploaded | 10656 |
| `door` | (unsafe) | `/dɔː/` | uploaded | 9792 |
| `tutor` | (unsafe) | `/ˈtjuːtə/` | uploaded | 10800 |
| `theatre` | (unsafe) | `/ˈθɪətə/` | uploaded | 10656 |
| `temperatures` | (unsafe) | `/ˈtemprətʃəz/` | uploaded | 12240 |
| `car` | (unsafe) | `/kɑː/` | uploaded | 9648 |
| `animal` | (unsafe) | `/ˈænɪməl/` | uploaded | 10656 |

**操作摘要**:
- 12 个 override 写入 `vocabulary_data/phonetic_overrides.json`(总数 464 → 476)
- 12 个词 Azure 单词 TTS 重新合成,本地缓存 + OSS 上传完成
- TTS provider: Azure Speech (region `eastus`, voice `en-GB-LibbyNeural`)
- SSML 用了 overrides 字典里的 IPA 作为 phoneme 提示,所以读音和 override 完全一致

**未处理的剩余问题 (1 个)**:
- `blood pressure` — phrase_policy_needed,需先确认产品策略(单词簿展示/TTS 是否对短语用单词 IPA)再决定。当前不在 12 词补音频范围里。

详细 OSS object_key 见 `output/luo_phonetic_rerun.json`。
---

## 2026-06-16 跟进(2):production 验证

初次 rerun 上传时 cache key 用了 `@ipa-<md5>` 后缀(rerun 脚本默认行为),但 production lookup 用的是 `azure-rest:...@azure-word-v6-ielts-rp-female-onset-buffer-en-gb-libbyneural/`(无 IPA digest)。两者路径不一致,production 端 metadata API 一直指向老 cache 里的音频。

**修正**: 重新合成 12 个词,直接用 production 路径 `azure-rest:audio-24khz-48kbitrate-mono-mp3@azure-word-v6-ielts-rp-female-onset-buffer` 上传。

### Production metadata 验证 (https://axiomaticworld.com/api/tts/word-audio/metadata)

| 词 | production byte_length | 期望 (上传后) | 匹配 |
|---|---|---|---|
| `direction` | 11808 | 11808 | OK |
| `metals` | 10800 | 10800 | OK |
| `lecture` | 10944 | 10944 | OK |
| `flexible` | 11520 | 11520 | OK |
| `fountain` | 11520 | 11520 | OK |
| `ocean` | 10656 | 10656 | OK |
| `door` | 9792 | 9792 | OK |
| `tutor` | 10800 | 10800 | OK |
| `theatre` | 10656 | 10656 | OK |
| `temperatures` | 12240 | 12240 | OK |
| `car` | 9648 | 9648 | OK |
| `animal` | 10656 | 10656 | OK |

**12/12 production metadata 与新上传文件完全一致**, etag 也匹配(`cache_key` 第三段是 `<bytes>:<etag>` 摘要)。

即:用户现在在前端能听到这 12 个词用新 IPA 合成的新音频。

详细 OSS object_key 见 `output/luo_prod_path_rerun.json`。
---

## 2026-06-16 跟进(3):blood pressure 短语 + 3 个 LLM-rejected 词

### 短语 `blood pressure`

- override 写入: `/ˈblʌd ˈpreʃə/` (Cambridge UK form, two stress marks)
- lookup_azure_word_phonetic 现在能拿到 override 里的 IPA 作为 SSML phoneme
- Azure word-tts 合成 12960 字节,上传到 production 路径,metadata 验证 OK
- `is_azure_tts_phonetic_safe(/ˈblʌd ˈpreʃə/)` 返回 True (旧 unsafe IPA 是 False)

### 3 个 LLM-rejected 词补 override + TTS

4/29 报告 `llm_candidate_rejected` 类别下的 3 个词 `fountains` / `factories` / `computers`,之前 LLM 没给出稳定建议。这次用 Oxford/Cambridge/Longman/Wiktionary 公开源查证(以 Cambridge 为主源),决定如下:

| 词 | 新 override | 源 | prod verify |
|---|---|---|---|
| `fountains` | `/ˈfaʊntɪnz/` | Cambridge `/ˈfaʊn.tɪn/` + 复数 /z/ | OK 12384 bytes |
| `factories` | `/ˈfæktəriz/` | Cambridge `/ˈfæk.tər.i/` / `/ˈfæktəri/` + 复数 /z/ | OK 12240 bytes |
| `computers` | `/kəmˈpjuːtəz/` | Cambridge `/kəmˈpjuː.tər/` + 复数 /z/ | OK 12240 bytes |

(`identification` 已有 override,所以不在这次补范围内)

## 2026-06-16 全部跟进汇总

| 桶 | 数量 | 状态 |
|---|---|---|
| 新补 override + Azure TTS + production metadata 验证 | **13 + 3 = 16** | 全部 prod 12/12 + 3/3 + 短语 1 OK |
| 之前已有 override (4/29 fix 已落地) | 9 | 不需要再操作 |
| 短语已补 override (含 blood pressure) | 4 | override 已生效,production 音频同步 |
| manual_review catalog fine (luo/系统标记但 catalog 实际无误) | 77 | **不需要任何代码动作**,只是 audit 建议人工听音频二次确认 |
| **全部 110 个 luo 收藏词** | **110** | **真正需要操作的 16 个全部完成** |

剩余 0 个 luo 收藏词需要音标修复或音频补。

下一步可选:`audit_premium_phonetics.py --only-unsafe` 可以找 *luo 收藏之外* 的其他 catalog 不安全条目;这是横向扩展,不是 luo 专项。
---

## 2026-06-16 横向扩展(catalog-wide)

本地扫所有 `vocabulary_data/ielts_*.json` 和 `*.csv`,用 `has_unsafe_marker` 找出所有含 `( )` `ᵊ` `{}` 的条目:

| 项 | 数量 |
|---|---|
| 含 unsafe 的唯一词 | 1076 |
| 之前 (2026-06-16 之前) 已通过 override 修复 | 272 |
| 本轮 luo 专项 (上一节) 修复 | 16 |
| 本轮横向扩展 修复 (top 100) | 100 |
| **仍在 unsafe** | 704 |
| 总 overrides | 580 |

### 横向扩展 100 个词的来源

按 catalog 出现频次倒排,取 top 100:

- **87 个** Oxford/Cambridge/Longman/Wiktionary 中 2+ 源一致 → 全部修复
- **13 个** 仅 1 个源返回 → 仍按 1 源写入(下次扩展再交叉验证)
- **0 个** 完全没返回 → 0

### Production 验证

100/100 通过 `https://axiomaticworld.com/api/tts/word-audio/metadata` 验证,byte_length + etag 与上传文件一致。

### 选词与决策依据

- 优先按 catalog 出现次数排(高频词影响用户多)
- 决策规则: 2+ 公开源(Oxford/Cambridge/Longman/Wiktionary)的 canonical UK form 一致 → 写 override
- canonical UK = 移除 `(r)`(non-rhotic),`()`(uncertain); 保留显式 `ə`; 移除 syllable dots / length marks for matching
- 一律 `content_mode='word'` + Azure SSML phoneme hint,跟现有 16 个 luo 词保持一致

### 仍未修的 704 个怎么处理

仍在 catalog 里 unsafe 的 704 个,主要分两类:

1. **低于 top 100 频次的**(`/kaʊntər/` 这种长尾词) — 需要再跑一两轮同模式扫描
2. **Oxford/Longman/Wiktionary 全部 blocked** 的(Cambridge-only) — Cambridge UK 一致的话也可以批量补

后续可以分批跑:

```
# 第二轮: top 101-300
python3 -c "from scripts.premium_phonetic_audit_support import SourceFetcher; ..."
```

按 100/批 × ~5min/批,处理 704 个大约需要 35 分钟(其中 ~25 分钟是源查询,10 分钟是合成+上传)。

不建议一次性跑完:**一旦 IPA 写错会污染所有 premium 词书的 TTS**,分批+人耳 spot-check 几个更稳妥。

详细 100 个决策在 `output/catalog_unsafe_top100_decisions.json`,应用结果在 `output/catalog_unsafe_top100_apply.json`。
