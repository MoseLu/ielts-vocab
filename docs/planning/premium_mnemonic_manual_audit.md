# Premium Mnemonic Manual Audit

Updated: 2026-05-11

This audit applies the real idictation word-card pattern index from `/Users/mose/Documents/Codex/2026-05-10/chrome-plugin-chrome-openai-bundled-chrome/雅思词汇助记规律索引.md` to the current manual TSV at `vocabulary_data/premium_word_mnemonics_manual.tsv`.

## Summary

Current implementation progress: `270 / 5493` paid-book entries have been manually rewritten and merged into `vocabulary_data/premium_word_mnemonics.json`.

| Batch | Rows | Status | Notes |
|---|---:|---|---|
| `manual-002` | 50 | merged | First corrected pass after the idictation sample index; fixes `education` away from roots-only direction. |
| `manual-003` | 50 | merged | Continued high-frequency listening answer words with scene, contrast, and real morpheme hooks. |
| `manual-004` | 50 | merged | Added map, travel, campus, sport, and basic comparison words with learner-facing contrasts. |
| `manual-005` | 50 | merged | Added nature, ticketing, field, material, and accommodation words; preserved the locked `accommodation` regression text. |
| `manual-006` | 70 | merged | Added review, flight, database, technical, exhibition, cost, behavior, and related forms. |

Initial 50-row audit result before rewriting:

| Decision | Count | Meaning |
|---|---:|---|
| 推翻重写 | 37 | Current entry is template-shaped or has the wrong primary mnemonic type. Re-author from scratch. |
| 局部重写 | 12 | Primary type is usable, but the current text still reads like metadata instead of a learner-facing memory hook. |
| 保留方向，重写表达 | 1 | `education` now has the correct primary type, but wording still needs original manual polish. |

Main issue: most rows describe fields rather than teach a learner how to remember the word. Many `roots_affixes` values are only `词根 + word itself`, which is not a real morpheme explanation.

## Audit Table

| # | Word | Current | Decision | Suggested | Reason |
|---:|---|---|---|---|---|
| 1 | art | 派生 | 推翻重写 | 扩展 | Use art/artist/artwork/artistic as a compact domain family, not a generic derivative row. |
| 2 | time | 辨析 | 推翻重写 | 辨析 | Keep time/period/timing contrast, but remove fake root metadata. |
| 3 | feed | 派生 | 推翻重写 | 串记 | Feed/food/fed/feeding should be a meaning chain around eating and giving food. |
| 4 | park | 串记 | 推翻重写 | 联想 | IELTS map/listening use needs place and parking-scene hooks. |
| 5 | week | 串记 | 推翻重写 | 串记 | Week/weekly/weekend is useful, but current root field is just the word. |
| 6 | fees | 派生 | 推翻重写 | 辨析 | Need fee/fare/fine/free contrast for listening money traps. |
| 7 | food | 辨析 | 局部重写 | 辨析 | Type is right, but text should teach food/feed/foods distinction plainly. |
| 8 | fish | 辨析 | 局部重写 | 辨析 | Type is right, but write animal/food/activity distinction as a usable note. |
| 9 | work | 扩展 | 推翻重写 | 扩展 | Work as job/task/artifact needs usage expansion, not `词根 work`. |
| 10 | city | 串记 | 推翻重写 | 联想 | Better as city-centre/map-location scene hook. |
| 11 | room | 辨析 | 局部重写 | 辨析 | Keep room/space/classroom contrast, rewrite learner-facing. |
| 12 | roads | 派生 | 推翻重写 | 联想 | Map-task road/main road/roadside scene is stronger than plural derivation. |
| 13 | study | 扩展 | 推翻重写 | 辨析 | Distinguish study as learning, research, and study room. |
| 14 | money | 扩展 | 推翻重写 | 联想 | Listening payment scene is more useful than a generic money family. |
| 15 | water | 扩展 | 推翻重写 | 联想 | Use drinking/fresh/running water scene contrasts. |
| 16 | music | 派生 | 推翻重写 | 扩展 | Use music/course/instrument/activity expansion. |
| 17 | local | 词根词缀 | 局部重写 | 词根词缀 | `loc` direction is okay; wording is still too template-like. |
| 18 | learn | 派生 | 推翻重写 | 扩展 | Learn/study/teach needs usage contrast more than derivatives. |
| 19 | light | 辨析 | 局部重写 | 辨析 | Keep light/lights/lighting distinction, rewrite with examples. |
| 20 | timing | 派生 | 推翻重写 | 辨析 | Timing is schedule/choice of time, not just time + -ing. |
| 21 | record | 辨析 | 局部重写 | 辨析 | Type is right; emphasize noun/verb stress and recording relation. |
| 22 | social | 词根词缀 | 局部重写 | 词根词缀 | `soci` direction is usable; text needs less formula. |
| 23 | lights | 派生 | 推翻重写 | 辨析 | Need lights vs light vs lighting. |
| 24 | garden | 派生 | 推翻重写 | 联想 | Place scene and gardening/gardener relation are more memorable. |
| 25 | market | 派生 | 推翻重写 | 扩展 | Market as place, demand, and sales channel needs expansion. |
| 26 | trains | 辨析 | 局部重写 | 辨析 | Keep transport/train-v distinction, rewrite cleaner. |
| 27 | people | 扩展 | 推翻重写 | 扩展 | Current `词根 people` is invalid as a mnemonic anchor. |
| 28 | parking | 派生 | 推翻重写 | 联想 | Strongest hook is car-park/listening-map scene. |
| 29 | records | 派生 | 推翻重写 | 辨析 | Records as files/history vs record as verb/noun. |
| 30 | fishing | 派生 | 推翻重写 | 联想 | Better as activity scene with fish/fishing/fisheries distinction. |
| 31 | feeding | 派生 | 推翻重写 | 联想 | Animal-care scene beats derivative metadata. |
| 32 | gardens | 派生 | 推翻重写 | 联想 | Map/location plural scene, not just garden + -s. |
| 33 | animals | 派生 | 推翻重写 | 扩展 | Use animal/species/wildlife/welfare family. |
| 34 | training | 派生 | 推翻重写 | 扩展 | Training course/skill/fitness should be expanded by scenario. |
| 35 | business | 词根词缀 | 局部重写 | 词根词缀 | Busy + -ness is valid, but current text needs a sharper hook. |
| 36 | learning | 派生 | 推翻重写 | 扩展 | Learning as process/education context, not just learn + -ing. |
| 37 | students | 派生 | 推翻重写 | 联想 | Student-card/course/accommodation scene works better. |
| 38 | research | 扩展 | 局部重写 | 扩展 | Direction is usable; rewrite as research/survey/study distinction. |
| 39 | lighting | 派生 | 推翻重写 | 辨析 | Lighting vs lights vs lightning is the real trap. |
| 40 | education | 谐音 | 保留方向，重写表达 | 谐音 | Corrected primary type; still needs original wording. |
| 41 | marketing | 派生 | 推翻重写 | 扩展 | Marketing/sales/market distinction should be usage-led. |
| 42 | recording | 派生 | 推翻重写 | 辨析 | Recording as audio/file/action should be separated. |
| 43 | foods | 派生 | 推翻重写 | 辨析 | Food as mass noun vs foods as types of food. |
| 44 | fishes | 辨析 | 推翻重写 | 辨析 | Current text is metadata; write fish/fishes/fishing contrast. |
| 45 | minutes | 辨析 | 局部重写 | 辨析 | Keep minutes as time and meeting notes distinction. |
| 46 | animal | 派生 | 推翻重写 | 扩展 | Animal/wildlife/species/welfare is a better family note. |
| 47 | student | 派生 | 推翻重写 | 联想 | Course/card/accommodation scenario is stronger. |
| 48 | gardening | 派生 | 推翻重写 | 联想 | Use garden activity scene and gardener/gardening contrast. |
| 49 | system | 扩展 | 推翻重写 | 扩展 | Current root is just the word; use system/structure/process context. |
| 50 | card | 辨析 | 局部重写 | 辨析 | Keep card/student card/credit card distinction, rewrite as memory note. |

## Replacement Rules

1. Do not mark a replacement `approved` until the row has a real learner-facing hook.
2. Keep `badge` aligned to the primary hook, not to a secondary tab.
3. Use `联想` for map, place, booking, payment, and classroom scenes when the scene is the real memory entry.
4. Use `roots_affixes` only when there is a genuine morpheme such as `loc`, `soci`, or `-ness`.
5. If a word is too basic for roots, write a usage contrast or IELTS listening scene instead.
