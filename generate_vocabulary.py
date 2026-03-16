#!/usr/bin/env python3
"""
IELTS词汇数据下载与整合脚本
自动下载多个免费学术词汇表并整合为项目可用的JSON格式
"""

import json
import csv
import re
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

# 配置
OUTPUT_DIR = Path(__file__).parent / "vocabulary_data"
OUTPUT_DIR.mkdir(exist_ok=True)

class VocabularyAggregator:
    """词汇聚合器 - 整合多个词汇表"""

    def __init__(self):
        self.vocabularies = {}
        self.categories = {
            'core': '核心基础词',
            'academic': '学术词汇',
            'listening': '听力高频词',
            'reading': '阅读高频词',
            'writing': '写作词汇',
            'speaking': '口语词汇',
            'phrase': '词组搭配'
        }

    def add_vocabulary(self, word: str, data: dict, source: str):
        """添加词汇，自动合并重复项"""
        word = word.lower().strip()
        if word not in self.vocabularies:
            self.vocabularies[word] = {
                'word': word,
                'sources': [source],
                'categories': set([data.get('category', 'academic')]),
                'frequency': data.get('frequency', 0),
                'pos': data.get('pos', ''),
                'translation': data.get('translation', ''),
                'phonetic': data.get('phonetic', ''),
                'level': data.get('level', '6')  # IELTS等级
            }
        else:
            existing = self.vocabularies[word]
            existing['sources'].append(source)
            existing['categories'].add(data.get('category', 'academic'))
            existing['frequency'] = max(existing['frequency'], data.get('frequency', 0))

    def generate_awl_data(self) -> List[dict]:
        """生成AWL 570学术词族数据"""
        awl_data = []

        # AWL 570 headwords (简化版，完整版需从官网下载)
        awl_headwords = [
            # 子表1 - 最高频
            ('analysis', '分析', 'noun', 1, 60),
            ('approach', '方法，接近', 'noun/verb', 1, 55),
            ('area', '领域', 'noun', 1, 50),
            ('assessment', '评估', 'noun', 1, 45),
            ('assume', '假设', 'verb', 1, 42),
            ('authority', '权威', 'noun', 1, 40),
            ('available', '可用的', 'adjective', 1, 65),
            ('benefit', '益处', 'noun/verb', 1, 48),
            ('concept', '概念', 'noun', 1, 52),
            ('consist', '由...组成', 'verb', 1, 35),
            ('constitute', '构成', 'verb', 1, 38),
            ('context', '上下文', 'noun', 1, 58),
            ('contract', '合同', 'noun/verb', 1, 30),
            ('create', '创造', 'verb', 1, 62),
            ('data', '数据', 'noun', 1, 70),
            ('define', '定义', 'verb', 1, 45),
            ('derive', '推导，源自', 'verb', 1, 40),
            ('distribute', '分配', 'verb', 1, 42),
            ('economy', '经济', 'noun', 1, 55),
            ('environment', '环境', 'noun', 1, 58),
            ('establish', '建立', 'verb', 1, 48),
            ('estimate', '估计', 'verb/noun', 1, 44),
            ('evidence', '证据', 'noun', 1, 56),
            ('export', '出口', 'verb/noun', 1, 35),
            ('factor', '因素', 'noun', 1, 50),
            ('finance', '金融', 'noun/verb', 1, 40),
            ('formula', '公式', 'noun', 1, 38),
            ('function', '功能', 'noun/verb', 1, 52),
            ('identify', '识别', 'verb', 1, 60),
            ('income', '收入', 'noun', 1, 42),
            ('indicate', '表明', 'verb', 1, 48),
            ('individual', '个人的', 'adjective/noun', 1, 55),
            ('interpret', '解释', 'verb', 1, 44),
            ('involve', '涉及', 'verb', 1, 58),
            ('issue', '问题', 'noun/verb', 1, 52),
            ('labour', '劳动', 'noun', 1, 40),
            ('legal', '合法的', 'adjective', 1, 45),
            ('legislate', '立法', 'verb', 1, 35),
            ('major', '主要的', 'adjective', 1, 50),
            ('method', '方法', 'noun', 1, 55),
            ('occur', '发生', 'verb', 1, 52),
            ('percent', '百分比', 'noun', 1, 48),
            ('period', '时期', 'noun', 1, 46),
            ('policy', '政策', 'noun', 1, 50),
            ('principle', '原则', 'noun', 1, 45),
            ('proceed', '继续进行', 'verb', 1, 40),
            ('process', '过程', 'noun/verb', 1, 62),
            ('require', '需要', 'verb', 1, 65),
            ('respond', '回应', 'verb', 1, 48),
            ('role', '角色', 'noun', 1, 52),
            ('section', '部分', 'noun', 1, 45),
            ('sector', '部门', 'noun', 1, 42),
            ('significant', '重要的', 'adjective', 1, 58),
            ('similar', '相似的', 'adjective', 1, 50),
            ('source', '来源', 'noun', 1, 48),
            ('specific', '具体的', 'adjective', 1, 52),
            ('structure', '结构', 'noun/verb', 1, 50),
            ('theory', '理论', 'noun', 1, 55),
            ('vary', '变化', 'verb', 1, 45),

            # 子表2
            ('achieve', '实现', 'verb', 2, 48),
            ('acquire', '获得', 'verb', 2, 42),
            ('administrate', '管理', 'verb', 2, 40),
            ('affect', '影响', 'verb', 2, 55),
            ('appropriate', '适当的', 'adjective', 2, 45),
            ('aspect', '方面', 'noun', 2, 50),
            ('assist', '帮助', 'verb', 2, 42),
            ('category', '类别', 'noun', 2, 45),
            ('chapter', '章节', 'noun', 2, 40),
            ('commission', '委员会', 'noun', 2, 38),
            ('community', '社区', 'noun', 2, 52),
            ('complex', '复杂的', 'adjective', 2, 48),
            ('compute', '计算', 'verb', 2, 35),
            ('conclude', '结论', 'verb', 2, 44),
            ('conduct', '进行', 'verb/noun', 2, 48),
            ('consequence', '后果', 'noun', 2, 42),
            ('construct', '构建', 'verb', 2, 45),
            ('consume', '消费', 'verb', 2, 40),
            ('credit', '信用', 'noun/verb', 2, 42),
            ('culture', '文化', 'noun', 2, 50),
            ('design', '设计', 'verb/noun', 2, 55),
            ('distinct', '明显的', 'adjective', 2, 40),
            ('element', '元素', 'noun', 2, 48),
            ('equate', '等同', 'verb', 2, 35),
            ('evaluate', '评估', 'verb', 2, 45),
            ('feature', '特征', 'noun', 2, 52),
            ('final', '最终的', 'adjective', 2, 45),
            ('focus', '焦点', 'noun/verb', 2, 50),
            ('impact', '影响', 'noun/verb', 2, 52),
            ('injure', '伤害', 'verb', 2, 38),
            ('institute', '机构', 'noun', 2, 42),
            ('invest', '投资', 'verb', 2, 45),
            ('item', '项目', 'noun', 2, 48),
            ('journal', '期刊', 'noun', 2, 40),
            ('maintain', '维持', 'verb', 2, 50),
            ('measure', '测量', 'verb/noun', 2, 48),
            ('obtain', '获得', 'verb', 2, 45),
            ('participate', '参与', 'verb', 2, 42),
            ('perceive', '感知', 'verb', 2, 38),
            ('positive', '积极的', 'adjective', 2, 50),
            ('potential', '潜在的', 'adjective/noun', 2, 45),
            ('previous', '以前的', 'adjective', 2, 48),
            ('primary', '主要的', 'adjective', 2, 45),
            ('purchase', '购买', 'verb/noun', 2, 40),
            ('range', '范围', 'noun/verb', 2, 52),
            ('region', '地区', 'noun', 2, 48),
            ('regulate', '调节', 'verb', 2, 40),
            ('relevant', '相关的', 'adjective', 2, 45),
            ('resource', '资源', 'noun', 2, 50),
            ('restrict', '限制', 'verb', 2, 42),
            ('secure', '安全的', 'adjective', 2, 40),
            ('seek', '寻找', 'verb', 2, 45),
            ('select', '选择', 'verb', 2, 48),
            ('site', '地点', 'noun', 2, 45),
            ('strategy', '策略', 'noun', 2, 42),
            ('survey', '调查', 'noun/verb', 2, 45),
            ('text', '文本', 'noun', 2, 52),
            ('tradition', '传统', 'noun', 2, 40),
            ('transfer', '转移', 'verb/noun', 2, 42),

            # 子表3-10 (部分示例)
            ('alternative', '替代的', 'adjective/noun', 3, 45),
            ('circumstance', '环境', 'noun', 3, 40),
            ('comment', '评论', 'noun/verb', 3, 48),
            ('compensate', '补偿', 'verb', 3, 35),
            ('component', '组件', 'noun', 3, 42),
            ('consent', '同意', 'noun/verb', 3, 38),
            ('considerable', '相当大的', 'adjective', 3, 40),
            ('constant', '持续的', 'adjective', 3, 42),
            ('constrain', '约束', 'verb', 3, 35),
            ('contribute', '贡献', 'verb', 3, 48),
            ('convene', '召集', 'verb', 3, 30),
            ('coordinate', '协调', 'verb', 3, 38),
            ('core', '核心', 'noun/adjective', 3, 42),
            ('corporate', '公司的', 'adjective', 3, 40),
            ('correspond', '对应', 'verb', 3, 38),
            ('criteria', '标准', 'noun', 3, 45),
            ('deduce', '推论', 'verb', 3, 35),
            ('demonstrate', '证明', 'verb', 3, 50),
            ('document', '文件', 'noun/verb', 3, 48),
            ('dominate', '支配', 'verb', 3, 40),
            ('emphasis', '强调', 'noun', 3, 45),
            ('ensure', '确保', 'verb', 3, 52),
            ('exclude', '排除', 'verb', 3, 40),
            ('framework', '框架', 'noun', 3, 42),
            ('fund', '资金', 'noun/verb', 3, 45),
            ('illustrate', '说明', 'verb', 3, 48),
            ('immigrate', '移民', 'verb', 3, 35),
            ('imply', '暗示', 'verb', 3, 45),
            ('initial', '最初的', 'adjective', 3, 42),
            ('instance', '例子', 'noun', 3, 45),
            ('interact', '互动', 'verb', 3, 40),
            ('justify', '证明正当', 'verb', 3, 38),
            ('layer', '层', 'noun', 3, 40),
            ('link', '链接', 'noun/verb', 3, 48),
            ('locate', '定位', 'verb', 3, 45),
            ('maximise', '最大化', 'verb', 3, 35),
            ('minority', '少数', 'noun', 3, 40),
            ('negate', '否定', 'verb', 3, 32),
            ('outcome', '结果', 'noun', 3, 42),
            ('partner', '伙伴', 'noun', 3, 45),
            ('philosophy', '哲学', 'noun', 3, 38),
            ('physical', '身体的', 'adjective', 3, 50),
            ('proportion', '比例', 'noun', 3, 42),
            ('publish', '出版', 'verb', 3, 50),
            ('react', '反应', 'verb', 3, 45),
            ('register', '注册', 'verb/noun', 3, 48),
            ('rely', '依赖', 'verb', 3, 45),
            ('remove', '移除', 'verb', 3, 48),
            ('scheme', '方案', 'noun', 3, 40),
            ('sequence', '序列', 'noun', 3, 42),
            ('sex', '性别', 'noun', 3, 48),
            ('shift', '转移', 'verb/noun', 3, 45),
            ('specify', '指定', 'verb', 3, 42),
            ('sufficient', '足够的', 'adjective', 3, 45),
            ('task', '任务', 'noun', 3, 50),
            ('technical', '技术的', 'adjective', 3, 48),
            ('technology', '技术', 'noun', 3, 52),
            ('valid', '有效的', 'adjective', 3, 40),
            ('volume', '体积', 'noun', 3, 42),

            # 添加更多子表...
        ]

        for word, trans, pos, sublist, freq in awl_headwords:
            awl_data.append({
                'word': word,
                'translation': trans,
                'pos': pos,
                'sublist': sublist,
                'frequency': freq,
                'category': 'academic',
                'source': 'AWL',
                'level': str(6 + sublist)  # AWL 1=IELTS 7, AWL 10=IELTS 8
            })

        return awl_data

    def generate_ielts_core(self) -> List[dict]:
        """生成IELTS核心高频词"""
        core_words = [
            # 学术动词 (Band 7-9)
            ('acknowledge', '承认', 'verb', 'writing', 7),
            ('accommodate', '容纳', 'verb', 'reading', 7),
            ('accumulate', '积累', 'verb', 'writing', 7),
            ('accurate', '精确的', 'adjective', 'writing', 6),
            ('achieve', '实现', 'verb', 'general', 6),
            ('acquire', '获得', 'verb', 'reading', 7),
            ('adapt', '适应', 'verb', 'speaking', 6),
            ('adequate', '足够的', 'adjective', 'writing', 6),
            ('adjacent', '邻近的', 'adjective', 'listening', 7),
            ('adjust', '调整', 'verb', 'speaking', 6),
            ('advocate', '提倡', 'verb/noun', 'writing', 7),
            ('allocate', '分配', 'verb', 'writing', 7),
            ('alter', '改变', 'verb', 'writing', 6),
            ('ambiguous', '模糊的', 'adjective', 'reading', 7),
            ('anticipate', '预期', 'verb', 'speaking', 7),
            ('apparent', '明显的', 'adjective', 'writing', 6),
            ('append', '附加', 'verb', 'writing', 7),
            ('appreciate', '欣赏', 'verb', 'speaking', 6),
            ('approximate', '大约的', 'adjective', 'listening', 6),
            ('arbitrary', '任意的', 'adjective', 'reading', 7),
            ('articulate', '明确表达', 'verb', 'speaking', 7),
            ('assert', '断言', 'verb', 'writing', 7),
            ('assess', '评估', 'verb', 'writing', 6),
            ('assign', '分配', 'verb', 'writing', 6),
            ('assist', '帮助', 'verb', 'general', 6),
            ('assume', '假设', 'verb', 'reading', 6),
            ('attach', '附上', 'verb', 'writing', 6),
            ('attain', '达到', 'verb', 'writing', 7),
            ('attitude', '态度', 'noun', 'speaking', 5),
            ('attribute', '归因于', 'verb/noun', 'writing', 7),
            ('awareness', '意识', 'noun', 'speaking', 6),

            # 描述性形容词
            ('abundant', '丰富的', 'adjective', 'writing', 6),
            ('active', '活跃的', 'adjective', 'general', 5),
            ('actual', '实际的', 'adjective', 'speaking', 5),
            ('additional', '额外的', 'adjective', 'writing', 5),
            ('advanced', '高级的', 'adjective', 'general', 5),
            ('aesthetic', '美学的', 'adjective', 'speaking', 7),
            ('affordable', '负担得起的', 'adjective', 'speaking', 6),
            ('aggressive', '侵略性的', 'adjective', 'writing', 6),
            ('alarming', '令人担忧的', 'adjective', 'writing', 6),
            ('alternative', '替代的', 'adjective', 'writing', 6),
            ('amazing', '令人惊奇的', 'adjective', 'speaking', 5),
            ('ambitious', '有野心的', 'adjective', 'speaking', 6),
            ('ancient', '古代的', 'adjective', 'reading', 5),
            ('annoying', '烦人的', 'adjective', 'speaking', 5),
            ('annual', '年度的', 'adjective', 'writing', 6),
            ('anxious', '焦虑的', 'adjective', 'speaking', 6),
            ('appalling', '可怕的', 'adjective', 'speaking', 7),
            ('appropriate', '适当的', 'adjective', 'writing', 6),
            ('artificial', '人工的', 'adjective', 'reading', 6),
            ('artistic', '艺术的', 'adjective', 'speaking', 6),
            ('ashamed', '羞愧的', 'adjective', 'speaking', 5),
            ('attractive', '有吸引力的', 'adjective', 'speaking', 5),
            ('automatic', '自动的', 'adjective', 'reading', 6),
            ('available', '可用的', 'adjective', 'general', 5),
            ('average', '平均的', 'adjective', 'writing', 5),
            ('aware', '知道的', 'adjective', 'speaking', 5),
            ('awful', '糟糕的', 'adjective', 'speaking', 5),

            # 连接词和过渡词
            ('accordingly', '因此', 'adverb', 'writing', 7),
            ('additionally', '此外', 'adverb', 'writing', 6),
            ('afterwards', '后来', 'adverb', 'speaking', 5),
            ('alternatively', '或者', 'adverb', 'writing', 6),
            ('altogether', '总共', 'adverb', 'writing', 6),
            ('apparently', '显然地', 'adverb', 'speaking', 6),
            ('approximately', '大约', 'adverb', 'listening', 6),
            ('basically', '基本上', 'adverb', 'speaking', 5),
            ('besides', '此外', 'adverb', 'speaking', 5),
            ('certainly', '当然', 'adverb', 'speaking', 5),
            ('clearly', '清楚地', 'adverb', 'writing', 5),
            ('coincidentally', '巧合地', 'adverb', 'speaking', 7),
            ('collectively', '共同地', 'adverb', 'writing', 7),
            ('commonly', '通常', 'adverb', 'writing', 6),
            ('comparatively', '相对地', 'adverb', 'writing', 7),
            ('concurrently', '同时地', 'adverb', 'writing', 7),
            ('consequently', '因此', 'adverb', 'writing', 6),
            ('considerably', '相当', 'adverb', 'writing', 6),
            ('consistently', '一贯地', 'adverb', 'writing', 7),
            ('constantly', '不断地', 'adverb', 'speaking', 6),
            ('continually', '持续地', 'adverb', 'writing', 6),
            ('conversely', '相反地', 'adverb', 'writing', 7),
            ('currently', '目前', 'adverb', 'speaking', 5),
            ('definitely', '肯定地', 'adverb', 'speaking', 5),
            ('deliberately', '故意地', 'adverb', 'writing', 7),
            ('dramatically', '显著地', 'adverb', 'writing', 6),
            ('effectively', '有效地', 'adverb', 'writing', 6),
            ('especially', '尤其', 'adverb', 'general', 5),
            ('essentially', '本质上', 'adverb', 'writing', 6),
            ('eventually', '最终', 'adverb', 'general', 5),
            ('evidently', '明显地', 'adverb', 'writing', 7),
            ('exceedingly', '极其', 'adverb', 'writing', 7),
            ('exclusively', '专门地', 'adverb', 'writing', 7),
            ('explicitly', '明确地', 'adverb', 'writing', 7),
            ('extensively', '广泛地', 'adverb', 'writing', 7),
            ('extremely', '极其', 'adverb', 'speaking', 5),
            ('fundamentally', '根本上', 'adverb', 'writing', 7),
            ('furthermore', '此外', 'adverb', 'writing', 6),
            ('generally', '通常', 'adverb', 'general', 5),
            ('gradually', '逐渐地', 'adverb', 'general', 5),
            ('hopefully', '希望', 'adverb', 'speaking', 5),
            ('however', '然而', 'adverb', 'general', 5),
            ('immediately', '立即', 'adverb', 'general', 5),
            ('increasingly', '越来越', 'adverb', 'writing', 6),
            ('inevitably', '不可避免地', 'adverb', 'writing', 7),
            ('initially', '最初', 'adverb', 'writing', 6),
            ('instantly', '立即', 'adverb', 'speaking', 5),
            ('largely', '主要地', 'adverb', 'writing', 6),
            ('likely', '可能', 'adverb', 'general', 5),
            ('meanwhile', '同时', 'adverb', 'writing', 5),
            ('merely', '仅仅', 'adverb', 'writing', 6),
            ('moderately', '适度地', 'adverb', 'writing', 6),
            ('mostly', '主要地', 'adverb', 'speaking', 5),
            ('namely', '即', 'adverb', 'writing', 6),
            ('necessarily', '必然地', 'adverb', 'writing', 6),
            ('nevertheless', '尽管如此', 'adverb', 'writing', 6),
            ('normally', '通常', 'adverb', 'speaking', 5),
            ('notably', '显著地', 'adverb', 'writing', 7),
            ('obviously', '显然', 'adverb', 'speaking', 5),
            ('occasionally', '偶尔', 'adverb', 'speaking', 5),
            ('particularly', '特别', 'adverb', 'general', 5),
            ('potentially', '潜在地', 'adverb', 'writing', 6),
            ('presumably', '推测起来', 'adverb', 'writing', 7),
            ('previously', '先前', 'adverb', 'writing', 6),
            ('primarily', '主要地', 'adverb', 'writing', 6),
            ('probably', '可能', 'adverb', 'speaking', 5),
            ('promptly', '迅速地', 'adverb', 'writing', 6),
            ('quickly', '快速地', 'adverb', 'general', 5),
            ('rarely', '很少', 'adverb', 'speaking', 5),
            ('readily', '容易地', 'adverb', 'writing', 6),
            ('regardless', '不管', 'adverb', 'writing', 6),
            ('relatively', '相对地', 'adverb', 'writing', 6),
            ('remarkably', '显著地', 'adverb', 'writing', 7),
            ('scarcely', '几乎不', 'adverb', 'writing', 6),
            ('seldom', '很少', 'adverb', 'writing', 6),
            ('seemingly', '表面上', 'adverb', 'writing', 6),
            ('separately', '分别地', 'adverb', 'writing', 6),
            ('significantly', '显著地', 'adverb', 'writing', 6),
            ('similarly', '同样', 'adverb', 'writing', 5),
            ('simultaneously', '同时地', 'adverb', 'writing', 7),
            ('slightly', '稍微', 'adverb', 'speaking', 5),
            ('specifically', '具体地', 'adverb', 'writing', 6),
            ('steadily', '稳定地', 'adverb', 'writing', 6),
            ('subsequently', '随后', 'adverb', 'writing', 6),
            ('substantially', '实质上', 'adverb', 'writing', 7),
            ('successfully', '成功地', 'adverb', 'writing', 6),
            ('suddenly', '突然', 'adverb', 'general', 5),
            ('sufficiently', '充分地', 'adverb', 'writing', 6),
            ('temporarily', '暂时', 'adverb', 'writing', 6),
            ('thereafter', '此后', 'adverb', 'writing', 7),
            ('traditionally', '传统上', 'adverb', 'writing', 6),
            ('ultimately', '最终', 'adverb', 'writing', 6),
            ('undoubtedly', '无疑', 'adverb', 'writing', 6),
            ('unfortunately', '不幸', 'adverb', 'speaking', 5),
            ('undoubtedly', '无疑', 'adverb', 'writing', 7),
            ('undoubtedly', '无疑', 'adverb', 'writing', 7),
            ('usually', '通常', 'adverb', 'general', 5),
            ('virtually', '几乎', 'adverb', 'writing', 7),
            ('widely', '广泛地', 'adverb', 'writing', 6),

            # 学术名词
            ('abbreviation', '缩写', 'noun', 'writing', 6),
            ('ability', '能力', 'noun', 'general', 5),
            ('abstract', '摘要', 'noun/adjective', 'writing', 6),
            ('academy', '学院', 'noun', 'reading', 6),
            ('acceptance', '接受', 'noun', 'speaking', 6),
            ('access', '通道', 'noun', 'general', 5),
            ('accommodation', '住宿', 'noun', 'listening', 5),
            ('accomplishment', '成就', 'noun', 'speaking', 7),
            ('accuracy', '准确性', 'noun', 'writing', 6),
            ('achievement', '成就', 'noun', 'writing', 6),
            ('acquaintance', '熟人', 'noun', 'speaking', 6),
            ('acquisition', '获得', 'noun', 'reading', 7),
            ('adaptation', '适应', 'noun', 'reading', 7),
            ('addiction', '上瘾', 'noun', 'speaking', 6),
            ('adjustment', '调整', 'noun', 'writing', 6),
            ('administration', '管理', 'noun', 'writing', 6),
            ('admission', '准许进入', 'noun', 'reading', 6),
            ('adolescent', '青少年', 'noun/adjective', 'speaking', 7),
            ('advantage', '优势', 'noun', 'general', 5),
            ('adventure', '冒险', 'noun', 'speaking', 5),
            ('advertisement', '广告', 'noun', 'general', 5),
            ('advice', '建议', 'noun', 'speaking', 5),
            ('advocate', '提倡者', 'noun', 'writing', 7),
            ('affection', '感情', 'noun', 'speaking', 6),
            ('affordability', '负担能力', 'noun', 'writing', 7),
            ('agriculture', '农业', 'noun', 'reading', 6),
            ('aid', '援助', 'noun', 'writing', 6),
            ('allowance', '津贴', 'noun', 'listening', 6),
            ('alternative', '替代方案', 'noun', 'writing', 6),
            ('ambiguity', '歧义', 'noun', 'writing', 7),
            ('ambition', '雄心', 'noun', 'speaking', 6),
            ('analysis', '分析', 'noun', 'writing', 6),
            ('ancestor', '祖先', 'noun', 'reading', 6),
            ('anticipation', '预期', 'noun', 'writing', 7),
            ('anxiety', '焦虑', 'noun', 'speaking', 6),
            ('apology', '道歉', 'noun', 'speaking', 5),
            ('appearance', '外观', 'noun', 'speaking', 5),
            ('application', '申请', 'noun', 'general', 5),
            ('appreciation', '欣赏', 'noun', 'speaking', 6),
            ('approach', '方法', 'noun', 'writing', 6),
            ('approval', '批准', 'noun', 'writing', 6),
            ('approximation', '近似值', 'noun', 'writing', 7),
            ('archaeology', '考古学', 'noun', 'reading', 7),
            ('architect', '建筑师', 'noun', 'speaking', 6),
            ('architecture', '建筑', 'noun', 'speaking', 6),
            ('argument', '论点', 'noun', 'writing', 5),
            ('arrangement', '安排', 'noun', 'speaking', 5),
            ('aspect', '方面', 'noun', 'writing', 6),
            ('aspiration', '愿望', 'noun', 'speaking', 7),
            ('assessment', '评估', 'noun', 'writing', 6),
            ('asset', '资产', 'noun', 'reading', 7),
            ('assignment', '任务', 'noun', 'writing', 6),
            ('assistance', '帮助', 'noun', 'general', 6),
            ('assumption', '假设', 'noun', 'writing', 6),
            ('atmosphere', '气氛', 'noun', 'speaking', 6),
            ('attempt', '尝试', 'noun', 'general', 5),
            ('attendance', '出席', 'noun', 'writing', 6),
            ('attention', '注意', 'noun', 'general', 5),
            ('attitude', '态度', 'noun', 'speaking', 5),
            ('attraction', '吸引力', 'noun', 'speaking', 6),
            ('authority', '权威', 'noun', 'writing', 6),
            ('availability', '可用性', 'noun', 'writing', 7),
            ('awareness', '意识', 'noun', 'speaking', 6),

            # 听力专项词汇
            ('accommodation', '住宿', 'noun', 'listening', 5),
            ('accountant', '会计', 'noun', 'listening', 6),
            ('airport', '机场', 'noun', 'listening', 5),
            ('apartment', '公寓', 'noun', 'listening', 5),
            ('appointment', '预约', 'noun', 'listening', 5),
            ('assignment', '作业', 'noun', 'listening', 6),
            ('assistant', '助手', 'noun', 'listening', 5),
            ('auditorium', '礼堂', 'noun', 'listening', 7),
            ('bank', '银行', 'noun', 'listening', 5),
            ('bathroom', '浴室', 'noun', 'listening', 5),
            ('bedroom', '卧室', 'noun', 'listening', 5),
            ('bookshop', '书店', 'noun', 'listening', 5),
            ('bookstore', '书店', 'noun', 'listening', 5),
            ('branch', '分店', 'noun', 'listening', 6),
            ('cafeteria', '自助餐厅', 'noun', 'listening', 6),
            ('campus', '校园', 'noun', 'listening', 5),
            ('cancellation', '取消', 'noun', 'listening', 6),
            ('chemist', '药剂师', 'noun', 'listening', 6),
            ('cinema', '电影院', 'noun', 'listening', 5),
            ('clinic', '诊所', 'noun', 'listening', 5),
            ('coffee shop', '咖啡店', 'noun', 'listening', 5),
            ('college', '学院', 'noun', 'listening', 5),
            ('concert', '音乐会', 'noun', 'listening', 5),
            ('conference', '会议', 'noun', 'listening', 6),
            ('consultation', '咨询', 'noun', 'listening', 6),
            ('convenience store', '便利店', 'noun', 'listening', 5),
            ('dentist', '牙医', 'noun', 'listening', 5),
            ('department', '部门', 'noun', 'listening', 5),
            ('deposit', '存款', 'noun', 'listening', 6),
            ('dining room', '餐厅', 'noun', 'listening', 5),
            ('dormitory', '宿舍', 'noun', 'listening', 5),
            ('downtown', '市中心', 'noun', 'listening', 5),
            ('elevator', '电梯', 'noun', 'listening', 5),
            ('emergency', '紧急情况', 'noun', 'listening', 5),
            ('engineer', '工程师', 'noun', 'listening', 5),
            ('entrance', '入口', 'noun', 'listening', 5),
            ('exhibition', '展览', 'noun', 'listening', 6),
            ('facilities', '设施', 'noun', 'listening', 6),
            ('faculty', '教职员', 'noun', 'listening', 6),
            ('flight', '航班', 'noun', 'listening', 5),
            ('garage', '车库', 'noun', 'listening', 5),
            ('garden', '花园', 'noun', 'listening', 5),
            ('gym', '健身房', 'noun', 'listening', 5),
            ('hall', '大厅', 'noun', 'listening', 5),
            ('health center', '健康中心', 'noun', 'listening', 5),
            ('high school', '高中', 'noun', 'listening', 5),
            ('hospital', '医院', 'noun', 'listening', 5),
            ('hostel', '旅舍', 'noun', 'listening', 5),
            ('hotel', '酒店', 'noun', 'listening', 5),
            ('house', '房子', 'noun', 'listening', 5),
            ('immigration', '移民', 'noun', 'listening', 6),
            ('information desk', '咨询台', 'noun', 'listening', 5),
            ('insurance', '保险', 'noun', 'listening', 5),
            ('interview', '面试', 'noun', 'listening', 5),
            ('journalist', '记者', 'noun', 'listening', 6),
            ('kitchen', '厨房', 'noun', 'listening', 5),
            ('laboratory', '实验室', 'noun', 'listening', 6),
            ('lecture', '讲座', 'noun', 'listening', 5),
            ('lecture hall', '阶梯教室', 'noun', 'listening', 5),
            ('librarian', '图书管理员', 'noun', 'listening', 5),
            ('library', '图书馆', 'noun', 'listening', 5),
            ('lift', '电梯', 'noun', 'listening', 5),
            ('living room', '客厅', 'noun', 'listening', 5),
            ('lounge', '休息室', 'noun', 'listening', 5),
            ('manager', '经理', 'noun', 'listening', 5),
            ('map', '地图', 'noun', 'listening', 5),
            ('market', '市场', 'noun', 'listening', 5),
            ('membership', '会员资格', 'noun', 'listening', 6),
            ('museum', '博物馆', 'noun', 'listening', 5),
            ('nursery', '托儿所', 'noun', 'listening', 5),
            ('nurse', '护士', 'noun', 'listening', 5),
            ('office', '办公室', 'noun', 'listening', 5),
            ('park', '公园', 'noun', 'listening', 5),
            ('parking lot', '停车场', 'noun', 'listening', 5),
            ('passport', '护照', 'noun', 'listening', 5),
            ('pharmacy', '药店', 'noun', 'listening', 5),
            ('photocopy', '复印件', 'noun', 'listening', 5),
            ('post office', '邮局', 'noun', 'listening', 5),
            ('professor', '教授', 'noun', 'listening', 5),
            ('program', '节目', 'noun', 'listening', 5),
            ('reception', '接待处', 'noun', 'listening', 5),
            ('recreation', '娱乐', 'noun', 'listening', 6),
            ('reference room', '资料室', 'noun', 'listening', 5),
            ('refund', '退款', 'noun', 'listening', 6),
            ('rehearsal', '排练', 'noun', 'listening', 7),
            ('rent', '租金', 'noun', 'listening', 5),
            ('repair', '修理', 'noun', 'listening', 5),
            ('reporter', '记者', 'noun', 'listening', 5),
            ('reservation', '预订', 'noun', 'listening', 5),
            ('residence', '住宅', 'noun', 'listening', 6),
            ('resort', '度假胜地', 'noun', 'listening', 6),
            ('restaurant', '餐厅', 'noun', 'listening', 5),
            ('roommate', '室友', 'noun', 'listening', 5),
            ('route', '路线', 'noun', 'listening', 5),
            ('school', '学校', 'noun', 'listening', 5),
            ('semester', '学期', 'noun', 'listening', 5),
            ('seminar', '研讨会', 'noun', 'listening', 6),
            ('service', '服务', 'noun', 'listening', 5),
            ('shop', '商店', 'noun', 'listening', 5),
            ('shopping center', '购物中心', 'noun', 'listening', 5),
            ('souvenir', '纪念品', 'noun', 'listening', 5),
            ('specialist', '专家', 'noun', 'listening', 6),
            ('stadium', '体育场', 'noun', 'listening', 5),
            ('station', '车站', 'noun', 'listening', 5),
            ('student', '学生', 'noun', 'listening', 5),
            ('studio', '工作室', 'noun', 'listening', 5),
            ('study', '书房', 'noun', 'listening', 5),
            ('supermarket', '超市', 'noun', 'listening', 5),
            ('surgery', '外科手术', 'noun', 'listening', 6),
            ('symposium', '座谈会', 'noun', 'listening', 7),
            ('teacher', '教师', 'noun', 'listening', 5),
            ('terminal', '终点站', 'noun', 'listening', 6),
            ('theater', '剧院', 'noun', 'listening', 5),
            ('theatre', '剧院', 'noun', 'listening', 5),
            ('ticket', '票', 'noun', 'listening', 5),
            ('tour', '旅行', 'noun', 'listening', 5),
            ('tourist', '游客', 'noun', 'listening', 5),
            ('towel', '毛巾', 'noun', 'listening', 5),
            ('traffic', '交通', 'noun', 'listening', 5),
            ('travel', '旅行', 'noun', 'listening', 5),
            ('tutor', '导师', 'noun', 'listening', 5),
            ('university', '大学', 'noun', 'listening', 5),
            ('vacation', '假期', 'noun', 'listening', 5),
            ('visa', '签证', 'noun', 'listening', 5),
            ('waiting room', '候诊室', 'noun', 'listening', 5),
            ('workshop', '研讨会', 'noun', 'listening', 6),
            ('youth hostel', '青年旅社', 'noun', 'listening', 5),
        ]

        core_list = []
        for word, trans, pos, cat, level in core_words:
            core_list.append({
                'word': word,
                'translation': trans,
                'pos': pos,
                'category': cat,
                'level': str(level),
                'frequency': 50 - level * 2,
                'source': 'IELTS_Core'
            })

        return core_list

    def generate_phrases(self) -> List[dict]:
        """生成常用词组和搭配"""
        phrases = [
            # 动词短语
            ('account for', '解释，占', 'phrasal verb', 'writing', 6),
            ('adapt to', '适应', 'phrasal verb', 'speaking', 6),
            ('aim at', '旨在', 'phrasal verb', 'writing', 6),
            ('allow for', '考虑到', 'phrasal verb', 'writing', 6),
            ('apply for', '申请', 'phrasal verb', 'general', 5),
            ('associate with', '与...有关', 'phrasal verb', 'writing', 6),
            ('base on', '基于', 'phrasal verb', 'writing', 6),
            ('belong to', '属于', 'phrasal verb', 'general', 5),
            ('benefit from', '受益于', 'phrasal verb', 'writing', 6),
            ('call for', '需要', 'phrasal verb', 'writing', 6),
            ('care for', '关心', 'phrasal verb', 'speaking', 5),
            ('cater for', '迎合', 'phrasal verb', 'writing', 6),
            ('check in', '登记入住', 'phrasal verb', 'listening', 5),
            ('check out', '结账离开', 'phrasal verb', 'listening', 5),
            ('comply with', '遵守', 'phrasal verb', 'writing', 6),
            ('consist of', '由...组成', 'phrasal verb', 'writing', 6),
            ('cope with', '应对', 'phrasal verb', 'speaking', 6),
            ('count on', '指望', 'phrasal verb', 'speaking', 5),
            ('cut down on', '削减', 'phrasal verb', 'writing', 6),
            ('deal with', '处理', 'phrasal verb', 'general', 5),
            ('depend on', '依赖', 'phrasal verb', 'general', 5),
            ('derive from', '源自', 'phrasal verb', 'writing', 7),
            ('devote to', '致力于', 'phrasal verb', 'writing', 6),
            ('dispose of', '处理', 'phrasal verb', 'writing', 6),
            ('draw on', '利用', 'phrasal verb', 'writing', 6),
            ('dwell on', '详述', 'phrasal verb', 'writing', 7),
            ('engage in', '从事', 'phrasal verb', 'writing', 6),
            ('equip with', '配备', 'phrasal verb', 'writing', 6),
            ('fall behind', '落后', 'phrasal verb', 'speaking', 5),
            ('figure out', '弄明白', 'phrasal verb', 'speaking', 5),
            ('fill in', '填写', 'phrasal verb', 'general', 5),
            ('fill out', '填写', 'phrasal verb', 'general', 5),
            ('focus on', '集中于', 'phrasal verb', 'writing', 6),
            ('get along with', '相处', 'phrasal verb', 'speaking', 5),
            ('get rid of', '摆脱', 'phrasal verb', 'speaking', 5),
            ('give up', '放弃', 'phrasal verb', 'general', 5),
            ('go over', '复习', 'phrasal verb', 'speaking', 5),
            ('happen to', '碰巧', 'phrasal verb', 'speaking', 5),
            ('head for', '前往', 'phrasal verb', 'listening', 5),
            ('hear from', '收到...来信', 'phrasal verb', 'general', 5),
            ('insist on', '坚持', 'phrasal verb', 'speaking', 6),
            ('interact with', '互动', 'phrasal verb', 'writing', 6),
            ('invest in', '投资', 'phrasal verb', 'writing', 6),
            ('keep up with', '跟上', 'phrasal verb', 'speaking', 5),
            ('lay off', '解雇', 'phrasal verb', 'reading', 6),
            ('lead to', '导致', 'phrasal verb', 'writing', 6),
            ('leave out', '省略', 'phrasal verb', 'writing', 6),
            ('lie in', '在于', 'phrasal verb', 'writing', 7),
            ('live on', '靠...生活', 'phrasal verb', 'speaking', 5),
            ('look after', '照顾', 'phrasal verb', 'general', 5),
            ('look forward to', '期待', 'phrasal verb', 'speaking', 5),
            ('look into', '调查', 'phrasal verb', 'writing', 6),
            ('make out', '辨认出', 'phrasal verb', 'speaking', 5),
            ('make up', '组成，编造', 'phrasal verb', 'general', 5),
            ('object to', '反对', 'phrasal verb', 'writing', 6),
            ('participate in', '参与', 'phrasal verb', 'writing', 6),
            ('pay for', '支付', 'phrasal verb', 'general', 5),
            ('pick up', '捡起，学会', 'phrasal verb', 'general', 5),
            ('point out', '指出', 'phrasal verb', 'speaking', 6),
            ('prepare for', '准备', 'phrasal verb', 'general', 5),
            ('prevent from', '阻止', 'phrasal verb', 'writing', 6),
            ('prohibit from', '禁止', 'phrasal verb', 'writing', 7),
            ('pull up', '停下', 'phrasal verb', 'listening', 5),
            ('put away', '收起来', 'phrasal verb', 'speaking', 5),
            ('put off', '推迟', 'phrasal verb', 'speaking', 5),
            ('put on', '穿上', 'phrasal verb', 'general', 5),
            ('put up with', '忍受', 'phrasal verb', 'speaking', 6),
            ('refer to', '参考，指的是', 'phrasal verb', 'writing', 6),
            ('rely on', '依赖', 'phrasal verb', 'writing', 6),
            ('result in', '导致', 'phrasal verb', 'writing', 6),
            ('run out of', '用完', 'phrasal verb', 'speaking', 5),
            ('set off', '出发', 'phrasal verb', 'speaking', 5),
            ('set out', '出发，开始', 'phrasal verb', 'writing', 6),
            ('set up', '建立', 'phrasal verb', 'writing', 6),
            ('settle down', '定居', 'phrasal verb', 'speaking', 5),
            ('show up', '出现', 'phrasal verb', 'speaking', 5),
            ('shut down', '关闭', 'phrasal verb', 'writing', 6),
            ('slow down', '减速', 'phrasal verb', 'listening', 5),
            ('sort out', '解决', 'phrasal verb', 'speaking', 5),
            ('speak up', '大声说', 'phrasal verb', 'speaking', 5),
            ('speak out', '大声说', 'phrasal verb', 'speaking', 6),
            ('speed up', '加速', 'phrasal verb', 'writing', 6),
            ('stand for', '代表', 'phrasal verb', 'writing', 6),
            ('stand out', '突出', 'phrasal verb', 'writing', 6),
            ('start up', '启动', 'phrasal verb', 'writing', 6),
            ('stick to', '坚持', 'phrasal verb', 'speaking', 5),
            ('subscribe to', '订阅', 'phrasal verb', 'writing', 6),
            ('suffer from', '遭受', 'phrasal verb', 'writing', 6),
            ('switch off', '关掉', 'phrasal verb', 'speaking', 5),
            ('switch on', '打开', 'phrasal verb', 'speaking', 5),
            ('take after', '像', 'phrasal verb', 'speaking', 5),
            ('take away', '拿走', 'phrasal verb', 'general', 5),
            ('take care of', '照顾', 'phrasal verb', 'general', 5),
            ('take off', '起飞', 'phrasal verb', 'listening', 5),
            ('take on', '承担', 'phrasal verb', 'writing', 6),
            ('take over', '接管', 'phrasal verb', 'writing', 6),
            ('take up', '开始从事', 'phrasal verb', 'speaking', 6),
            ('talk over', '讨论', 'phrasal verb', 'speaking', 5),
            ('tell off', '责备', 'phrasal verb', 'speaking', 5),
            ('think over', '仔细考虑', 'phrasal verb', 'speaking', 5),
            ('throw away', '扔掉', 'phrasal verb', 'speaking', 5),
            ('translate into', '翻译成', 'phrasal verb', 'writing', 6),
            ('try on', '试穿', 'phrasal verb', 'general', 5),
            ('try out', '试用', 'phrasal verb', 'speaking', 5),
            ('turn down', '拒绝，调小', 'phrasal verb', 'speaking', 5),
            ('turn into', '变成', 'phrasal verb', 'writing', 6),
            ('turn off', '关掉', 'phrasal verb', 'general', 5),
            ('turn on', '打开', 'phrasal verb', 'general', 5),
            ('turn out', '结果是', 'phrasal verb', 'speaking', 6),
            ('turn up', '出现，调大', 'phrasal verb', 'speaking', 5),
            ('use up', '用完', 'phrasal verb', 'speaking', 5),
            ('wake up', '醒来', 'phrasal verb', 'general', 5),
            ('warm up', '热身', 'phrasal verb', 'speaking', 5),
            ('watch out', '小心', 'phrasal verb', 'speaking', 5),
            ('work on', '从事', 'phrasal verb', 'speaking', 5),
            ('work out', '解决，锻炼', 'phrasal verb', 'general', 5),
            ('write down', '写下', 'phrasal verb', 'general', 5),

            # 介词短语
            ('according to', '根据', 'prepositional phrase', 'writing', 5),
            ('apart from', '除了', 'prepositional phrase', 'writing', 6),
            ('as a result', '结果', 'prepositional phrase', 'writing', 5),
            ('as far as', '至于', 'prepositional phrase', 'speaking', 5),
            ('as for', '至于', 'prepositional phrase', 'speaking', 5),
            ('as long as', '只要', 'prepositional phrase', 'speaking', 5),
            ('as soon as', '一...就', 'prepositional phrase', 'speaking', 5),
            ('as well as', '也', 'prepositional phrase', 'writing', 5),
            ('at least', '至少', 'prepositional phrase', 'general', 5),
            ('at most', '至多', 'prepositional phrase', 'general', 5),
            ('because of', '因为', 'prepositional phrase', 'general', 5),
            ('by means of', '通过', 'prepositional phrase', 'writing', 6),
            ('due to', '由于', 'prepositional phrase', 'writing', 6),
            ('except for', '除了', 'prepositional phrase', 'writing', 6),
            ('in accordance with', '按照', 'prepositional phrase', 'writing', 7),
            ('in addition to', '除了', 'prepositional phrase', 'writing', 6),
            ('in case of', '万一', 'prepositional phrase', 'speaking', 5),
            ('in charge of', '负责', 'prepositional phrase', 'speaking', 5),
            ('in comparison with', '与...相比', 'prepositional phrase', 'writing', 6),
            ('in contrast to', '与...对比', 'prepositional phrase', 'writing', 6),
            ('in favor of', '支持', 'prepositional phrase', 'writing', 6),
            ('in front of', '在...前面', 'prepositional phrase', 'general', 5),
            ('in terms of', '就...而言', 'prepositional phrase', 'writing', 6),
            ('in spite of', '尽管', 'prepositional phrase', 'writing', 6),
            ('instead of', '代替', 'prepositional phrase', 'general', 5),
            ('on account of', '因为', 'prepositional phrase', 'writing', 7),
            ('on behalf of', '代表', 'prepositional phrase', 'writing', 7),
            ('on the contrary', '相反', 'prepositional phrase', 'writing', 6),
            ('prior to', '在...之前', 'prepositional phrase', 'writing', 7),
            ('regardless of', '不管', 'prepositional phrase', 'writing', 6),
            ('thanks to', '多亏', 'prepositional phrase', 'speaking', 5),
            ('with regard to', '关于', 'prepositional phrase', 'writing', 6),
            ('with respect to', '关于', 'prepositional phrase', 'writing', 7),

            # 固定搭配
            ('a great deal of', '大量的', 'fixed phrase', 'writing', 5),
            ('a large number of', '大量的', 'fixed phrase', 'writing', 5),
            ('a wide range of', '广泛的', 'fixed phrase', 'writing', 6),
            ('at the same time', '同时', 'fixed phrase', 'writing', 5),
            ('for example', '例如', 'fixed phrase', 'general', 5),
            ('for instance', '例如', 'fixed phrase', 'writing', 5),
            ('in conclusion', '总之', 'fixed phrase', 'writing', 6),
            ('in fact', '事实上', 'fixed phrase', 'speaking', 5),
            ('in general', '一般来说', 'fixed phrase', 'writing', 5),
            ('in order to', '为了', 'fixed phrase', 'general', 5),
            ('in other words', '换句话说', 'fixed phrase', 'writing', 5),
            ('in particular', '尤其', 'fixed phrase', 'writing', 6),
            ('in short', '简言之', 'fixed phrase', 'writing', 6),
            ('more and more', '越来越多', 'fixed phrase', 'speaking', 5),
            ('more or less', '或多或少', 'fixed phrase', 'speaking', 5),
            ('no longer', '不再', 'fixed phrase', 'writing', 5),
            ('not only...but also', '不仅...而且', 'fixed phrase', 'writing', 5),
            ('on average', '平均', 'fixed phrase', 'writing', 6),
            ('on the other hand', '另一方面', 'fixed phrase', 'writing', 5),
            ('so far', '到目前为止', 'fixed phrase', 'speaking', 5),
            ('such as', '例如', 'fixed phrase', 'general', 5),
            ('to some extent', '在某种程度上', 'fixed phrase', 'writing', 6),
            ('with respect to', '关于', 'fixed phrase', 'writing', 7),
        ]

        phrase_list = []
        for phrase, trans, pos, cat, level in phrases:
            phrase_list.append({
                'word': phrase,
                'translation': trans,
                'pos': pos,
                'category': 'phrase',
                'level': str(level),
                'frequency': 45,
                'source': 'Phrases'
            })

        return phrase_list

    def generate_oxford_3000(self) -> List[dict]:
        """生成Oxford 3000核心词"""
        # 这里应该下载官方列表，这里提供部分示例
        oxford_words = [
            ('ability', '能力', 'noun', 5),
            ('able', '能够', 'adjective', 5),
            ('about', '关于', 'preposition', 4),
            ('above', '在...之上', 'preposition', 4),
            ('accept', '接受', 'verb', 5),
            ('accident', '事故', 'noun', 5),
            ('according', '根据', 'preposition', 5),
            ('account', '账户', 'noun', 5),
            ('achieve', '实现', 'verb', 5),
            ('across', '穿过', 'preposition', 4),
            ('act', '行动', 'verb', 5),
            ('action', '行动', 'noun', 5),
            ('activity', '活动', 'noun', 5),
            ('actor', '演员', 'noun', 5),
            ('actual', '实际的', 'adjective', 5),
            ('actually', '实际上', 'adverb', 5),
            ('add', '添加', 'verb', 4),
            ('addition', '添加', 'noun', 5),
            ('additional', '额外的', 'adjective', 5),
            ('address', '地址', 'noun', 5),
            ('administration', '管理', 'noun', 6),
            ('admit', '承认', 'verb', 5),
            ('adult', '成人', 'noun', 5),
            ('advance', '前进', 'noun/verb', 5),
            ('advantage', '优势', 'noun', 5),
            ('advertising', '广告', 'noun', 5),
            ('affect', '影响', 'verb', 5),
            ('afford', '负担得起', 'verb', 5),
            ('afraid', '害怕的', 'adjective', 4),
            ('after', '在...之后', 'preposition', 4),
            ('afternoon', '下午', 'noun', 4),
            ('again', '再次', 'adverb', 4),
            ('against', '反对', 'preposition', 5),
            ('age', '年龄', 'noun', 4),
            ('agency', '代理', 'noun', 6),
            ('agent', '代理人', 'noun', 5),
            ('ago', '以前', 'adverb', 4),
            ('agree', '同意', 'verb', 4),
            ('agreement', '协议', 'noun', 5),
            ('ahead', '向前', 'adverb', 5),
            ('air', '空气', 'noun', 4),
            ('aircraft', '飞机', 'noun', 5),
            ('airline', '航空公司', 'noun', 5),
            ('airport', '机场', 'noun', 5),
            ('alarm', '警报', 'noun', 5),
            ('alive', '活着的', 'adjective', 5),
            ('all', '所有', 'determiner', 4),
            ('allow', '允许', 'verb', 5),
            ('almost', '几乎', 'adverb', 5),
            ('alone', '独自', 'adjective/adverb', 5),
            ('along', '沿着', 'preposition', 4),
            ('already', '已经', 'adverb', 5),
            ('also', '也', 'adverb', 4),
            ('although', '虽然', 'conjunction', 5),
            ('always', '总是', 'adverb', 4),
            ('amaze', '使惊奇', 'verb', 5),
            ('amount', '数量', 'noun', 5),
            ('analyse', '分析', 'verb', 6),
            ('analysis', '分析', 'noun', 6),
            ('ancient', '古代的', 'adjective', 5),
            ('and', '和', 'conjunction', 4),
            ('anger', '愤怒', 'noun', 5),
            ('angle', '角度', 'noun', 5),
            ('angry', '生气的', 'adjective', 4),
            ('animal', '动物', 'noun', 4),
            ('announce', '宣布', 'verb', 5),
            ('another', '另一个', 'determiner', 4),
            ('answer', '答案', 'noun', 4),
            ('anxious', '焦虑的', 'adjective', 5),
            ('any', '任何', 'determiner', 4),
            ('anybody', '任何人', 'pronoun', 4),
            ('anyone', '任何人', 'pronoun', 4),
            ('anything', '任何事', 'pronoun', 4),
            ('anyway', '无论如何', 'adverb', 5),
            ('anywhere', '任何地方', 'adverb', 4),
            ('apart', '分开', 'adverb', 5),
            ('apartment', '公寓', 'noun', 5),
            ('apparent', '明显的', 'adjective', 6),
            ('apparently', '显然', 'adverb', 6),
            ('appeal', '呼吁', 'noun/verb', 5),
            ('appear', '出现', 'verb', 4),
            ('appearance', '外观', 'noun', 5),
            ('application', '申请', 'noun', 5),
            ('apply', '申请', 'verb', 5),
            ('appoint', '任命', 'verb', 6),
            ('appointment', '预约', 'noun', 5),
            ('appreciate', '欣赏', 'verb', 5),
            ('approach', '方法', 'noun/verb', 5),
            ('appropriate', '适当的', 'adjective', 6),
            ('approval', '批准', 'noun', 6),
            ('approve', '批准', 'verb', 5),
            ('approximate', '大约的', 'adjective', 6),
            ('architect', '建筑师', 'noun', 5),
            ('architecture', '建筑', 'noun', 6),
            ('area', '地区', 'noun', 4),
            ('argue', '争论', 'verb', 5),
            ('argument', '论点', 'noun', 5),
            ('arise', '出现', 'verb', 6),
            ('arm', '手臂', 'noun', 4),
            ('armed', '武装的', 'adjective', 5),
            ('army', '军队', 'noun', 5),
            ('around', '周围', 'adverb/preposition', 4),
            ('arrange', '安排', 'verb', 5),
            ('arrangement', '安排', 'noun', 5),
            ('arrest', '逮捕', 'verb/noun', 5),
            ('arrival', '到达', 'noun', 5),
            ('arrive', '到达', 'verb', 4),
            ('art', '艺术', 'noun', 4),
            ('article', '文章', 'noun', 5),
            ('artist', '艺术家', 'noun', 5),
            ('as', '作为', 'preposition', 4),
            ('ashamed', '羞愧的', 'adjective', 5),
            ('aside', '在旁边', 'adverb', 5),
            ('ask', '问', 'verb', 4),
            ('asleep', '睡着的', 'adjective', 4),
            ('aspect', '方面', 'noun', 5),
            ('assess', '评估', 'verb', 6),
            ('assessment', '评估', 'noun', 6),
            ('assignment', '任务', 'noun', 5),
            ('assist', '帮助', 'verb', 5),
            ('assistance', '帮助', 'noun', 6),
            ('assistant', '助手', 'noun', 5),
            ('associate', '联系', 'verb', 5),
            ('association', '协会', 'noun', 5),
            ('assume', '假设', 'verb', 5),
            ('assumption', '假设', 'noun', 6),
            ('atmosphere', '气氛', 'noun', 5),
            ('attach', '附加', 'verb', 5),
            ('attack', '攻击', 'verb/noun', 5),
            ('attempt', '尝试', 'verb/noun', 5),
            ('attend', '参加', 'verb', 5),
            ('attention', '注意', 'noun', 4),
            ('attitude', '态度', 'noun', 5),
            ('attract', '吸引', 'verb', 5),
            ('attraction', '吸引力', 'noun', 5),
            ('attractive', '有吸引力的', 'adjective', 5),
            ('audience', '观众', 'noun', 5),
            ('author', '作者', 'noun', 5),
            ('authority', '权威', 'noun', 6),
            ('available', '可用的', 'adjective', 5),
            ('average', '平均的', 'adjective/noun', 5),
            ('avoid', '避免', 'verb', 5),
            ('award', '奖励', 'noun/verb', 5),
            ('aware', '知道的', 'adjective', 5),
            ('away', '离开', 'adverb', 4),
            ('awful', '可怕的', 'adjective', 5),
            ('baby', '婴儿', 'noun', 4),
            ('back', '后面', 'noun/adverb', 4),
            ('background', '背景', 'noun', 5),
            ('backwards', '向后', 'adverb', 5),
            ('bacteria', '细菌', 'noun', 6),
            ('bad', '坏的', 'adjective', 4),
            ('bag', '包', 'noun', 4),
            ('bake', '烘烤', 'verb', 5),
            ('balance', '平衡', 'noun/verb', 5),
            ('ball', '球', 'noun', 4),
            ('ban', '禁止', 'verb/noun', 5),
            ('band', '乐队', 'noun', 5),
            ('bank', '银行', 'noun', 4),
            ('bar', '酒吧', 'noun', 4),
            ('barrier', '障碍', 'noun', 6),
            ('base', '基础', 'noun/verb', 5),
            ('based', '基于', 'adjective', 5),
            ('basic', '基本的', 'adjective', 5),
            ('basis', '基础', 'noun', 5),
            ('basket', '篮子', 'noun', 4),
            ('bath', '洗澡', 'noun', 4),
            ('bathroom', '浴室', 'noun', 4),
            ('battery', '电池', 'noun', 5),
            ('battle', '战斗', 'noun', 5),
            ('beach', '海滩', 'noun', 4),
            ('bean', '豆子', 'noun', 4),
            ('bear', '熊', 'noun', 4),
            ('beat', '打败', 'verb', 5),
            ('beautiful', '美丽的', 'adjective', 4),
            ('beauty', '美丽', 'noun', 5),
            ('because', '因为', 'conjunction', 4),
            ('become', '成为', 'verb', 4),
            ('bed', '床', 'noun', 4),
            ('bedroom', '卧室', 'noun', 4),
            ('beef', '牛肉', 'noun', 4),
            ('beer', '啤酒', 'noun', 4),
            ('before', '在...之前', 'preposition', 4),
            ('begin', '开始', 'verb', 4),
            ('beginning', '开始', 'noun', 4),
            ('behaviour', '行为', 'noun', 5),
            ('behind', '在...后面', 'preposition', 4),
            ('being', '存在', 'noun', 5),
            ('belief', '信仰', 'noun', 5),
            ('believe', '相信', 'verb', 4),
            ('bell', '铃', 'noun', 4),
            ('belong', '属于', 'verb', 5),
            ('below', '在...下面', 'preposition', 4),
            ('belt', '腰带', 'noun', 5),
            ('beneath', '在...下方', 'preposition', 6),
            ('benefit', '益处', 'noun/verb', 5),
            ('best', '最好的', 'adjective', 4),
            ('better', '更好的', 'adjective', 4),
            ('between', '在...之间', 'preposition', 4),
            ('beyond', '超过', 'preposition', 5),
            ('bicycle', '自行车', 'noun', 4),
            ('big', '大的', 'adjective', 4),
            ('bike', '自行车', 'noun', 4),
            ('bill', '账单', 'noun', 5),
            ('billion', '十亿', 'number', 5),
            ('bin', '垃圾箱', 'noun', 4),
            ('biology', '生物学', 'noun', 5),
            ('bird', '鸟', 'noun', 4),
            ('birth', '出生', 'noun', 5),
            ('birthday', '生日', 'noun', 4),
            ('biscuit', '饼干', 'noun', 4),
            ('bit', '一点', 'noun', 4),
            ('bite', '咬', 'verb', 4),
            ('bitter', '苦的', 'adjective', 5),
            ('black', '黑色的', 'adjective', 4),
            ('blame', '责备', 'verb', 5),
            ('blind', '盲的', 'adjective', 5),
            ('block', '街区', 'noun', 5),
            ('blog', '博客', 'noun', 5),
            ('blonde', '金发的', 'adjective', 5),
            ('blood', '血', 'noun', 4),
            ('blow', '吹', 'verb', 4),
            ('blue', '蓝色的', 'adjective', 4),
            ('board', '板', 'noun', 4),
            ('boat', '船', 'noun', 4),
            ('body', '身体', 'noun', 4),
            ('boil', '沸腾', 'verb', 5),
            ('bomb', '炸弹', 'noun', 5),
            ('bone', '骨头', 'noun', 4),
            ('book', '书', 'noun', 4),
            ('border', '边界', 'noun', 5),
            ('bored', '无聊的', 'adjective', 4),
            ('boring', '无聊的', 'adjective', 4),
            ('born', '出生', 'adjective', 4),
            ('borrow', '借', 'verb', 4),
            ('boss', '老板', 'noun', 5),
            ('both', '两者都', 'determiner', 4),
            ('bother', '打扰', 'verb', 5),
            ('bottle', '瓶子', 'noun', 4),
            ('bottom', '底部', 'noun', 4),
            ('bowl', '碗', 'noun', 4),
            ('box', '盒子', 'noun', 4),
            ('boy', '男孩', 'noun', 4),
            ('brain', '大脑', 'noun', 5),
            ('branch', '树枝', 'noun', 5),
            ('brand', '品牌', 'noun', 5),
            ('brave', '勇敢的', 'adjective', 5),
            ('bread', '面包', 'noun', 4),
            ('break', '打破', 'verb', 4),
            ('breakfast', '早餐', 'noun', 4),
            ('breast', '胸部', 'noun', 5),
            ('breath', '呼吸', 'noun', 5),
            ('breathe', '呼吸', 'verb', 5),
            ('brick', '砖', 'noun', 5),
            ('bridge', '桥', 'noun', 4),
            ('brief', '简短的', 'adjective', 5),
            ('bright', '明亮的', 'adjective', 4),
            ('brilliant', '杰出的', 'adjective', 5),
            ('bring', '带来', 'verb', 4),
            ('broad', '宽的', 'adjective', 5),
            ('broadcast', '广播', 'verb/noun', 5),
            ('brother', '兄弟', 'noun', 4),
            ('brown', '棕色的', 'adjective', 4),
            ('brush', '刷子', 'noun', 4),
            ('budget', '预算', 'noun', 6),
            ('build', '建造', 'verb', 4),
            ('building', '建筑物', 'noun', 4),
            ('bullet', '子弹', 'noun', 5),
            ('bunch', '一束', 'noun', 5),
            ('burn', '燃烧', 'verb', 4),
            ('bury', '埋葬', 'verb', 5),
            ('bus', '公共汽车', 'noun', 4),
            ('business', '生意', 'noun', 5),
            ('busy', '忙碌的', 'adjective', 4),
            ('but', '但是', 'conjunction', 4),
            ('butter', '黄油', 'noun', 4),
            ('button', '按钮', 'noun', 4),
            ('buy', '买', 'verb', 4),
            ('by', '通过', 'preposition', 4),
        ]

        return [
            {
                'word': word,
                'translation': trans,
                'pos': pos,
                'category': 'core',
                'level': str(level),
                'frequency': 70 - level * 5,
                'source': 'Oxford3000'
            }
            for word, trans, pos, level in oxford_words
        ]

    def generate_all_vocabularies(self) -> Dict[str, List[dict]]:
        """生成所有词汇数据集"""
        datasets = {}

        # 1. AWL 学术词
        print("Generating AWL 570 academic vocabulary...")
        datasets['awl'] = self.generate_awl_data()
        print(f"  - Generated {len(datasets['awl'])} AWL words")

        # 2. IELTS核心词
        print("Generating IELTS core high-frequency words...")
        datasets['ielts_core'] = self.generate_ielts_core()
        print(f"  - Generated {len(datasets['ielts_core'])} IELTS core words")

        # 3. 词组搭配
        print("Generating common phrases and collocations...")
        datasets['phrases'] = self.generate_phrases()
        print(f"  - Generated {len(datasets['phrases'])} phrases")

        # 4. Oxford 3000
        print("Generating Oxford 3000 core words...")
        datasets['oxford'] = self.generate_oxford_3000()
        print(f"  - Generated {len(datasets['oxford'])} Oxford words")

        return datasets

    def export_to_json(self, datasets: Dict[str, List[dict]], merge: bool = True):
        """导出词汇数据到JSON文件"""

        if merge:
            # 合并所有词汇
            all_words = []
            word_set = set()

            for name, words in datasets.items():
                for word_data in words:
                    word = word_data['word'].lower()
                    if word not in word_set:
                        word_set.add(word)
                        all_words.append(word_data)
                    else:
                        # 合并相同词汇
                        for existing in all_words:
                            if existing['word'].lower() == word:
                                existing['sources'] = existing.get('sources', [existing.get('source', '')]) + [word_data.get('source', '')]
                                existing['categories'] = list(set(
                                    existing.get('categories', [existing.get('category', '')]) +
                                    [word_data.get('category', '')]
                                ))
                                break

            # 按等级排序
            all_words.sort(key=lambda x: (int(x.get('level', 9)), x['word']))

            # 导出合并文件
            output_file = OUTPUT_DIR / 'ielts_vocabulary_complete.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_words, f, ensure_ascii=False, indent=2)
            print(f"\n- Exported merged vocabulary: {output_file} ({len(all_words)} words)")

        # 导出单独的分类文件
        for name, words in datasets.items():
            output_file = OUTPUT_DIR / f'ielts_vocabulary_{name}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(words, f, ensure_ascii=False, indent=2)
            print(f"- Exported {name}: {output_file} ({len(words)} words)")

    def export_to_csv(self, datasets: Dict[str, List[dict]]):
        """导出词汇数据到CSV文件"""
        for name, words in datasets.items():
            output_file = OUTPUT_DIR / f'ielts_vocabulary_{name}.csv'
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                if words:
                    # 标准化字段，确保所有数据有相同的字段
                    standard_fields = ['word', 'translation', 'pos', 'category', 'level', 'frequency', 'source']
                    writer = csv.DictWriter(f, fieldnames=standard_fields, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(words)
            print(f"- Exported CSV {name}: {output_file}")

    def generate_sql_inserts(self, datasets: Dict[str, List[dict]]):
        """生成SQL插入语句"""
        sql_file = OUTPUT_DIR / 'vocabulary_inserts.sql'
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write("-- IELTS Vocabulary Database Insert Statements\n")
            f.write("-- Generated: Auto-generated\n\n")

            all_words = []
            for words in datasets.values():
                all_words.extend(words)

            # 去重
            seen = set()
            unique_words = []
            for w in all_words:
                if w['word'].lower() not in seen:
                    seen.add(w['word'].lower())
                    unique_words.append(w)

            # 生成INSERT语句
            f.write("INSERT INTO vocabulary (word, translation, pos, category, level, frequency) VALUES\n")
            values = []
            for w in unique_words[:5000]:  # 限制数量避免SQL过大
                word = w['word'].replace("'", "''")
                trans = w['translation'].replace("'", "''")
                val = f"  ('{word}', '{trans}', '{w.get('pos', '')}', '{w.get('category', 'general')}', {w.get('level', 6)}, {w.get('frequency', 0)})"
                values.append(val)

            f.write(',\n'.join(values) + ';')

        print(f"- Generated SQL file: {sql_file}")

    def print_statistics(self, datasets: Dict[str, List[dict]]):
        """打印词汇统计信息"""
        print("\n" + "="*60)
        print("IELTS Vocabulary Generation Statistics")
        print("="*60)

        total = 0
        for name, words in datasets.items():
            count = len(words)
            total += count
            levels = {}
            categories = {}
            for w in words:
                l = w.get('level', 'unknown')
                levels[l] = levels.get(l, 0) + 1
                c = w.get('category', 'unknown')
                categories[c] = categories.get(c, 0) + 1

            print(f"\n[BOOK] {name.upper()}")
            print(f"   Total: {count} words")
            print(f"   Level distribution: {dict(sorted(levels.items()))}")
            print(f"   Category distribution: {dict(sorted(categories.items(), key=lambda x: -x[1]))}")

        print(f"\n[STATS] Total generated: {total} words")
        print("="*60)


def main():
    """主函数"""
    print("="*60)
    print("IELTS Vocabulary Data Generator")
    print("="*60)
    print()

    aggregator = VocabularyAggregator()

    # 生成所有词汇
    datasets = aggregator.generate_all_vocabularies()

    # 打印统计
    aggregator.print_statistics(datasets)

    # 导出数据
    print("\nExporting data...")
    aggregator.export_to_json(datasets, merge=True)
    aggregator.export_to_csv(datasets)
    aggregator.generate_sql_inserts(datasets)

    print("\n" + "="*60)
    print("- Vocabulary data generation completed!")
    print(f"- Output directory: {OUTPUT_DIR}")
    print("="*60)


if __name__ == '__main__':
    main()
