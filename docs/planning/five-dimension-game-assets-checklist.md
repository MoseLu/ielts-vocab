# 五维一体游戏模式素材缺少清单

Last updated: 2026-04-22

## 用途
- 用于整理“五维一体游戏模式”从“可运行”升级到“成熟游戏体验”还缺少的素材。
- 可直接发给美术、动效、音频同学作为交付清单。
- 当前项目代码已接入基础游戏流程，但素材层仍明显不足。

## 当前已接入素材概况
- 素材目录：`frontend/assets/game`
- 当前素材总数：129
- 当前文件格式：以 `.png` 为主，另含补充清单 `.json`
- 当前没有：
  - 音频文件
  - 动效文件
  - Rive / Spine / Lottie / GIF / MP4
  - 可拉伸面板源文件

## 当前关键素材尺寸现状
- `map_large.png`: `338x270`
- `map_small.png`: `165x146`
- `level_card_spell.png`: `86x147`
- `level_card_pronunciation.png`: `87x147`
- `level_card_definition.png`: `86x147`
- `level_card_speaking.png`: `87x147`
- `level_card_example.png`: `86x147`
- `hero_boy_idle.png`: `52x85`
- `bird_teacher_point_book.png`: `66x75`
- `robot_wave.png`: `58x80`

结论：当前静态 PNG 足够支撑“原型版”，不足以支撑“成熟游戏版”。

## 2026-04-22 补充包接入状态

### 已补充且已装配使用
- 地图主背景：
  - `map_background_desktop.png` `1920x1080`
  - `map_background_tablet.png` `1536x1024`
  - `map_background_mobile.png` `1080x1920`
- 地图分层：
  - `map_layer_far.png`
  - `map_layer_mid.png`
  - `map_layer_front.png`
- 五维场景大图：
  - `scene_spell.png`
  - `scene_pronunciation.png`
  - `scene_definition.png`
  - `scene_speaking.png`
  - `scene_example.png`
- 录音状态图：
  - `mic_idle.png`
  - `mic_recording.png`
  - `mic_recognizing.png`
  - `mic_permission_fail.png`
  - `mic_disconnected.png`
- 风格统一图标：
  - `icon_current.png`
  - `icon_notebook.png`
  - `icon_reward.png`
  - `icon_target.png`

### 这批补充包解决了什么
- 地图页已不再依赖低分辨率 `map_large.png`
- 五维关卡已有统一风格的大场景底图
- 录音玩法已有独立状态视觉，不再只靠文字提示

### 这批补充包仍未覆盖的核心缺口
- 音频素材
- 角色动效
- UI 状态图层
- 结算与奖励动画
- 五维场景移动端竖版图
- 体力不足 / 网络异常 / 回流区空态等系统状态插图

## 交付优先级定义
- `P0`：必须补齐，否则游戏完成度不足
- `P1`：强烈建议补齐，否则体验明显偏弱
- `P2`：增强项，可在首版后补

---

## P0 必须补齐

### 1. 地图主背景
| 项目 | 数量 | 建议规格 | 用途 | 优先级 |
|---|---:|---|---|---|
| 地图主背景（桌面横版） | 1 | `1920x1080` PNG/WebP | `/game` 地图首页主背景 | P0 |
| 地图主背景（平板横版） | 1 | `1536x1024` PNG/WebP | 平板布局适配 | P0 |
| 地图主背景（手机竖版） | 1 | `1080x1920` PNG/WebP | 移动端地图页 | P0 |
| 地图分层前景/中景/远景 | 3-6 层 | 透明 PNG | 视差、镜头裁切、响应式重组 | P0 |

验收要求：
- 宽屏和手机都能铺满，不拉伸、不糊。
- 重要路径、节点、地标在安全区内。

### 2. 五个关卡的大场景背景
| 关卡 | 数量 | 建议规格 | 用途 | 优先级 |
|---|---:|---|---|---|
| 拼写强化场景 | 1-2 | `1600x900` 以上 | 关卡战斗主场景 | P0 |
| 发音训练场景 | 1-2 | `1600x900` 以上 | 发音关主场景 | P0 |
| 释义理解场景 | 1-2 | `1600x900` 以上 | 释义选择关 | P0 |
| 口语录音场景 | 1-2 | `1600x900` 以上 | 录音关 / Boss 关 | P0 |
| 例句应用场景 | 1-2 | `1600x900` 以上 | 例句填空 / 选词应用 | P0 |

说明：
- 当前 5 张 `level_card_*.png` 只能做卡牌，不够做完整战斗舞台。
- 最好每关再补一个移动端安全裁切版本。

### 3. 角色动效
| 角色 | 动作 | 数量 | 建议格式 | 优先级 |
|---|---|---:|---|---|
| 主角男孩 | idle / run / cheer / fail / level-up / recording | 6 | Rive / 序列帧 PNG | P0 |
| 主角女孩 | idle / run / cheer / fail / level-up / recording | 6 | Rive / 序列帧 PNG | P0 |
| 老师鸟 | idle / point / wave / approve / remind | 5 | Rive / 序列帧 PNG | P0 |
| 机器人 | idle / wave / scan / alert / hint | 5 | Rive / 序列帧 PNG | P0 |

说明：
- 当前项目里有静态姿态图，但缺动态表现。
- 若首版资源不足，至少先补：`idle / run / cheer / recording`。

### 4. 奖励与结算动画
| 项目 | 数量 | 建议格式 | 用途 | 优先级 |
|---|---:|---|---|---|
| 宝箱开启动画 | 4 套 | 序列帧 / Spine / Rive | normal / sapphire / golden / special | P0 |
| 星级结算动画 | 4 套 | 序列帧 / Lottie | 0 / 1 / 2 / 3 星结算 | P0 |
| 金币飞入动画 | 1 套 | 序列帧 / Lottie | 结算奖励 | P0 |
| 宝石飞入动画 | 1 套 | 序列帧 / Lottie | 稀有奖励 | P0 |
| 关卡解锁闪光 | 1 套 | 序列帧 / Lottie | 点亮下一维 | P0 |
| 连击火焰 | 1 套 | 序列帧 / Lottie | 连击表现 | P0 |

### 5. 按钮与面板完整状态
| 组件 | 状态 | 数量 | 建议格式 | 优先级 |
|---|---|---:|---|---|
| 主按钮 | default / hover / pressed / disabled | 4 | 9-slice PNG / 大图源文件 | P0 |
| 次按钮 | default / hover / pressed / disabled | 4 | 9-slice PNG / 大图源文件 | P0 |
| 危险按钮 | default / disabled | 2 | 9-slice PNG / 大图源文件 | P0 |
| 地图 dock 面板 | 1 套 | 9-slice PNG | 地图底部信息栏 | P0 |
| 结算面板 | 1 套 | 9-slice PNG | 通关 / 失败结算 | P0 |
| 提示条 | success / warning / error | 3 | 9-slice PNG | 状态反馈 | P0 |

说明：
- 当前 `button_green.png / button_yellow.png / panel_*` 数量不够，且状态不完整。
- 最好提供可拉伸设计源，避免前端硬撑。

### 6. 录音玩法专用反馈素材
| 项目 | 数量 | 建议规格 | 用途 | 优先级 |
|---|---:|---|---|---|
| 麦克风默认图 | 1 | 64x64 / 128x128 | 录音按钮 | P0 |
| 录音中动态图 | 1 | 动效或序列帧 | 录音状态 | P0 |
| 识别中波形 | 1 | 动效或序列帧 | 处理中状态 | P0 |
| 麦克风权限失败图 | 1 | 插图/图标 | 权限失败提示 | P0 |
| 语音服务断连图 | 1 | 插图/图标 | 服务异常提示 | P0 |

### 7. 音频素材
| 项目 | 数量 | 建议格式 | 用途 | 优先级 |
|---|---:|---|---|---|
| 地图 BGM | 1 | `.mp3` / `.ogg` | 地图主页 | P0 |
| 普通关卡 BGM | 1 | `.mp3` / `.ogg` | 五维关卡 | P0 |
| Boss 关 BGM | 1 | `.mp3` / `.ogg` | Boss 关压迫感 | P0 |
| 通关结算 BGM | 1 | `.mp3` / `.ogg` | 成功结算 | P0 |
| 失败结算 BGM | 1 | `.mp3` / `.ogg` | 失败 / 回流 | P0 |
| 点击音效 | 1 | `.wav` / `.ogg` | 通用 UI | P0 |
| 正确音效 | 1 | `.wav` / `.ogg` | 判定通过 | P0 |
| 错误音效 | 1 | `.wav` / `.ogg` | 判定失败 | P0 |
| 翻卡音效 | 1 | `.wav` / `.ogg` | 关卡卡片切换 | P0 |
| 星星音效 | 1 | `.wav` / `.ogg` | 评分结算 | P0 |
| 金币音效 | 1 | `.wav` / `.ogg` | 奖励飞入 | P0 |
| 宝箱音效 | 1 | `.wav` / `.ogg` | 宝箱开启 | P0 |
| 解锁音效 | 1 | `.wav` / `.ogg` | 下一关点亮 | P0 |
| 录音开始/结束音效 | 2 | `.wav` / `.ogg` | 录音交互反馈 | P0 |

建议按音频设计类型继续细分：
- 动作 SFX：点击、正确/错误、连击、解锁、宝箱、金币、录音开始/结束
- 环境氛围音：森林、城堡、水域、风声、鸟鸣
- UI/UX 提示音：按钮 hover、面板弹出、切页、提示条
- 角色音效：主角、导师、机器人拟音或语音
- 自适应音轨：依据紧张度或奖励反馈叠加层

建议额外提供：
- 文件命名规范
- 采样率与码率说明
- 每个音频的触发条件

### 8. 系统状态插图
| 项目 | 数量 | 用途 | 优先级 |
|---|---:|---|---|
| 体力不足 | 1 | 地图页不能开局 | P0 |
| 场景生成中 | 1 | AI 配图未回填时 | P0 |
| 场景生成失败 | 1 | 配图 fallback | P0 |
| 网络失败 | 1 | API / 语音异常 | P0 |
| 回流区为空 | 1 | 回流区空态 | P0 |
| 关卡锁定 | 1 | 未解锁维度 | P0 |

---

## P1 强烈建议补齐

### 9. HUD 与功能图标补全
当前已有部分图标，但还缺业务闭环。

需要补充：
- 任务
- 成就
- 排行榜
- 邮件
- 背包
- 奖励领取
- 重试
- 麦克风错误
- 网络重试
- 加载中

建议规格：
- `24x24`、`32x32`、`64x64`
- 统一风格

### 10. 章节/Boss 专属视觉
需要：
- 普通章节牌
- Boss 关专属徽记
- 奖励关专属徽记
- 回流区专属标识
- 新章节开启横幅

### 11. 引导与过场素材
需要：
- 首次进入地图引导
- 首次录音引导
- 首次解锁五维说明
- 新关卡开启提示

额外建议：
- 手势提示
- 教程箭头
- 步骤编号
- 对话框尾巴/气泡指向件

### 12. 多端裁切版本
建议为所有核心大图补：
- 桌面横版
- 平板横版
- 手机竖版
- 安全区说明图

---

## P2 增强项

### 13. 个性化与皮肤
- 主角换装
- 节日主题地图
- 宝箱皮肤
- 赛季主题 UI

### 14. 商店/背包/成就页专属背景
- 商店背景
- 背包背景
- 成就墙背景
- 排行榜背景

### 15. 扩展道具表现
当前目录已有部分静态道具，可增强为完整系统：
- potion
- key
- scroll
- shield
- ticket
- badge 系列

建议补：
- 悬浮状态
- 领取状态
- 使用状态

### 16. 任务 / 成就 / 社交 / 商店扩展
- 每日任务图标
- 成就徽章
- 排行榜段位图标
- 好友头像框
- 邀请/分享按钮
- 商品分类图标
- 背包格子
- 折扣标签

### 17. 无障碍增强资源
- 高对比度按钮版本
- 色盲友好图标版本
- 重要状态的非颜色区分样式
- 更大字号版本的关键提示图

---

## 当前可复用素材

### 已有、可继续使用
- 地图节点：`map_node1~5.png`
- 地图地标：`map_forest / map_lake / map_mountain / map_castle`
- 关卡卡面：`level_card_*`
- 静态角色：`hero_* / bird_teacher_* / robot_*`
- 奖励图标：`coin / diamond / exp / heart / chest_* / star*`
- 基础图标：`icon_*`
- 基础面板：`panel_* / ribbon_blue / label_wood`
- 装饰元素：`dec_*`

### 不建议继续直接充当成熟主视觉的素材
- `map_large.png`
- `map_small.png`
- `level_card_*`
- 大部分角色小图

原因：
- 分辨率太低
- 只能做小组件，不能做主场景
- 无法支撑高质量过场与动画

---

## 建议交付顺序
1. 地图背景大图
2. 五关场景大图
3. 角色基础动效
4. 录音玩法反馈素材
5. 结算与奖励动画
6. 按钮/面板完整状态
7. BGM 与关键音效
8. 系统状态插图
9. HUD 补图
10. 引导与过场

---

## 建议文件命名规范

### 地图
- `map_bg_desktop.png`
- `map_bg_tablet.png`
- `map_bg_mobile.png`
- `map_layer_far.png`
- `map_layer_mid.png`
- `map_layer_front.png`

### 五维场景
- `scene_spelling_desktop.png`
- `scene_pronunciation_desktop.png`
- `scene_definition_desktop.png`
- `scene_speaking_desktop.png`
- `scene_example_desktop.png`

### 动效
- `hero_boy_idle_0001.png ...`
- `hero_boy_run_0001.png ...`
- `teacher_wave.riv`
- `robot_scan.riv`
- `chest_golden_open_0001.png ...`

### 音频
- `bgm_map.mp3`
- `bgm_stage.mp3`
- `bgm_boss.mp3`
- `sfx_click.wav`
- `sfx_correct.wav`
- `sfx_wrong.wav`
- `sfx_chest_open.wav`
- `sfx_record_start.wav`
- `sfx_record_end.wav`

---

## 一句话总结
当前项目已经不缺“原型图标”，缺的是“能把五维模式真正做成成熟游戏”的主视觉、动效和音频资产。
