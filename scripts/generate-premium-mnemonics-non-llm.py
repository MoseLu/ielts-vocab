#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv
import json, re
from difflib import SequenceMatcher
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; VOCAB = ROOT / 'vocabulary_data'
BOOK_FILES = {
    'ielts_listening_premium': 'ielts_listening_premium.json',
    'ielts_reading_premium': 'ielts_reading_premium.json',
}
SOURCE = 'premium_word_mnemonics'; BADGES = {'助记', '联想', '词根词缀', '辨析', '串记', '扩展'}
LOW_QUALITY_RE = re.compile(
    r'词形尾巴|固定表达整体记|先抓核心义|放回句子判断|核心义仍是|'
    r'使用场景，再回到例句里确认|看到 [a-z][a-z -]* 时'
)
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
WORD_TOKEN_RE = r"[a-z]+(?:[-'][a-z]+)*(?:'s?)?"; WORD_RE = re.compile(rf"^{WORD_TOKEN_RE}(?: {WORD_TOKEN_RE})*$")
PREFIXES = {'anti': '反对/抵抗', 'auto': '自动/自己', 'bio': '生命', 'co': '共同', 'com': '共同/加强', 'con': '共同/加强', 'de': '向下/去除', 'dis': '分开/否定', 'en': '使进入某状态', 'em': '使进入某状态', 'ex': '向外', 'extra': '额外/外部', 'fore': '预先/前面', 'im': '否定/进入', 'in': '否定/进入', 'inter': '相互/之间', 'ir': '否定', 'il': '否定', 'micro': '微小', 'mid': '中间', 'mis': '错误', 'multi': '多', 'non': '非/不', 'out': '向外/超过', 'over': '过度/在上', 'post': '之后', 'pre': '预先/在前', 'pro': '向前/支持', 're': '再次/向后', 'sub': '在下/次级', 'super': '在上/超出', 'trans': '跨越/转变', 'un': '否定/解除', 'under': '不足/在下'}
SUFFIXES = [
    ('ization', '名词后缀，表示过程或结果'), ('isation', '名词后缀，表示过程或结果'),
    ('ational', '形容词后缀，表示“与...有关”'), ('fulness', '名词后缀，表示性质'),
    ('lessness', '名词后缀，表示缺少某性质'), ('ability', '名词后缀，表示能力或性质'),
    ('ibility', '名词后缀，表示能力或性质'), ('ically', '副词后缀，表示方式'),
    ('ation', '名词后缀，表示动作或结果'), ('ition', '名词后缀，表示动作或结果'),
    ('sion', '名词后缀，表示动作或结果'), ('tion', '名词后缀，表示动作或结果'),
    ('ment', '名词后缀，表示结果或状态'), ('ness', '名词后缀，表示性质'),
    ('ance', '名词后缀，表示状态或行为'), ('ence', '名词后缀，表示状态或行为'),
    ('ship', '名词后缀，表示身份或关系'), ('hood', '名词后缀，表示身份或阶段'),
    ('able', '形容词后缀，表示“能够/适合”'), ('ible', '形容词后缀，表示“能够/适合”'),
    ('less', '形容词后缀，表示缺少'), ('ful', '形容词后缀，表示充满'),
    ('ive', '形容词后缀，表示倾向或性质'), ('ous', '形容词后缀，表示具有某性质'),
    ('al', '形容词后缀，表示“与...有关”'), ('ic', '形容词后缀，表示性质'),
    ('ical', '形容词后缀，表示性质'), ('ary', '形容词/名词后缀，表示相关'),
    ('er', '人或物后缀'), ('or', '人或物后缀'), ('ist', '人或主义后缀'),
    ('ism', '主义/观念后缀'), ('ly', '副词后缀，表示方式'), ('ed', '过去或被动标记'),
    ('ing', '动作进行或名词化标记'), ('es', '复数或第三人称标记'), ('s', '复数或第三人称标记'),
]
ROOTS = [
    ('anthrop', '人类'), ('archae', '古代'), ('aud', '听'), ('bell', '战争'),
    ('bene', '好'), ('bio', '生命'), ('capit', '头/首要'), ('capt', '抓取'),
    ('cept', '拿取'), ('cip', '拿取'), ('chron', '时间'), ('cid', '切/杀'),
    ('cide', '杀'), ('claim', '喊叫'), ('clar', '清楚'), ('clud', '关闭'),
    ('clus', '关闭'), ('cogn', '认识'), ('corp', '身体/团体'), ('cred', '相信'),
    ('curr', '跑/流动'), ('curs', '跑'), ('dem', '人民'), ('dict', '说'),
    ('duc', '引导'), ('duct', '引导'), ('dur', '持续/坚硬'), ('equ', '相等'),
    ('facil', '容易'), ('fact', '做'), ('fect', '做'), ('fer', '携带'),
    ('fin', '边界/结束'), ('flex', '弯曲'), ('form', '形状'), ('fract', '破裂'),
    ('gen', '产生'), ('geo', '地球/土地'), ('grad', '步级'), ('graph', '书写/图像'),
    ('gress', '行走'), ('hab', '拥有/居住'), ('ject', '投掷'), ('jud', '判断'),
    ('junct', '连接'), ('labor', '劳动'), ('later', '边'), ('lect', '选择/阅读'),
    ('leg', '法律/选择'), ('liber', '自由'), ('loc', '地方'), ('log', '说/学科'),
    ('lumin', '光'), ('magn', '大'), ('manu', '手'), ('mater', '母/材料'),
    ('meter', '测量'), ('migr', '迁移'), ('min', '小'), ('miss', '送出'),
    ('mit', '送出'), ('mob', '移动'), ('mot', '移动'), ('mov', '移动'),
    ('mort', '死亡'), ('nat', '出生'), ('nom', '名称/规则'), ('norm', '标准'),
    ('oper', '工作'), ('path', '感受/疾病'), ('ped', '脚/儿童'), ('pel', '推动'),
    ('pend', '悬挂'), ('phon', '声音'), ('photo', '光'), ('plic', '折叠'),
    ('popul', '人民'), ('port', '搬运/港口'), ('pos', '放置'), ('press', '压'),
    ('psych', '心理'), ('rupt', '破裂'), ('scrib', '写'), ('script', '写'),
    ('sect', '切分'), ('sens', '感觉'), ('sequ', '跟随'), ('serv', '服务/保存'),
    ('sign', '标记'), ('sist', '站立'), ('solv', '松开/解决'), ('spec', '看'),
    ('spect', '看'), ('spir', '呼吸'), ('stat', '站立/状态'), ('struct', '建造'),
    ('tact', '接触'), ('tele', '远'), ('tempor', '时间'), ('tend', '伸展'),
    ('tens', '伸展'), ('terr', '土地'), ('therm', '热'), ('tract', '拉'),
    ('tribut', '给予/分配'), ('urb', '城市'), ('vac', '空'), ('val', '价值/力量'),
    ('ven', '来'), ('vent', '来'), ('vers', '转'), ('vert', '转'), ('vid', '看'),
    ('vis', '看'), ('viv', '生命'), ('voc', '声音/呼唤'), ('volv', '卷/转'),
]
PREP_MEANING = {'about': '关于', 'after': '之后', 'against': '反对/抵着', 'along': '沿着', 'around': '周围', 'as': '作为/像', 'at': '点位', 'by': '凭借/在旁', 'for': '为了/面向', 'from': '来源', 'in': '内部/范围', 'into': '进入', 'of': '所属/内容', 'off': '离开', 'on': '接触/关于', 'over': '覆盖/超过', 'through': '穿过/凭借', 'to': '方向/对象', 'under': '在下/不足', 'up': '向上/完成', 'with': '伴随/使用', 'without': '没有'}
REF_OVERRIDES = {'more': '更多', 'than': '比', 'much': '很/许多', 'few': '少数', 'less': '更少', 'most': '最/最多', 'front': '前面', 'card': '卡片', 'catalog': '目录', 'catalogue': '目录', 'direct': '直接的', 'fit': '健康的/适合的', 'life': '生活', 'point': '点/指出', 'so': '如此', 'like': '喜欢', 'make': '做/进行', 'sport': '运动', 'bacterium': '细菌', 'sprain': '扭伤', 'bud': '芽', 'impress': '留下印象', 'convict': '定罪', 'listen': '听', 'increase': '增加', 'beneficiary': '受益人', 'beneficiaries': '受益人', 'benefit': '益处/有益于', 'park': '停车/公园', 'sink': '下沉/水槽', 'attribute': '归因/属性', 'addict': '上瘾者/使沉迷', 'advocate': '倡导者/提倡', 'analyst': '分析者', 'agency': '机构/代理处', 'par': '标准杆/票面价值', 'post': '张贴/岗位/邮件', 'book': '书/预订', 'bath': '洗澡/浴缸', 'load': '装载/大量', 'plummet': '骤降/垂直落下', 'select': '选择/挑选', 'play': '玩/戏剧', 'wrought': '造成的/精制的', 'flyover': '立交桥/飞越', 'metres': '米', 'metallic': '金属的', 'formulae': '公式', 'formulate': '制定/构想', 'favour': '支持/好感', 'favor': '支持/好感', 'base': '底部/基础', 'enough': '足够的', 'adverb': '副词', 'field': '领域/田野', 'though': '虽然', 'even': '甚至/即使', 'airliner': '客机', 'alcoholism': '酗酒', 'alcoholic': '含酒精的/酗酒者', 'one': '一', 'sort': '分类/整理', 'further': '进一步的', 'last': '上一个/最近的', 'too': '太/过于', 'player': '运动员/参与者', 'consistently': '一贯地', 'consistency': '一致性'}
UNSAFE_DERIVATION_BASES = {'port', 'tail', 'intern', 'inform', 'remark', 'miner', 'critic', 'politic', 'both', 'hung'}
MANUAL_NOTES = {'mate': ('扩展', 'mate 核心是“配在一起”：人是伙伴/伴侣，动物是交配；workmate、schoolmate、teammate 都是同伴。'), 'demographic': ('词根词缀', 'demo 表“人群”，graphic 表“图表/描述”，合起来就是人口统计的、人口的。'), 'secrete': ('联想', 'secret 是秘密，secrete 可记“把东西藏起来”；在生物语境中是腺体分泌液体。'), 'accommodation': ('词根词缀', 'accommodate 是“容纳/提供住宿”，accommodation 就是住处或住宿安排。'), 'have a look': ('扩展', 'have a look 是固定口语表达，意思是“看一下”。'), 'quit': ('辨析', 'quit 比 quiet 少一个 e，e 退出队伍，记“离开；停止；辞职”。'), 'quiz': ('助记', 'quiz 常出现在课堂或节目语境，指知识竞赛或小测验。'), 'quiet': ('辨析', 'quiet 比 quit 多一个 e，像嘘声拉长让环境安静下来，记“安静的”。'), 'quick': ('辨析', 'quick 和 quit/quiet 同属 qu 开头易混词，quick 只记速度“快的；迅速的”。'), 'quote': ('扩展', 'quote 作动词是引用或报价，作名词是引文或报价；阅读中看价格还是文字出处。'), 'in a sense': ('扩展', 'in a sense 是固定表达，意思是“在某种意义上；从某种角度说”。'), 'universe': ('词根词缀', 'uni 表“一”，vers 有“转成整体”的线索；universe 是万物合成的整体，记“宇宙”。'), 'cuttings': ('扩展', 'cuttings 在听力里常指 newspaper cuttings，记作“剪报/剪下来的资料”，不是“锋利的”的复数。'), 'tortoises': ('助记', 'tortoises 先按动物义记“乌龟/陆龟”；例句里说能活很久，别被“行动迟缓的人”带偏。'), 'witnessed': ('词根词缀', 'witness 作动词是“目击/见证”；witnessed 就是过去式，记“目睹了；见证了”。'), 'entail': ('扩展', 'entail 表示“必然涉及/需要”，常用于说明一个计划会带来哪些要求或后果。'), 'insist': ('扩展', 'insist 记“坚持认为；坚决要求”，重点是态度很强，不是普通地 say。'), 'versa': ('扩展', 'versa 常见于 vice versa，整组记“反过来也一样”。'), 'turn on': ('扩展', 'turn on 是“打开灯或机器”；和 turn to“求助于”分开记。'), 'work with': ('扩展', 'work with 在听力里多指“与...共事/合作”；别只按“对...起作用”理解。'), 'so few': ('扩展', 'so few 表“如此少”，修饰可数名词；few 本身就抓数量少。'), 'straight away': ('扩展', 'straight away 是固定副词短语，直接记“立即；马上”。'), 'pronounced': ('扩展', 'pronounced 作形容词常指“明显的”，如 pronounced accent 是明显的口音；也可作 pronounce 的过去式。'), 'acknowledgement': ('扩展', 'acknowledgement 可表示“承认”，也常用于“感谢/致谢”；例句里 received an acknowledgement 是收到感谢。'), 'sweater': ('助记', 'sweater 直接记“毛衣”；不要按“出汗”义硬拆成派生词。'), 'agents': ('词根词缀', 'agent 是“代理人/经纪人”，agents 是复数，记“代理人；代理商”。'), 'agencies': ('词根词缀', 'agency 是“机构/代理处”，agencies 是复数，记“代理处；机构”。'), 'selected': ('词根词缀', 'select 是“选择/挑选”，selected 是过去分词或形容词，记“被选出的；精选的”。'), 'bath': ('辨析', 'bath 记“洗澡；浴缸”，bathe 是“洗澡/游泳”的动词，batch 是“一批/一组”。'), 'metres': ('词根词缀', 'metre 是“米”，metres 是复数，记“米；公尺”。'), 'board': ('扩展', 'board 在交通语境中是“登上车/船/飞机”；board 也可作“板；董事会”。'), 'circle': ('扩展', 'circle 可记“圆圈；循环”；恶性循环就是 vicious circle。'), 'drunk': ('扩展', 'drunk 是 drink 的过去分词，也作形容词“喝醉的”；例句里记“喝醉的”。'), 'judge': ('扩展', 'judge 作名词是“法官”，作动词是“判断”；以貌取人里用动词义。'), 'landscape': ('扩展', 'landscape 在雅思里多记“风景；地貌”，也可指风景画。'), 'page': ('扩展', 'page 先记“页；页面”，出版语境中才引申为版面。'), 'rule': ('扩展', 'rule 可作“规则”，也可作动词“裁定/统治”；法庭语境里是裁决。'), 'ship': ('扩展', 'ship 作名词是船，作动词是“运送/发货”；发货语境记动词义。'), 'smoke': ('扩展', 'smoke 作名词是烟，作动词是“抽烟/冒烟”；例句里是不抽烟。'), 'ring': ('扩展', 'ring 可指戒指、铃声，也可作“按铃/打电话”；门铃语境记“按铃”。'), 'shell': ('扩展', 'shell 作名词是“壳”，也可作动词“剥壳”；乌龟语境先记名词义。'), 'core': ('扩展', 'core 先记“核心”，不是只记“核”；core subject 是核心科目。'), 'sex': ('扩展', 'sex 在表格语境多指“性别”，也可指生物学上的性。'), 'knock': ('扩展', 'knock 是“敲；撞击”；敲门语境记“敲”。'), 'presumably': ('扩展', 'presumably 表“据推测；大概”，语气是根据已有信息作合理猜测。'), 'raw': ('扩展', 'raw 记“生的；未加工的”，可用于 raw materials 或 raw food。')}
MANUAL_NOTES.update({'analyses': ('词根词缀', 'analyses 是 analysis 的复数，记“分析；剖析”；不要误当成 analyse 的第三人称。'), 'ages': ('扩展', 'ages 可指“年龄”，也可指“很长时间/时代”；例句里的 for ages 记“很久”。'), 'cap': ('扩展', 'cap 名词是帽子，动词可指“覆盖顶部/限制”；盖瓶子或给上限时用动词义。'), 'set': ('扩展', 'set 义项多：设定、放置、一套、固定的；例句 set requirements 记“设定要求”。'), 'crew': ('扩展', 'crew 不只船员，也指机组或一队工作人员；film crew 是摄制组。'), 'direct line': ('扩展', 'direct line 在听力里常指“专线电话/直拨线路”，不是普通的几何直线。'), 'cater for': ('扩展', 'cater for 可指“供应餐饮”，也常指“满足/迎合需求”；看宾语决定义项。'), 'as far as': ('扩展', 'as far as 不是普通 as...as 比较，常记“直到；就……而言”。'), 'as well as': ('扩展', 'as well as 整体记“也；以及”，连接并列信息，不按比较结构硬拆。'), 'as though': ('扩展', 'as though 整体记“好像；仿佛”，后面常接从句描述看起来的状态。'), 'fishing industry': ('扩展', 'fishing industry 直接记“渔业/捕鱼业”，重点是行业，不是单次钓鱼。'), 'high street': ('扩展', 'high street 是英式表达，指城镇主要商业街，不是“高的街”。'), 'a lot': ('扩展', 'a lot 可作“大量/许多”，也可修饰动词或形容词表示“很；非常”。'), 'account for': ('扩展', 'account for 常见三义：解释原因、负责、在比例上占；阅读里要按上下文选。'), 'make up': ('扩展', 'make up 多义：组成、编造、弥补、化妆、和好；别只记“化妆”。')})
MANUAL_NOTES.update({'capabilities': ('扩展', 'capability 是“能力/潜力”，capabilities 是复数；本表里不要按“可能”单独记。'), 'applications': ('扩展', 'application 可指“申请”，也可指“应用”；applications 在本表里重点记“应用”。'), 'aspects': ('扩展', 'aspect 可指“方面”，也可指“外观/面貌”；aspects 按上下文选“方面”或“面貌”。'), 'glasses': ('扩展', 'glasses 通常先记“眼镜”，也可作 glass 的复数“玻璃杯”；不要只联想到玻璃。'), 'mouses': ('扩展', 'mouses 在电脑语境是 mouse 的复数，记“鼠标”；动物复数更常见 mice。'), 'patches': ('扩展', 'patches 可指“补丁/补片”，也可指一小块区域；本表里记“小块；斑块”。'), 'premises': ('扩展', 'premises 作复数常指企业或机构的“房屋及土地/经营场所”，不是 premise 的前提义。'), 'similarities': ('词根词缀', 'similar 是“相似的”，similarity 是“相似性”，similarities 是复数“相似之处”。')})
MANUAL_NOTES.update({'analyses': ('词根词缀', 'analyses 是 analysis 的复数，记“分析；剖析”；不要误拆成 analyse 加后缀。'), 'according': ('扩展', 'according 单独可作“符合的/相符的”，常见 according to 整体记“根据；按照”。'), 'applied': ('扩展', 'applied 作形容词重点记“应用的；实用的”，也可作 apply 的过去分词。'), 'missing': ('扩展', 'missing 是 miss 加 -ing，作形容词常记“失踪的；缺失的”，不是 mis- 前缀词。'), 'following': ('扩展', 'following 作形容词是“接着的；下列的”，作介词是“在……之后”。'), 'associated': ('扩展', 'associated 记“相关的；有关联的”，常见搭配 be associated with。'), 'involved': ('扩展', 'involved 可指“有关的；牵涉其中的”，也可指事情“复杂的”。'), 'compelling': ('扩展', 'compelling 在阅读里常指“令人信服的；强有力的”，不是普通的强迫。'), 'disappointing': ('扩展', 'disappointing 是“令人失望的”，-ing 形容事物给人的感受。'), 'exciting': ('扩展', 'exciting 是“令人兴奋的；激动人心的”，-ing 形容事物本身。'), 'frustrating': ('扩展', 'frustrating 是“令人沮丧/懊恼的”，常形容过程或问题。'), 'reassuring': ('扩展', 'reassuring 是“令人安心的”，来自 reassure“使放心”。'), 'relaxing': ('扩展', 'relaxing 是“令人放松的；轻松的”，-ing 形容活动或环境。'), 'satisfying': ('扩展', 'satisfying 是“令人满意的”，常形容结果或体验。'), 'surprising': ('扩展', 'surprising 是“令人吃惊的；出人意料的”，-ing 形容事情本身。'), 'advertising': ('扩展', 'advertising 重点记“广告活动；广告业”，也可表示 advertise 的进行形式。'), 'surrounding': ('扩展', 'surrounding 作形容词是“周围的”，如 surrounding area；也可作 surround 的进行形式。'), 'promising': ('扩展', 'promising 作形容词是“有希望的；有前途的”，不只表示 promise 的进行形式。')})
REF_OVERRIDES.update({'access': '通道/使用权', 'account': '账户/解释', 'addition': '增加/附加', 'admission': '准入/承认', 'advance': '前进/进展', 'advanced': '先进的/高级的', 'award': '奖项/授予', 'bar': '酒吧/条状物', 'bear': '熊/承受', 'content': '内容/含量', 'contract': '合同/收缩', 'current': '当前的/水流', 'project': '项目/投射', 'present': '目前的/呈现', 'subject': '主题/学科', 'charge': '收费/负责', 'match': '匹配/比赛'}); MANUAL_NOTES.update({'access': ('扩展', 'access 核心是“进入/使用的权利或通道”，也可作动词“获取/访问”；不要只记“接触”。'), 'account': ('扩展', 'account 可指“账户”，也可指“叙述/解释”；account for 另记“解释原因/占比”。'), 'addition': ('扩展', 'addition 是“增加；附加”，in addition 表“此外”；不要只记成一个附加物。'), 'admission': ('扩展', 'admission 可指“准入/录取”，也可指“承认”；看学校、场馆还是陈述语境。'), 'advance': ('扩展', 'advance 可作“前进/推进/进展”，也有“提前/预先的”义；别只记发展。'), 'advanced': ('扩展', 'advanced 重点记“先进的；高级的”，也可作 advance 的过去分词。'), 'award': ('扩展', 'award 作名词是奖项，作动词是“授予/裁定”；和 aware 分开记。'), 'bar': ('扩展', 'bar 可指“酒吧”，也可指条状物或栅栏；听力场景先看地点还是形状。'), 'bear': ('扩展', 'bear 名词是熊，动词可指“承受/忍受/带有/生育”；阅读里常考动词义。'), 'content': ('扩展', 'content 作名词是“内容/含量”，作形容词是“满足的”；注意重音不同。'), 'contract': ('扩展', 'contract 名词是“合同”，动词可指“收缩/感染/签约”；按语境分义。'), 'current': ('扩展', 'current 作形容词是“当前的”，作名词可指水流、电流或趋势。'), 'project': ('扩展', 'project 名词是“项目/课题”，动词可指“预计/投射/突出”。'), 'present': ('扩展', 'present 可指“目前的/在场的”，也可作名词“礼物”或动词“呈现/提出”。'), 'subject': ('扩展', 'subject 可指主题、学科、实验对象；be subject to 表“易受……影响”。'), 'charge': ('扩展', 'charge 可指收费、负责、指控或充电；看宾语和场景判断。'), 'match': ('扩展', 'match 可作“匹配/比赛”，也可指火柴；和 math 分开记。')})
MANUAL_NOTES.update({'in a way': ('扩展', 'in a way 整体记“在某种程度上；以某种方式”，不要逐词硬拆。'), 'in case of': ('扩展', 'in case of 表“如果发生；在……情况下”，后面通常接名词或名词短语。'), 'keep fit': ('扩展', 'keep fit 是固定表达，意思是“保持健康”。'), 'lead to': ('扩展', 'lead to 在阅读里常表“导致；通向”，不是字面上的“把……带到”。'), 'learn about': ('扩展', 'learn about 表“了解；获悉有关……的信息”，about 提示信息主题。'), 'life cycle': ('扩展', 'life cycle 直接记“生命周期”，指生物或产品从开始到结束的阶段循环。'), 'meet up': ('扩展', 'meet up 是“碰头；见面”，不一定是偶然遇见。'), 'no charge': ('扩展', 'no charge 是“免费；不收费”，charge 在这里是费用。'), 'right now': ('扩展', 'right now 整体记“现在；马上”，这里的 right 是强调“正好/立刻”，不是右边。'), 'run through': ('扩展', 'run through 常指“快速浏览/排练/贯穿”，按语境选择。'), 'rural areas': ('扩展', 'rural areas 直接记“农村地区”，area 不必翻成单独的“区域”再拼。'), 'set aside': ('扩展', 'set aside 表“留出；搁置”，不是普通地设置到一边。'), 'set out': ('扩展', 'set out 可表“出发”，也可表“陈述/列出”；看旅行还是文本语境。'), 'make a booking': ('扩展', 'make a booking 是“预订”，booking 本身就是预约/订位。'), 'work out': ('扩展', 'work out 可指“解决/算出”，也可指锻炼；学习语境常记“弄明白；解决”。'), 'write up': ('扩展', 'write up 表“整理成文；详细写出”，常用于把笔记或研究结果写成报告。')})
REF_OVERRIDES.update({'contact': '联系/接触'}); MANUAL_NOTES.update({'as far as': ('扩展', 'as far as 整体记“直到；就……而言”，常用于范围、距离或话题边界。'), 'high street': ('扩展', 'high street 是英式表达，指城镇主要商业街或购物街。'), 'contact': ('扩展', 'contact 作名词/动词都可记“联系；接触”，contact details 是联系方式。'), 'high level': ('扩展', 'high level 整体记“高级的；高层次的”，常修饰课程、技能或抽象水平。')})
@dataclass
class Seed:
    word: str
    display: str
    pos: str
    definitions: list[str]
    phonetic: str
    book_ids: list[str]
def normalize_word(raw: str | None) -> str:
    text = str(raw or '').replace('...', ' ').replace('…', ' ').strip().lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+(?:n|v|vi|vt|adj|adv|prep|conj|pron|det|num|phrase)\.?$', '', text)
    return text.strip(" .'\"")
def compact_def(text: str | None) -> str:
    text = str(text or '').strip()
    text = re.sub(r'\[[^\]]*\]|【[^】]*】|<[^>]*>|[\(（][^\)）]*[\)）]', '', text)
    text = re.sub(r'[\[<][^;；,，/。]*', '', text)
    text = re.sub(r'[\(（][^;；,，/。]*', '', text)
    text = re.sub(r'^(?:短语(?:动词|名词|形容词)?|[a-zA-Z./ ]+)[.。．、,，:：]\s*', '', text)
    text = re.sub(r'[a-zA-Z]{1,20}\.?', '', text)
    text = re.sub(r'[&=~]+', '', text)
    text = re.sub(r'^表示[“"]?', '', text).strip('”"')
    text = re.sub(r'“[^”]+”的(?:复数|过去式|现在分词|过去分词|第三人称单数)', '', text)
    parts = [p.strip() for p in re.split(r'[;；,，/。]+', text) if p.strip()]
    for part in parts:
        part = re.sub(r'\s+', '', part).strip()
        if CJK_RE.search(part) and part not in {'的', '地', '得'} and not re.search(r'[a-zA-Z]', part):
            return part[:18]
    return text[:18] if text else '核心义'
def definition_parts(definitions: list[str]) -> list[str]:
    parts = []
    for definition in definitions:
        cleaned = re.sub(r'[\(（][^\)）]*[\)）]', '', str(definition or ''))
        for raw in re.split(r'[;；,，/。]+', cleaned):
            part = compact_def(raw)
            if part and part != '核心义':
                parts.append(part)
    return dedupe(parts, 12)
def target_def(seed: Seed, example: str = '') -> str:
    parts = definition_parts(seed.definitions)
    if example:
        for part in parts:
            if part in example:
                return part
        example_chars = set(re.findall(r'[\u4e00-\u9fff]', example))
        for part in parts:
            chars = set(re.findall(r'[\u4e00-\u9fff]', part))
            if len(chars & example_chars) >= min(2, len(chars)):
                return part
    return parts[0] if parts else '核心义'
def short_zh(text: str | None, limit: int = 26) -> str:
    text = re.sub(r'\s+', '', str(text or ''))
    text = re.sub(r'[A-Za-z]{2,}[A-Za-z -]*', '', text)
    text = re.sub(r'[。；;]+$', '', text)
    return text if len(text) <= limit else text[:limit - 1].rstrip('，、；;') + '…'
def dedupe(values: list[str], limit: int = 8) -> list[str]:
    seen = set()
    result = []
    for value in values:
        item = str(value or '').strip()
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
        if len(result) >= limit:
            break
    return result
def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))
def iter_entries_from(path: Path):
    if not path.exists():
        return
    if path.suffix == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                yield row
        return
    data = read_json(path)
    if isinstance(data, dict) and isinstance(data.get('chapters'), list):
        for chapter in data['chapters']:
            for entry in chapter.get('words', []):
                yield entry
    elif isinstance(data, list):
        for entry in data:
            yield entry
def load_seeds(book_ids: list[str]) -> list[Seed]:
    index: dict[str, dict] = {}
    for book_id in book_ids:
        for chapter in read_json(VOCAB / BOOK_FILES[book_id])['chapters']:
            for entry in chapter['words']:
                word = normalize_word(entry.get('word'))
                if not word or not WORD_RE.fullmatch(word):
                    continue
                current = index.setdefault(word, {
                    'display': entry.get('word', word), 'pos': '', 'defs': [],
                    'phonetic': '', 'book_ids': [],
                })
                current['pos'] = current['pos'] or str(entry.get('pos') or '').strip()
                current['phonetic'] = current['phonetic'] or str(entry.get('phonetic') or '').strip()
                current['defs'].append(str(entry.get('definition') or entry.get('translation') or '').strip())
                current['book_ids'].append(book_id)
    return [
        Seed(word=k, display=v['display'], pos=v['pos'], definitions=dedupe(v['defs'], 4),
             phonetic=v['phonetic'], book_ids=dedupe(v['book_ids'], 4))
        for k, v in sorted(index.items())
    ]
def load_reference_defs() -> dict[str, str]:
    files = [
        'ielts_reading_premium.json', 'ielts_listening_premium.json',
        'ielts_vocabulary_6260.csv', 'ielts_vocabulary_ultimate.csv',
        'ielts_vocabulary_FINAL.json', 'ielts_vocabulary_comprehensive.json',
        'ielts_9400_extended.json', 'ielts_vocabulary_complete_extended.json',
    ]
    refs: dict[str, str] = {}
    for filename in files:
        for entry in iter_entries_from(VOCAB / filename):
            word = normalize_word(entry.get('word') or entry.get('headword'))
            definition = entry.get('definition') or entry.get('translation')
            if word and definition and word not in refs:
                refs[word] = compact_def(definition)
    refs.update(REF_OVERRIDES)
    return refs
def load_examples() -> dict[str, str]:
    path = VOCAB / 'vocabulary_examples.json'
    if not path.exists():
        return {}
    payload = read_json(path).get('examples', {})
    examples = {}
    for word, rows in payload.items():
        if isinstance(rows, list) and rows:
            zh = str(rows[0].get('zh') or '').strip()
            if zh:
                examples[normalize_word(word)] = zh
    return examples
def load_confusables() -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    match_path = VOCAB / 'ielts_confusable_match.json'
    if match_path.exists():
        by_group: dict[str, list[dict]] = defaultdict(list)
        for chapter in read_json(match_path).get('chapters', []):
            for row in chapter.get('words', []):
                by_group[str(row.get('group_key') or '')].append(row)
        for rows in by_group.values():
            for row in rows:
                word = normalize_word(row.get('word'))
                grouped[word].extend(other for other in rows if normalize_word(other.get('word')) != word)
    priority_path = VOCAB / 'confusable_priority_groups.json'
    if priority_path.exists():
        for group in read_json(priority_path).get('groups', []):
            rows = [{'word': word, 'definition': ''} for word in group.get('words', [])]
            for row in rows:
                word = normalize_word(row.get('word'))
                grouped[word].extend(other for other in rows if normalize_word(other.get('word')) != word)
    high_path = VOCAB / 'ielts_high_value_confusables.json'
    if high_path.exists():
        words = read_json(high_path).get('words', {})
        for raw_word, rows in words.items():
            word = normalize_word(raw_word)
            for row in rows[:4] if isinstance(rows, list) else []:
                other = normalize_word(row.get('word'))
                if looks_high_similarity_pair(word, other):
                    grouped[word].append(row)
    return grouped
def looks_high_similarity_pair(left: str, right: str) -> bool:
    if not left or not right or left == right:
        return False
    if abs(len(left) - len(right)) > 3:
        return False
    ratio = SequenceMatcher(None, left, right).ratio()
    same_prefix = len(left) >= 5 and left[:3] == right[:3]
    return ratio >= 0.84 or same_prefix and ratio >= 0.82
def candidate_bases(word: str) -> list[str]:
    candidates = []
    transforms = [
        (r'ies$', 'y'), (r'ves$', 'f'), (r'ves$', 'fe'), (r'ied$', 'y'),
        (r'ing$', ''), (r'ing$', 'e'), (r'ed$', ''), (r'ed$', 'e'),
        (r'es$', ''), (r'es$', 'e'), (r's$', ''), (r'ly$', ''),
        (r'ally$', 'al'), (r'ically$', 'ic'), (r'ation$', 'e'), (r'ition$', 'e'),
        (r'tion$', 'e'), (r'sion$', 'd'), (r'ment$', ''), (r'ness$', ''),
        (r'ity$', 'e'), (r'ability$', 'able'), (r'ibility$', 'ible'),
        (r'able$', ''), (r'ible$', 'e'), (r'ive$', 'e'), (r'al$', ''),
        (r'ous$', ''), (r'er$', ''), (r'or$', ''), (r'ist$', ''), (r'ism$', ''),
    ]
    for pattern, repl in transforms:
        if re.search(pattern, word):
            base = re.sub(pattern, repl, word)
            candidates.append(base)
            if len(base) > 3 and base[-1:] == base[-2:-1]:
                candidates.append(base[:-1])
    return dedupe([c for c in candidates if len(c) >= 4 and c != word], 10)
def suffix_for(word: str) -> tuple[str, str] | None:
    for suffix, meaning in SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            return suffix, meaning
    return None
def derivation_note(seed: Seed, refs: dict[str, str]) -> tuple[str, str] | None:
    if ' ' in seed.word:
        return None
    target = compact_def(seed.definitions[0] if seed.definitions else '')
    suffix = suffix_for(seed.word)
    if not suffix:
        return None
    for base in candidate_bases(seed.word):
        if base in refs:
            if base in UNSAFE_DERIVATION_BASES:
                continue
            base_def = refs[base]
            suf, meaning = suffix
            if re.search(r'复数|过去|现在分词|第三人称|变形|名词复数', target):
                target = base_def
            if suf in {'s', 'es'}:
                text = f'{base} 是“{base_def}”，-{suf} 标记复数或三单；{seed.word} 在题中指“{target}”。'
            elif suf in {'ed', 'ing'}:
                text = f'{base} 是“{base_def}”，-{suf} 标记时态/状态；{seed.word} 指“{target}”。'
            else:
                text = f'{base} 是“{base_def}”，-{suf} 是{meaning}；{seed.word} 合起来指“{target}”。'
            return '词根词缀', text
    return None
def prefix_note(seed: Seed, refs: dict[str, str]) -> tuple[str, str] | None:
    if ' ' in seed.word:
        return None
    target = compact_def(seed.definitions[0] if seed.definitions else '')
    for prefix, meaning in sorted(PREFIXES.items(), key=lambda item: len(item[0]), reverse=True):
        if not seed.word.startswith(prefix) or len(seed.word) <= len(prefix) + 3:
            continue
        if not prefix_is_semantic(prefix, target):
            continue
        base = seed.word[len(prefix):]
        if base in refs:
            return '词根词缀', f'{prefix}- 表“{meaning}”；{seed.word} 顺着这层前缀关系记“{target}”。'
        if base.startswith(('m', 'p', 'b')) and f'in{base}' == seed.word and base in refs:
            return '词根词缀', f'in-/im- 表“否定或进入”；{seed.word} 记“{target}”。'
    return None
def prefix_is_semantic(prefix: str, target: str) -> bool:
    rules = {
        'un|non|in|im|il|ir': r'不|无|非|未|失|缺|难以|不能|不足|非法',
        'dis|mis': r'不|无|错|误|反|分|失|消|混|疾病|劣',
        're': r'再|重新|重|回|恢复|返回|重复',
        'pre|fore': r'预|前|先',
        'post': r'后|研究生',
        'inter': r'相互|之间|国际|交互|中间|人际',
        'micro': r'微|小',
        'multi': r'多',
        'anti': r'反|抗',
        'auto': r'自动|自己|自治',
        'over': r'过|超|上|头顶',
        'under|sub': r'下|不足|次级|潜',
        'trans': r'跨|转|运输',
        'super|extra': r'超|额外|非凡',
        'bio': r'生物|生命',
    }
    return any(prefix in key.split('|') and re.search(pattern, target) for key, pattern in rules.items())
def root_note(seed: Seed) -> tuple[str, str] | None:
    if ' ' in seed.word:
        return None
    target = compact_def(seed.definitions[0] if seed.definitions else '')
    word = seed.word.replace('-', '')
    suffix = suffix_for(word)
    suffix_text = f'，-{suffix[0]} 是{suffix[1]}' if suffix and suffix[0] not in {'s', 'es', 'ed', 'ing'} else ''
    for root, meaning in sorted(ROOTS, key=lambda item: len(item[0]), reverse=True):
        if root in word and len(root) >= 3:
            if root in {'manu', 'bio', 'geo', 'tele', 'photo'} or len(root) >= 4:
                return '词根词缀', f'{root} 表“{meaning}”{suffix_text}；{seed.word} 从这个词根线索记“{target}”。'
    return None
def confusable_note(seed: Seed, refs: dict[str, str], confusables: dict[str, list[dict]]) -> tuple[str, str] | None:
    rows = confusables.get(seed.word) or []
    target = target_def(seed)
    parts = []
    seen = {seed.word}
    for row in rows:
        word = normalize_word(row.get('word'))
        definition = REF_OVERRIDES.get(word) or compact_def(row.get('definition')) if row.get('definition') else refs.get(word, '')
        if not word or word in seen or not CJK_RE.search(definition) or definition == '核心义':
            continue
        if definition == target:
            continue
        parts.append(f'{word} 是“{definition}”')
        seen.add(word)
        if len(parts) >= 2:
            break
    if parts:
        return '辨析', f'和近形/近音词分开：{seed.word} 是“{target}”；' + '，'.join(parts) + '。'
    return None
def phrase_note(seed: Seed, refs: dict[str, str], examples: dict[str, str]) -> tuple[str, str] | None:
    if ' ' not in seed.word:
        return None
    target = target_def(seed, examples.get(seed.word, ''))
    words = seed.word.split()
    if words[0] in {'a', 'an'} and len(words) >= 2:
        head = words[-1].rstrip("'")
        head_def = refs.get(head, target)
        modifier = ' '.join(words[1:-1])
        if 'more' in words:
            return '扩展', f'few 表少量，more 表额外增加；{seed.word} 表“{target.rstrip("的")}”。'
        if words[-2:] == ['of'] or words[-1] == 'of':
            return '扩展', f'{seed.word} 是数量/范围搭配，of 后接对象；在题中表示“{target}”。'
        if words[-1] in PREP_MEANING and len(words) >= 3:
            return '扩展', f'{words[1]} 是“{refs.get(words[1], target)}”，{words[-1]} 接对象或方面；{seed.word} 表“{target}”。'
        if modifier:
            return '扩展', f'{head} 是“{head_def}”，{modifier} 限定程度或数量；{seed.word} 表“{target}”。'
        return '扩展', f'a/an 把后面的 {head} 变成一个可数单位；{seed.word} 表“{target}”。'
    if len(words) >= 3 and words[-2] == 'of':
        head = ' '.join(words[:-2])
        return '扩展', f'{head} 与 of 后面的对象连成固定搭配；{seed.word} 在句中表示“{target}”。'
    if len(words) >= 2 and words[0] in {'be', 'have', 'make', 'take', 'come', 'go', 'get', 'give'}:
        if words[0] == 'be':
            return '扩展', f'{seed.word} 是 be 加状态/介词的搭配；整体记“{target}”，后半段给出状态或范围。'
        return '扩展', f'{seed.word} 先按固定搭配记整体义“{target}”；{words[0]} 提示动作框架，后半段给出对象或结果。'
    if len(words) == 3 and words[0] == 'as' and words[-1] == 'as':
        return '辨析', f'as...as 是比较框架，中间的 {words[1]} 定程度；{seed.word} 表“{target}”。'
    if words[-1] in PREP_MEANING and words[0] in refs:
        hint = '后接动作或对象' if words[-1] == 'to' else f'提示“{PREP_MEANING[words[-1]]}”的方向或范围'
        return '扩展', f'{seed.word} 重点记整体义“{target}”；末尾 {words[-1]} {hint}。'
    if words[0] in PREP_MEANING:
        return '扩展', f'{words[0]} 表“{PREP_MEANING[words[0]]}”，后半段限定位置/时间；{seed.word} 表“{target}”。'
    if len(words) == 2 and words[0] in refs and words[1] in refs:
        return '串记', f'{words[0]} 可借“{refs[words[0]]}”起头，{words[1]} 限定对象或场景；{seed.word} 记“{target}”。'
    example = examples.get(seed.word)
    if example:
        return '助记', f'把 {seed.word} 放进例句场景“{short_zh(example, 24)}”，重点记“{target}”。' if '…' not in short_zh(example, 24) else f'{seed.word} 在例句中对应“{target}”，先把词形和这个考试义绑定。'
    return '扩展', f'把 {seed.word} 当考试搭配处理，不逐词硬拆；它在题中表示“{target}”。'
def example_note(seed: Seed, examples: dict[str, str]) -> tuple[str, str] | None:
    example = examples.get(seed.word)
    if not example:
        return None
    target = target_def(seed, example)
    return '助记', f'把 {seed.word} 放进例句场景“{short_zh(example, 24)}”，重点记“{target}”。' if '…' not in short_zh(example, 24) else f'{seed.word} 在例句中对应“{target}”，先把词形和这个考试义绑定。'
def fallback_note(seed: Seed) -> tuple[str, str]:
    target = compact_def(seed.definitions[0] if seed.definitions else '')
    if seed.phonetic:
        return '助记', f'把读音 {seed.phonetic} 和考试义“{target}”绑定，先认准 {seed.word} 的核心用法。'
    return '助记', f'{seed.word} 先按考试高频义“{target}”识别，再结合题干搭配判断具体义项。'
def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('“ ', '“').replace(' ”', '”')
    if len(text) > 118:
        text = text[:115].rstrip('，；; ') + '。'
    return text
def build_item(seed: Seed, refs: dict[str, str], examples: dict[str, str], confusables: dict[str, list[dict]]) -> dict:
    manual = MANUAL_NOTES.get(seed.word)
    if manual:
        badge, text = manual
    else:
        for builder in (
            lambda: phrase_note(seed, refs, examples),
            lambda: prefix_note(seed, refs),
            lambda: derivation_note(seed, refs),
            lambda: confusable_note(seed, refs, confusables),
            lambda: example_note(seed, examples),
            lambda: root_note(seed),
        ):
            result = builder()
            if result:
                badge, text = result
                break
        else:
            badge, text = fallback_note(seed)
    text = clean_text(text)
    if badge not in BADGES:
        badge = '助记'
    if LOW_QUALITY_RE.search(text) or not CJK_RE.search(text):
        badge, text = fallback_note(seed)
        text = clean_text(text)
    return {
        'word': seed.word,
        'badge': badge,
        'text': text,
        'book_ids': seed.book_ids,
        'source': SOURCE,
    }
def validate(items: dict[str, dict], seeds: list[Seed]) -> dict:
    expected = {seed.word for seed in seeds}
    missing = sorted(expected - set(items))
    bad = []
    badges = defaultdict(int)
    for word, item in items.items():
        text = str(item.get('text') or '')
        badges[str(item.get('badge') or '')] += 1
        if item.get('badge') not in BADGES or len(text) < 8 or LOW_QUALITY_RE.search(text):
            bad.append({'word': word, 'badge': item.get('badge'), 'text': text})
    return {
        'total_words': len(expected),
        'covered_words': len(expected) - len(missing),
        'missing_count': len(missing),
        'missing_sample': missing[:30],
        'bad_count': len(bad),
        'bad_sample': bad[:30],
        'badge_distribution': dict(sorted(badges.items())),
    }
def main() -> int:
    parser = argparse.ArgumentParser(description='Generate premium mnemonics without any LLM calls.')
    parser.add_argument('--book', action='append', choices=sorted(BOOK_FILES), default=[])
    parser.add_argument('--output-file', default=str(VOCAB / 'premium_word_mnemonics.json'))
    parser.add_argument('--report-file', default='')
    args = parser.parse_args()
    book_ids = args.book or ['ielts_listening_premium', 'ielts_reading_premium']
    seeds = load_seeds(book_ids)
    refs = load_reference_defs()
    refs.update({seed.word: compact_def(seed.definitions[0] if seed.definitions else '') for seed in seeds})
    refs.update(REF_OVERRIDES)
    examples = load_examples()
    confusables = load_confusables()
    items = {seed.word: build_item(seed, refs, examples, confusables) for seed in seeds}
    payload = {
        'manifest_version': 1,
        'book_ids': book_ids,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'items': dict(sorted(items.items())),
    }
    output = Path(args.output_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
    report = validate(items, seeds)
    if args.report_file:
        Path(args.report_file).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report['missing_count'] == 0 and report['bad_count'] == 0 else 2
if __name__ == '__main__': raise SystemExit(main())
