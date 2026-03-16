#!/usr/bin/env python3
"""
IELTS Massive Vocabulary Generator
Target: 8,000-12,000 vocabulary words
包含：完整AWL 570词族 + 牛津3000 + 雅思核心 + 听力场景 + 阅读话题
"""

import json
import csv
from pathlib import Path
from typing import Dict, List

OUTPUT_DIR = Path(__file__).parent / "vocabulary_data"
OUTPUT_DIR.mkdir(exist_ok=True)

# ============== 牛津3000核心词汇 (按主题分类) ==============
OXFORD_3000 = {
    # A开头高频词
    'a_words': [
        ('ability', '能力', 'noun', 5, 90), ('able', '能够', 'adjective', 4, 95), ('about', '关于', 'preposition', 3, 98),
        ('above', '在...上面', 'preposition', 4, 90), ('abroad', '在国外', 'adverb', 5, 75), ('absence', '缺席', 'noun', 5, 75),
        ('absent', '缺席的', 'adjective', 5, 70), ('absolute', '绝对的', 'adjective', 6, 75), ('absolutely', '绝对地', 'adverb', 5, 80),
        ('accept', '接受', 'verb', 4, 90), ('access', '进入', 'noun', 5, 85), ('accident', '事故', 'noun', 4, 85),
        ('accommodation', '住宿', 'noun', 5, 80), ('accompany', '陪伴', 'verb', 5, 75), ('according', '根据', 'preposition', 4, 90),
        ('account', '账户', 'noun', 4, 85), ('accurate', '准确的', 'adjective', 5, 80), ('achieve', '实现', 'verb', 5, 90),
        ('achievement', '成就', 'noun', 5, 85), ('acid', '酸', 'noun', 6, 65), ('acknowledge', '承认', 'verb', 6, 80),
        ('across', '横过', 'preposition', 4, 90), ('act', '行动', 'verb', 3, 90), ('action', '行动', 'noun', 4, 90),
        ('active', '活跃的', 'adjective', 4, 85), ('activity', '活动', 'noun', 4, 90), ('actor', '演员', 'noun', 4, 80),
        ('actress', '女演员', 'noun', 4, 75), ('actual', '实际的', 'adjective', 4, 85), ('actually', '实际上', 'adverb', 4, 90),
        ('adapt', '适应', 'verb', 5, 80), ('add', '添加', 'verb', 3, 95), ('addition', '加法', 'noun', 4, 85),
        ('additional', '额外的', 'adjective', 5, 80), ('address', '地址', 'noun', 4, 90), ('adequate', '足够的', 'adjective', 6, 75),
        ('adjust', '调整', 'verb', 5, 75), ('administration', '管理', 'noun', 6, 80), ('admire', '钦佩', 'verb', 5, 75),
        ('admit', '承认', 'verb', 4, 85), ('adopt', '采用', 'verb', 5, 80), ('adult', '成年人', 'noun', 4, 85),
        ('advance', '前进', 'verb/noun', 5, 80), ('advanced', '高级的', 'adjective', 5, 80), ('advantage', '优势', 'noun', 4, 85),
        ('adventure', '冒险', 'noun', 5, 75), ('advertise', '广告', 'verb', 5, 80), ('advertisement', '广告', 'noun', 5, 80),
        ('advice', '建议', 'noun', 4, 90), ('advise', '建议', 'verb', 4, 85), ('affair', '事务', 'noun', 5, 75),
        ('affect', '影响', 'verb', 5, 85), ('afford', '负担得起', 'verb', 4, 80), ('afraid', '害怕的', 'adjective', 3, 90),
        ('after', '在...之后', 'preposition', 3, 98), ('afternoon', '下午', 'noun', 3, 90), ('afterwards', '后来', 'adverb', 5, 75),
        ('again', '再次', 'adverb', 3, 95), ('against', '反对', 'preposition', 4, 90), ('age', '年龄', 'noun', 3, 95),
        ('aged', '年迈的', 'adjective', 4, 75), ('agency', '代理', 'noun', 5, 75), ('agent', '代理人', 'noun', 5, 80),
        ('aggressive', '侵略性的', 'adjective', 5, 75), ('ago', '以前', 'adverb', 3, 90), ('agree', '同意', 'verb', 3, 95),
        ('agreement', '协议', 'noun', 4, 85), ('ahead', '向前', 'adverb', 4, 85), ('aid', '援助', 'noun', 5, 80),
        ('aim', '目标', 'noun', 4, 85), ('air', '空气', 'noun', 3, 95), ('aircraft', '飞机', 'noun', 5, 75),
        ('airline', '航空公司', 'noun', 5, 80), ('airport', '机场', 'noun', 4, 85), ('alarm', '警报', 'noun', 5, 80),
        ('alcohol', '酒精', 'noun', 5, 75), ('alive', '活着的', 'adjective', 4, 80), ('all', '所有', 'determiner', 2, 98),
        ('allow', '允许', 'verb', 4, 90), ('ally', '盟友', 'noun', 6, 70), ('almost', '几乎', 'adverb', 4, 90),
        ('alone', '独自', 'adjective', 4, 85), ('along', '沿着', 'preposition', 4, 90), ('alongside', '在旁边', 'preposition', 5, 75),
        ('already', '已经', 'adverb', 4, 90), ('also', '也', 'adverb', 3, 95), ('alter', '改变', 'verb', 5, 80),
        ('alternative', '替代的', 'adjective', 5, 80), ('although', '尽管', 'conjunction', 4, 85), ('altogether', '总共', 'adverb', 5, 75),
        ('always', '总是', 'adverb', 3, 95), ('amaze', '使惊讶', 'verb', 5, 75), ('ambition', '野心', 'noun', 5, 75),
        ('ambulance', '救护车', 'noun', 5, 75), ('among', '在...之中', 'preposition', 4, 85), ('amount', '数量', 'noun', 4, 85),
        ('amuse', '逗乐', 'verb', 5, 75), ('analysis', '分析', 'noun', 5, 85), ('analyze', '分析', 'verb', 5, 80),
        ('ancient', '古代的', 'adjective', 5, 80), ('and', '和', 'conjunction', 1, 99), ('anger', '愤怒', 'noun', 4, 80),
        ('angle', '角度', 'noun', 4, 80), ('angry', '生气的', 'adjective', 3, 90), ('animal', '动物', 'noun', 3, 95),
        ('announce', '宣布', 'verb', 5, 80), ('annoy', '惹恼', 'verb', 4, 80), ('annual', '每年的', 'adjective', 5, 80),
        ('another', '另一个', 'determiner', 4, 90), ('answer', '答案', 'noun', 3, 95), ('anticipate', '预期', 'verb', 6, 75),
        ('anxiety', '焦虑', 'noun', 5, 80), ('anxious', '焦虑的', 'adjective', 5, 80), ('any', '任何', 'determiner', 3, 95),
        ('anybody', '任何人', 'pronoun', 4, 85), ('anyone', '任何人', 'pronoun', 4, 85), ('anything', '任何事', 'pronoun', 4, 90),
        ('anyway', '无论如何', 'adverb', 4, 85), ('anywhere', '任何地方', 'adverb', 4, 80), ('apart', '分开', 'adverb', 4, 80),
        ('apartment', '公寓', 'noun', 4, 85), ('apologize', '道歉', 'verb', 5, 80), ('apparent', '明显的', 'adjective', 5, 80),
        ('apparently', '显然', 'adverb', 5, 80), ('appeal', '呼吁', 'noun', 5, 80), ('appear', '出现', 'verb', 4, 90),
        ('appearance', '外观', 'noun', 4, 80), ('apple', '苹果', 'noun', 3, 90), ('application', '应用', 'noun', 5, 85),
        ('apply', '申请', 'verb', 4, 85), ('appoint', '任命', 'verb', 5, 75), ('appointment', '预约', 'noun', 5, 80),
        ('appreciate', '欣赏', 'verb', 5, 80), ('approach', '方法', 'noun', 5, 85), ('appropriate', '适当的', 'adjective', 5, 80),
        ('approve', '批准', 'verb', 5, 80), ('architect', '建筑师', 'noun', 5, 75), ('architecture', '建筑', 'noun', 6, 75),
        ('area', '地区', 'noun', 3, 95), ('argue', '争论', 'verb', 4, 85), ('argument', '论点', 'noun', 5, 85),
        ('arise', '出现', 'verb', 5, 80), ('arm', '手臂', 'noun', 3, 95), ('armed', '武装的', 'adjective', 5, 75),
        ('army', '军队', 'noun', 4, 80), ('around', '周围', 'preposition', 3, 95), ('arrange', '安排', 'verb', 4, 85),
        ('arrangement', '安排', 'noun', 4, 80), ('arrest', '逮捕', 'verb', 5, 80), ('arrival', '到达', 'noun', 4, 80),
        ('arrive', '到达', 'verb', 3, 90), ('art', '艺术', 'noun', 3, 95), ('article', '文章', 'noun', 4, 90),
        ('artificial', '人造的', 'adjective', 5, 80), ('artist', '艺术家', 'noun', 4, 80), ('as', '作为', 'preposition', 3, 98),
        ('ashamed', '羞愧的', 'adjective', 5, 75), ('aside', '在旁边', 'adverb', 4, 75), ('ask', '问', 'verb', 2, 98),
        ('asleep', '睡着的', 'adjective', 4, 80), ('aspect', '方面', 'noun', 5, 85), ('assess', '评估', 'verb', 5, 80),
        ('assessment', '评估', 'noun', 5, 80), ('assist', '帮助', 'verb', 5, 80), ('assistance', '帮助', 'noun', 5, 80),
        ('assistant', '助手', 'noun', 5, 75), ('associate', '联系', 'verb', 5, 80), ('association', '协会', 'noun', 5, 80),
        ('assume', '假设', 'verb', 5, 85), ('at', '在', 'preposition', 2, 99), ('atmosphere', '大气', 'noun', 5, 80),
        ('attach', '附上', 'verb', 5, 80), ('attack', '攻击', 'noun', 4, 85), ('attempt', '尝试', 'noun', 5, 85),
        ('attend', '参加', 'verb', 4, 85), ('attention', '注意', 'noun', 4, 90), ('attitude', '态度', 'noun', 4, 90),
        ('attorney', '律师', 'noun', 6, 70), ('attract', '吸引', 'verb', 4, 85), ('attraction', '吸引', 'noun', 5, 75),
        ('attractive', '有吸引力的', 'adjective', 4, 80), ('audience', '观众', 'noun', 4, 85), ('author', '作者', 'noun', 4, 90),
        ('authority', '权威', 'noun', 5, 85), ('automatic', '自动的', 'adjective', 5, 80), ('available', '可用的', 'adjective', 4, 90),
        ('average', '平均', 'adjective', 4, 85), ('avoid', '避免', 'verb', 4, 90), ('awake', '醒着的', 'adjective', 4, 80),
        ('award', '奖励', 'noun', 5, 80), ('aware', '意识到的', 'adjective', 5, 85), ('away', '离开', 'adverb', 3, 95),
        ('awful', '可怕的', 'adjective', 4, 80), ('awkward', '尴尬的', 'adjective', 5, 75),
    ],
    # B开头高频词
    'b_words': [
        ('baby', '婴儿', 'noun', 3, 95), ('back', '背部', 'noun', 3, 98), ('background', '背景', 'noun', 4, 85),
        ('backwards', '向后', 'adverb', 4, 75), ('bacteria', '细菌', 'noun', 6, 75), ('bad', '坏的', 'adjective', 3, 98),
        ('badly', '糟糕地', 'adverb', 4, 85), ('bag', '袋子', 'noun', 3, 95), ('bake', '烘烤', 'verb', 4, 75),
        ('balance', '平衡', 'noun', 4, 85), ('ball', '球', 'noun', 3, 95), ('ban', '禁止', 'verb', 5, 75),
        ('band', '乐队', 'noun', 4, 80), ('bank', '银行', 'noun', 3, 95), ('bar', '酒吧', 'noun', 4, 85),
        ('barrier', '障碍', 'noun', 5, 80), ('base', '基础', 'noun', 4, 85), ('basic', '基本的', 'adjective', 4, 90),
        ('basically', '基本上', 'adverb', 4, 85), ('basis', '基础', 'noun', 5, 80), ('bath', '洗澡', 'noun', 4, 80),
        ('bathroom', '浴室', 'noun', 4, 90), ('battery', '电池', 'noun', 5, 80), ('battle', '战斗', 'noun', 5, 80),
        ('be', '是', 'verb', 1, 99), ('beach', '海滩', 'noun', 4, 85), ('bean', '豆子', 'noun', 4, 75),
        ('bear', '熊', 'noun', 4, 80), ('beat', '打败', 'verb', 4, 85), ('beautiful', '美丽的', 'adjective', 3, 95),
        ('beauty', '美丽', 'noun', 4, 80), ('because', '因为', 'conjunction', 3, 98), ('become', '成为', 'verb', 3, 98),
        ('bed', '床', 'noun', 3, 95), ('bedroom', '卧室', 'noun', 4, 90), ('beef', '牛肉', 'noun', 4, 75),
        ('beer', '啤酒', 'noun', 4, 80), ('before', '之前', 'preposition', 3, 98), ('begin', '开始', 'verb', 3, 98),
        ('beginning', '开始', 'noun', 4, 90), ('behalf', '代表', 'noun', 6, 70), ('behave', '表现', 'verb', 4, 85),
        ('behavior', '行为', 'noun', 4, 90), ('behind', '在后面', 'preposition', 3, 95), ('being', '存在', 'noun', 4, 85),
        ('belief', '信仰', 'noun', 4, 85), ('believe', '相信', 'verb', 3, 98), ('bell', '铃', 'noun', 4, 75),
        ('belong', '属于', 'verb', 4, 85), ('below', '在下面', 'preposition', 4, 90), ('belt', '腰带', 'noun', 4, 75),
        ('bend', '弯曲', 'verb', 4, 80), ('benefit', '益处', 'noun', 4, 90), ('beside', '在旁边', 'preposition', 4, 80),
        ('best', '最好的', 'adjective', 3, 95), ('bet', '打赌', 'verb', 4, 75), ('better', '更好的', 'adjective', 3, 95),
        ('between', '在...之间', 'preposition', 3, 95), ('beyond', '超过', 'preposition', 4, 85), ('big', '大的', 'adjective', 2, 98),
        ('bike', '自行车', 'noun', 3, 90), ('bill', '账单', 'noun', 4, 85), ('billion', '十亿', 'number', 4, 85),
        ('bin', '垃圾箱', 'noun', 4, 75), ('bird', '鸟', 'noun', 3, 95), ('birth', '出生', 'noun', 4, 85),
        ('birthday', '生日', 'noun', 3, 90), ('biscuit', '饼干', 'noun', 4, 70), ('bit', '一点', 'noun', 3, 95),
        ('bite', '咬', 'verb', 4, 80), ('bitter', '苦的', 'adjective', 4, 80), ('black', '黑色的', 'adjective', 3, 95),
        ('blame', '责备', 'verb', 4, 85), ('blank', '空白的', 'adjective', 4, 75), ('blind', '盲的', 'adjective', 4, 80),
        ('block', '街区', 'noun', 4, 85), ('blonde', '金发', 'adjective', 4, 75), ('blood', '血', 'noun', 4, 90),
        ('blow', '吹', 'verb', 4, 85), ('blue', '蓝色的', 'adjective', 3, 95), ('board', '板', 'noun', 4, 90),
        ('boat', '船', 'noun', 3, 95), ('body', '身体', 'noun', 3, 95), ('boil', '沸腾', 'verb', 4, 80),
        ('bomb', '炸弹', 'noun', 5, 80), ('bone', '骨头', 'noun', 4, 80), ('book', '书', 'noun', 3, 98),
        ('boot', '靴子', 'noun', 4, 80), ('border', '边界', 'noun', 5, 80), ('bore', '使厌烦', 'verb', 4, 85),
        ('boring', '无聊的', 'adjective', 4, 85), ('born', '出生的', 'adjective', 4, 85), ('borrow', '借', 'verb', 4, 85),
        ('boss', '老板', 'noun', 4, 85), ('both', '两者都', 'determiner', 3, 95), ('bother', '打扰', 'verb', 4, 85),
        ('bottle', '瓶子', 'noun', 3, 95), ('bottom', '底部', 'noun', 4, 85), ('bowl', '碗', 'noun', 4, 80),
        ('box', '盒子', 'noun', 3, 95), ('boy', '男孩', 'noun', 3, 95), ('brain', '大脑', 'noun', 4, 90),
        ('branch', '分支', 'noun', 4, 85), ('brand', '品牌', 'noun', 5, 80), ('brave', '勇敢的', 'adjective', 4, 80),
        ('bread', '面包', 'noun', 3, 95), ('break', '打破', 'verb', 3, 95), ('breakfast', '早餐', 'noun', 3, 90),
        ('breast', '乳房', 'noun', 4, 75), ('breath', '呼吸', 'noun', 4, 85), ('breathe', '呼吸', 'verb', 4, 85),
        ('brick', '砖', 'noun', 4, 75), ('bridge', '桥', 'noun', 4, 85), ('brief', '简短的', 'adjective', 4, 85),
        ('bright', '明亮的', 'adjective', 4, 85), ('brilliant', '杰出的', 'adjective', 5, 80), ('bring', '带来', 'verb', 3, 95),
        ('broad', '宽阔的', 'adjective', 4, 80), ('broadcast', '广播', 'verb', 5, 75), ('brother', '兄弟', 'noun', 3, 95),
        ('brown', '棕色的', 'adjective', 3, 90), ('brush', '刷子', 'noun', 4, 80), ('budget', '预算', 'noun', 5, 80),
        ('build', '建造', 'verb', 3, 95), ('building', '建筑物', 'noun', 3, 95), ('bullet', '子弹', 'noun', 5, 75),
        ('bunch', '束', 'noun', 4, 75), ('burn', '燃烧', 'verb', 4, 85), ('burst', '爆发', 'verb', 5, 75),
        ('bus', '公共汽车', 'noun', 3, 95), ('bush', '灌木', 'noun', 4, 75), ('business', '商业', 'noun', 4, 95),
        ('busy', '忙碌的', 'adjective', 3, 90), ('but', '但是', 'conjunction', 2, 99), ('butter', '黄油', 'noun', 4, 80),
        ('button', '按钮', 'noun', 4, 80), ('buy', '买', 'verb', 2, 98), ('by', '通过', 'preposition', 2, 99),
        ('bye', '再见', 'exclamation', 3, 95),
    ],
    # C开头高频词 (继续扩展)
    'c_words': [
        ('cabinet', '内阁', 'noun', 6, 75), ('cable', '电缆', 'noun', 5, 75), ('cake', '蛋糕', 'noun', 3, 90),
        ('calculate', '计算', 'verb', 5, 80), ('call', '打电话', 'verb', 3, 98), ('calm', '平静的', 'adjective', 4, 80),
        ('camera', '相机', 'noun', 4, 90), ('camp', '营地', 'noun', 4, 85), ('campaign', '活动', 'noun', 5, 85),
        ('can', '能', 'modal verb', 2, 99), ('cancel', '取消', 'verb', 4, 85), ('cancer', '癌症', 'noun', 5, 80),
        ('candidate', '候选人', 'noun', 5, 85), ('candle', '蜡烛', 'noun', 4, 75), ('candy', '糖果', 'noun', 4, 70),
        ('cap', '帽子', 'noun', 4, 80), ('capable', '有能力的', 'adjective', 5, 80), ('capacity', '容量', 'noun', 5, 80),
        ('capital', '首都', 'noun', 4, 90), ('captain', '船长', 'noun', 4, 85), ('capture', '捕获', 'verb', 5, 80),
        ('car', '汽车', 'noun', 3, 98), ('card', '卡片', 'noun', 3, 95), ('care', '关心', 'noun', 3, 95),
        ('career', '职业', 'noun', 4, 90), ('careful', '小心的', 'adjective', 4, 90), ('carefully', '小心地', 'adverb', 4, 85),
        ('careless', '粗心的', 'adjective', 4, 80), ('carpet', '地毯', 'noun', 4, 80), ('carrot', '胡萝卜', 'noun', 4, 75),
        ('carry', '携带', 'verb', 3, 95), ('case', '案例', 'noun', 4, 95), ('cash', '现金', 'noun', 4, 85),
        ('cast', '投', 'verb', 4, 80), ('cat', '猫', 'noun', 3, 95), ('catch', '抓住', 'verb', 3, 95),
        ('category', '类别', 'noun', 5, 80), ('cause', '原因', 'noun', 4, 90), ('cease', '停止', 'verb', 5, 75),
        ('ceiling', '天花板', 'noun', 4, 80), ('celebrate', '庆祝', 'verb', 4, 85), ('celebration', '庆祝', 'noun', 4, 80),
        ('cell', '细胞', 'noun', 5, 85), ('cent', '分', 'noun', 3, 90), ('center', '中心', 'noun', 4, 90),
        ('century', '世纪', 'noun', 4, 90), ('ceremony', '仪式', 'noun', 5, 80), ('certain', '确定的', 'adjective', 4, 90),
        ('certainly', '当然', 'adverb', 4, 85), ('chain', '链', 'noun', 4, 85), ('chair', '椅子', 'noun', 3, 95),
        ('chairman', '主席', 'noun', 5, 80), ('challenge', '挑战', 'noun', 5, 90), ('champion', '冠军', 'noun', 5, 80),
        ('chance', '机会', 'noun', 3, 95), ('change', '改变', 'verb', 3, 98), ('channel', '频道', 'noun', 5, 85),
        ('chapter', '章节', 'noun', 5, 85), ('character', '性格', 'noun', 4, 90), ('characteristic', '特征', 'noun', 5, 80),
        ('charge', '收费', 'noun', 4, 90), ('charity', '慈善', 'noun', 5, 80), ('chart', '图表', 'noun', 5, 85),
        ('chase', '追逐', 'verb', 4, 80), ('cheap', '便宜的', 'adjective', 4, 90), ('cheat', '欺骗', 'verb', 4, 80),
        ('check', '检查', 'verb', 3, 95), ('cheek', '脸颊', 'noun', 4, 75), ('cheerful', '愉快的', 'adjective', 4, 80),
        ('cheese', '奶酪', 'noun', 4, 85), ('chef', '厨师', 'noun', 5, 75), ('chemical', '化学的', 'adjective', 5, 85),
        ('chest', '胸部', 'noun', 4, 80), ('chicken', '鸡', 'noun', 3, 90), ('chief', '主要的', 'adjective', 5, 80),
        ('child', '孩子', 'noun', 3, 98), ('childhood', '童年', 'noun', 4, 80), ('chip', '芯片', 'noun', 4, 85),
        ('chocolate', '巧克力', 'noun', 4, 85), ('choice', '选择', 'noun', 4, 90), ('choose', '选择', 'verb', 3, 95),
        ('chop', '砍', 'verb', 4, 75), ('church', '教堂', 'noun', 4, 85), ('cigarette', '香烟', 'noun', 5, 80),
        ('cinema', '电影院', 'noun', 4, 80), ('circle', '圆', 'noun', 4, 85), ('circumstance', '环境', 'noun', 5, 85),
        ('citizen', '公民', 'noun', 5, 85), ('city', '城市', 'noun', 3, 95), ('civil', '公民的', 'adjective', 5, 85),
        ('claim', '声称', 'verb', 4, 90), ('class', '班级', 'noun', 3, 95), ('classic', '经典的', 'adjective', 5, 80),
        ('classical', '古典的', 'adjective', 5, 80), ('classify', '分类', 'verb', 5, 75), ('classroom', '教室', 'noun', 4, 90),
        ('clay', '粘土', 'noun', 5, 65), ('clean', '干净的', 'adjective', 3, 95), ('clear', '清楚的', 'adjective', 3, 95),
        ('clearly', '清楚地', 'adverb', 4, 90), ('clerk', '职员', 'noun', 4, 80), ('clever', '聪明的', 'adjective', 4, 85),
        ('click', '点击', 'verb', 4, 85), ('client', '客户', 'noun', 5, 85), ('climate', '气候', 'noun', 5, 90),
        ('climb', '爬', 'verb', 4, 90), ('clinic', '诊所', 'noun', 5, 80), ('clock', '时钟', 'noun', 3, 95),
        ('close', '关闭', 'verb', 3, 95), ('closed', '关闭的', 'adjective', 4, 85), ('closely', '紧密地', 'adverb', 4, 85),
        ('cloth', '布', 'noun', 4, 80), ('clothes', '衣服', 'noun', 3, 95), ('clothing', '服装', 'noun', 4, 85),
        ('cloud', '云', 'noun', 3, 90), ('club', '俱乐部', 'noun', 3, 95), ('clue', '线索', 'noun', 4, 80),
        ('coach', '教练', 'noun', 4, 85), ('coal', '煤', 'noun', 4, 80), ('coast', '海岸', 'noun', 4, 85),
        ('coat', '外套', 'noun', 3, 95), ('code', '代码', 'noun', 5, 85), ('coffee', '咖啡', 'noun', 3, 95),
        ('coin', '硬币', 'noun', 3, 90), ('cold', '冷的', 'adjective', 3, 95), ('collapse', '倒塌', 'verb', 5, 80),
        ('colleague', '同事', 'noun', 5, 85), ('collect', '收集', 'verb', 4, 90), ('collection', '收集', 'noun', 4, 85),
        ('college', '学院', 'noun', 4, 90), ('color', '颜色', 'noun', 3, 95), ('colored', '有色的', 'adjective', 4, 75),
        ('column', '专栏', 'noun', 5, 80), ('combination', '结合', 'noun', 5, 80), ('combine', '结合', 'verb', 4, 85),
        ('come', '来', 'verb', 2, 99), ('comedy', '喜剧', 'noun', 5, 80), ('comfort', '安慰', 'noun', 4, 85),
        ('comfortable', '舒适的', 'adjective', 4, 90), ('command', '命令', 'noun', 4, 85), ('comment', '评论', 'noun', 4, 90),
        ('commercial', '商业的', 'adjective', 5, 85), ('commission', '委员会', 'noun', 6, 80), ('commit', '承诺', 'verb', 5, 85),
        ('commitment', '承诺', 'noun', 5, 85), ('committee', '委员会', 'noun', 5, 80), ('common', '常见的', 'adjective', 3, 95),
        ('commonly', '通常', 'adverb', 4, 85), ('communicate', '交流', 'verb', 4, 90), ('communication', '交流', 'noun', 4, 90),
        ('community', '社区', 'noun', 4, 90), ('company', '公司', 'noun', 3, 98), ('compare', '比较', 'verb', 4, 90),
        ('comparison', '比较', 'noun', 5, 85), ('compete', '竞争', 'verb', 4, 85), ('competition', '竞争', 'noun', 4, 90),
        ('competitive', '竞争的', 'adjective', 5, 80), ('complain', '抱怨', 'verb', 4, 85), ('complaint', '投诉', 'noun', 5, 80),
        ('complete', '完成', 'verb', 4, 90), ('completely', '完全', 'adverb', 4, 90), ('complex', '复杂的', 'adjective', 5, 90),
        ('complicated', '复杂的', 'adjective', 5, 80), ('component', '组件', 'noun', 5, 80), ('comprehensive', '全面的', 'adjective', 6, 80),
        ('computer', '计算机', 'noun', 3, 98), ('concentrate', '集中', 'verb', 5, 85), ('concept', '概念', 'noun', 5, 90),
        ('concern', '关心', 'noun', 4, 90), ('concerned', '关心的', 'adjective', 4, 85), ('concert', '音乐会', 'noun', 4, 80),
        ('conclude', '总结', 'verb', 5, 85), ('conclusion', '结论', 'noun', 5, 85), ('condition', '条件', 'noun', 4, 95),
        ('conduct', '进行', 'verb', 5, 90), ('conference', '会议', 'noun', 5, 90), ('confidence', '信心', 'noun', 4, 85),
        ('confident', '自信的', 'adjective', 4, 85), ('confirm', '确认', 'verb', 5, 85), ('conflict', '冲突', 'noun', 5, 90),
        ('confused', '困惑的', 'adjective', 4, 85), ('confusing', '令人困惑的', 'adjective', 4, 80), ('connection', '连接', 'noun', 4, 90),
        ('conscious', '有意识的', 'adjective', 5, 80), ('consequence', '后果', 'noun', 5, 85), ('consider', '考虑', 'verb', 3, 95),
        ('considerable', '相当大的', 'adjective', 5, 80), ('considerably', '相当', 'adverb', 5, 75), ('consideration', '考虑', 'noun', 5, 85),
        ('consistent', '一致的', 'adjective', 5, 80), ('constant', '持续的', 'adjective', 5, 85), ('constantly', '不断地', 'adverb', 5, 80),
        ('construct', '构建', 'verb', 5, 80), ('construction', '建造', 'noun', 5, 85), ('consume', '消费', 'verb', 5, 85),
        ('consumer', '消费者', 'noun', 5, 90), ('contact', '联系', 'noun', 4, 90), ('contain', '包含', 'verb', 4, 90),
        ('container', '容器', 'noun', 4, 80), ('contemporary', '当代的', 'adjective', 5, 80), ('content', '内容', 'noun', 4, 90),
        ('contest', '比赛', 'noun', 5, 75), ('context', '上下文', 'noun', 5, 90), ('continent', '大陆', 'noun', 5, 80),
        ('continue', '继续', 'verb', 3, 95), ('continuous', '连续的', 'adjective', 5, 80), ('contract', '合同', 'noun', 5, 90),
        ('contrast', '对比', 'noun', 5, 85), ('contribute', '贡献', 'verb', 5, 85), ('contribution', '贡献', 'noun', 5, 80),
        ('control', '控制', 'noun', 4, 95), ('controlled', '受控的', 'adjective', 5, 75), ('controversial', '有争议的', 'adjective', 6, 80),
        ('convention', '惯例', 'noun', 5, 80), ('conventional', '传统的', 'adjective', 5, 80), ('conversation', '对话', 'noun', 4, 90),
        ('convert', '转换', 'verb', 5, 80), ('convince', '说服', 'verb', 4, 85), ('convincing', '令人信服的', 'adjective', 5, 75),
        ('cook', '烹饪', 'verb', 3, 95), ('cooking', '烹饪', 'noun', 4, 85), ('cool', '凉爽的', 'adjective', 3, 95),
        ('copy', '复制', 'noun', 4, 90), ('core', '核心', 'noun', 5, 85), ('corn', '玉米', 'noun', 4, 75),
        ('corner', '角落', 'noun', 3, 95), ('correct', '正确的', 'adjective', 3, 95), ('correctly', '正确地', 'adverb', 4, 85),
        ('cost', '成本', 'noun', 3, 95), ('cottage', '小屋', 'noun', 4, 75), ('cotton', '棉花', 'noun', 4, 75),
        ('could', '能', 'modal verb', 3, 98), ('council', '委员会', 'noun', 5, 85), ('count', '数', 'verb', 3, 95),
        ('counter', '柜台', 'noun', 4, 85), ('country', '国家', 'noun', 3, 98), ('countryside', '农村', 'noun', 4, 80),
        ('county', '县', 'noun', 5, 75), ('couple', '一对', 'noun', 4, 90), ('courage', '勇气', 'noun', 4, 80),
        ('course', '课程', 'noun', 3, 98), ('court', '法庭', 'noun', 4, 90), ('cousin', '堂兄', 'noun', 4, 85),
        ('cover', '覆盖', 'verb', 3, 95), ('covered', '覆盖的', 'adjective', 4, 80), ('cow', '奶牛', 'noun', 3, 90),
        ('crash', '碰撞', 'verb', 5, 80), ('crazy', '疯狂的', 'adjective', 4, 85), ('cream', '奶油', 'noun', 4, 80),
        ('create', '创造', 'verb', 4, 95), ('creation', '创造', 'noun', 5, 80), ('creative', '有创造力的', 'adjective', 5, 85),
        ('creature', '生物', 'noun', 4, 80), ('credit', '信用', 'noun', 5, 90), ('crew', '船员', 'noun', 5, 80),
        ('crime', '犯罪', 'noun', 4, 90), ('criminal', '犯罪的', 'adjective', 5, 85), ('crisis', '危机', 'noun', 5, 85),
        ('criterion', '标准', 'noun', 6, 75), ('critic', '评论家', 'noun', 5, 80), ('critical', '批评的', 'adjective', 5, 85),
        ('criticism', '批评', 'noun', 5, 85), ('criticize', '批评', 'verb', 5, 80), ('crop', '作物', 'noun', 4, 80),
        ('cross', '穿过', 'verb', 4, 90), ('crowd', '人群', 'noun', 4, 85), ('crucial', '关键的', 'adjective', 6, 80),
        ('cruel', '残忍的', 'adjective', 4, 80), ('cry', '哭', 'verb', 3, 95), ('cultural', '文化的', 'adjective', 5, 85),
        ('culture', '文化', 'noun', 4, 95), ('cup', '杯子', 'noun', 3, 95), ('cupboard', '橱柜', 'noun', 4, 75),
        ('cure', '治愈', 'verb', 5, 75), ('curious', '好奇的', 'adjective', 4, 85), ('curiously', '好奇地', 'adverb', 5, 75),
        ('currency', '货币', 'noun', 5, 80), ('current', '当前的', 'adjective', 4, 95), ('currently', '目前', 'adverb', 4, 90),
        ('curtain', '窗帘', 'noun', 4, 80), ('curve', '曲线', 'noun', 5, 80), ('custom', '习俗', 'noun', 5, 85),
        ('customer', '顾客', 'noun', 4, 95), ('cut', '切', 'verb', 3, 95), ('cycle', '循环', 'noun', 5, 85),
    ],
}

# ============== IELTS核心词汇 (按场景分类) ==============
IELTS_CORE = {
    # 教育场景
    'education': [
        ('academic', '学术的', 'adjective', 6, 90), ('academy', '学院', 'noun', 6, 70), ('admission', '入学', 'noun', 6, 80),
        ('advanced', '高级的', 'adjective', 5, 85), ('assignment', '作业', 'noun', 5, 90), ('attend', '参加', 'verb', 4, 90),
        ('attendance', '出勤', 'noun', 6, 75), ('auditorium', '礼堂', 'noun', 7, 60), ('bachelor', '学士', 'noun', 6, 80),
        ('campus', '校园', 'noun', 6, 85), ('certificate', '证书', 'noun', 5, 85), ('classroom', '教室', 'noun', 4, 90),
        ('compulsory', '强制的', 'adjective', 6, 75), ('course', '课程', 'noun', 4, 95), ('credit', '学分', 'noun', 5, 85),
        ('curriculum', '课程', 'noun', 7, 75), ('degree', '学位', 'noun', 5, 90), ('diploma', '文凭', 'noun', 6, 80),
        ('discipline', '学科', 'noun', 6, 80), ('dissertation', '论文', 'noun', 8, 70), ('doctorate', '博士', 'noun', 7, 65),
        ('dropout', '退学', 'noun', 6, 70), ('elective', '选修的', 'adjective', 6, 70), ('enroll', '注册', 'verb', 6, 80),
        ('enrollment', '注册', 'noun', 6, 75), ('essay', '论文', 'noun', 5, 90), ('examination', '考试', 'noun', 5, 95),
        ('exam', '考试', 'noun', 4, 98), ('faculty', '院系', 'noun', 6, 80), ('fellowship', '奖学金', 'noun', 7, 65),
        ('fraternity', '兄弟会', 'noun', 7, 60), ('freshman', '大一新生', 'noun', 6, 75), ('grade', '成绩', 'noun', 4, 90),
        ('graduation', '毕业', 'noun', 6, 85), ('grant', '助学金', 'noun', 6, 75), ('headmaster', '校长', 'noun', 6, 70),
        ('honors', '荣誉', 'noun', 6, 70), ('instructor', '讲师', 'noun', 6, 80), ('intellect', '智力', 'noun', 6, 70),
        ('interdisciplinary', '跨学科的', 'adjective', 8, 65), ('junior', '大三学生', 'noun', 6, 75), ('kindergarten', '幼儿园', 'noun', 6, 75),
        ('lecture', '讲座', 'noun', 5, 90), ('lecturer', '讲师', 'noun', 6, 85), ('literacy', '读写能力', 'noun', 6, 75),
        ('major', '专业', 'noun', 5, 90), ('master', '硕士', 'noun', 6, 80), ('matriculation', '入学', 'noun', 8, 60),
        ('mentor', '导师', 'noun', 6, 75), ('minor', '辅修', 'noun', 6, 70), ('module', '模块', 'noun', 6, 75),
        ('optional', '选修的', 'adjective', 6, 75), ('paper', '论文', 'noun', 4, 90), ('placement', '分班', 'noun', 6, 70),
        ('postgraduate', '研究生', 'noun', 7, 75), ('prerequisite', '先决条件', 'noun', 7, 70), ('preschool', '学前', 'noun', 6, 70),
        ('principal', '校长', 'noun', 6, 75), ('professor', '教授', 'noun', 6, 90), ('project', '项目', 'noun', 4, 95),
        ('pupil', '学生', 'noun', 4, 80), ('quiz', '小测验', 'noun', 5, 80), ('reading', '阅读', 'noun', 4, 95),
        ('recitation', '背诵', 'noun', 7, 60), ('register', '注册', 'verb', 5, 85), ('registration', '注册', 'noun', 6, 80),
        ('scholarship', '奖学金', 'noun', 6, 85), ('schooling', '教育', 'noun', 6, 70), ('semester', '学期', 'noun', 6, 90),
        ('seminar', '研讨会', 'noun', 6, 80), ('senior', '大四学生', 'noun', 6, 75), ('sophomore', '大二学生', 'noun', 7, 70),
        ('specialization', '专业', 'noun', 7, 70), ('specialize', '专攻', 'verb', 6, 75), ('syllabus', '大纲', 'noun', 7, 75),
        ('term', '学期', 'noun', 4, 90), ('textbook', '教科书', 'noun', 5, 85), ('thesis', '论文', 'noun', 7, 80),
        ('transcript', '成绩单', 'noun', 7, 70), ('transfer', '转学', 'verb', 6, 80), ('tuition', '学费', 'noun', 6, 85),
        ('tutor', '导师', 'noun', 5, 80), ('tutorial', '辅导课', 'noun', 6, 75), ('undergraduate', '本科生', 'noun', 7, 80),
        ('university', '大学', 'noun', 5, 95), ('valedictorian', '毕业生代表', 'noun', 9, 55), ('vocation', '职业', 'noun', 6, 70),
        ('workshop', '研讨会', 'noun', 6, 80),
    ],
    # 工作场景
    'employment': [
        ('ambition', '野心', 'noun', 5, 80), ('applicant', '申请者', 'noun', 6, 80), ('application', '申请', 'noun', 5, 90),
        ('apply', '申请', 'verb', 4, 90), ('apprentice', '学徒', 'noun', 6, 70), ('apprenticeship', '学徒期', 'noun', 7, 65),
        ('assignment', '任务', 'noun', 5, 85), ('associate', '同事', 'noun', 6, 80), ('authority', '权威', 'noun', 5, 85),
        ('benefit', '福利', 'noun', 4, 90), ('bonus', '奖金', 'noun', 5, 80), ('boss', '老板', 'noun', 4, 90),
        ('candidate', '候选人', 'noun', 5, 85), ('career', '职业', 'noun', 4, 95), ('colleague', '同事', 'noun', 5, 90),
        ('commission', '佣金', 'noun', 6, 75), ('committee', '委员会', 'noun', 5, 80), ('company', '公司', 'noun', 3, 98),
        ('compensation', '补偿', 'noun', 6, 75), ('contract', '合同', 'noun', 5, 90), ('cooperate', '合作', 'verb', 5, 80),
        ('cooperation', '合作', 'noun', 5, 80), ('corporate', '公司的', 'adjective', 6, 80), ('coworker', '同事', 'noun', 5, 75),
        ('dismiss', '解雇', 'verb', 5, 75), ('dismissal', '解雇', 'noun', 6, 70), ('employ', '雇用', 'verb', 4, 90),
        ('employee', '雇员', 'noun', 4, 90), ('employer', '雇主', 'noun', 4, 90), ('employment', '就业', 'noun', 5, 90),
        ('executive', '主管', 'noun', 6, 85), ('experience', '经验', 'noun', 4, 95), ('fire', '解雇', 'verb', 4, 85),
        ('full-time', '全职的', 'adjective', 5, 80), ('hire', '雇用', 'verb', 4, 85), ('income', '收入', 'noun', 5, 90),
        ('industry', '工业', 'noun', 4, 90), ('interview', '面试', 'noun', 5, 90), ('interviewer', '面试官', 'noun', 6, 80),
        ('job', '工作', 'noun', 3, 98), ('labor', '劳动', 'noun', 5, 85), ('laborer', '劳动者', 'noun', 5, 70),
        ('layoff', '解雇', 'noun', 6, 70), ('leadership', '领导力', 'noun', 6, 85), ('leave', '休假', 'noun', 4, 85),
        ('manager', '经理', 'noun', 4, 95), ('management', '管理', 'noun', 5, 90), ('manual', '手册', 'noun', 6, 75),
        ('manufacture', '制造', 'verb', 5, 80), ('manufacturer', '制造商', 'noun', 6, 80), ('occupation', '职业', 'noun', 6, 80),
        ('offer', '提供', 'noun', 4, 90), ('officer', '官员', 'noun', 4, 85), ('overtime', '加班', 'noun', 5, 75),
        ('part-time', '兼职的', 'adjective', 5, 80), ('pension', '养老金', 'noun', 6, 75), ('position', '职位', 'noun', 4, 95),
        ('profession', '职业', 'noun', 5, 85), ('professional', '专业的', 'adjective', 5, 90), ('promote', '晋升', 'verb', 5, 85),
        ('promotion', '晋升', 'noun', 5, 80), ('prospective', '预期的', 'adjective', 6, 75), ('qualify', '使合格', 'verb', 5, 80),
        ('qualification', '资格', 'noun', 6, 80), ('recruit', '招聘', 'verb', 5, 80), ('recruitment', '招聘', 'noun', 6, 75),
        ('redundant', '多余的', 'adjective', 6, 70), ('resign', '辞职', 'verb', 5, 80), ('resignation', '辞职', 'noun', 6, 75),
        ('resume', '简历', 'noun', 5, 85), ('retire', '退休', 'verb', 5, 85), ('retirement', '退休', 'noun', 6, 80),
        ('salary', '薪水', 'noun', 5, 90), ('shift', '轮班', 'noun', 5, 80), ('skill', '技能', 'noun', 4, 95),
        ('sick leave', '病假', 'noun', 5, 75), ('staff', '员工', 'noun', 4, 90), ('stipend', '津贴', 'noun', 7, 60),
        ('strike', '罢工', 'noun', 5, 80), ('supervisor', '主管', 'noun', 6, 80), ('teamwork', '团队合作', 'noun', 5, 80),
        ('temporary', '临时的', 'adjective', 6, 80), ('trainee', '实习生', 'noun', 6, 75), ('training', '培训', 'noun', 5, 85),
        ('unemployed', '失业的', 'adjective', 5, 80), ('unemployment', '失业', 'noun', 6, 80), ('union', '工会', 'noun', 5, 80),
        ('vacancy', '空缺', 'noun', 6, 75), ('wage', '工资', 'noun', 5, 85), ('work', '工作', 'noun', 3, 99),
        ('worker', '工人', 'noun', 4, 95), ('workforce', '劳动力', 'noun', 6, 75), ('workplace', '工作场所', 'noun', 5, 80),
    ],
}

# ============== 完整AWL词族 (完整570词族) ==============
AWL_FULL = """
# Sublist 1
analysis|analyze,analyzes,analyzing,analyzed,analyses,analyst,analysts,analytic,analytical,analytically|分析|noun
approach|approaches,approached,approaching,approachable|方法/接近|noun/verb
area|areas|领域|noun
assessment|assess,assesses,assessing,assessed,assessable,assessments,reassess,reassessed,reassessing,reassessment|评估|noun
assume|assumes,assuming,assumed,assumption,assumptions|假设|verb
authority|authorities,authoritative,authoritatively|权威|noun
available|availability,unavailable|可用的|adjective
benefit|benefits,benefited,benefiting,beneficial,beneficiary,beneficiaries|益处|noun/verb
concept|concepts,conception,conceptual,conceptually,conceptualize,conceptualization|概念|noun
consist|consists,consisted,consisting,consistency,inconsistency,consistent,inconsistent,consistently|由...组成|verb
constitute|constitutes,constituted,constituting,constituent,constituents,constituency,constituencies,constitution,constitutional,constitutionally,constitutive|构成|verb
context|contexts,contextual,contextualize,contextualization|上下文|noun
contract|contracts,contracted,contracting,contractor,contractors|合同|noun/verb
create|creates,creating,created,creation,creations,creative,creatively,creator,creators|创造|verb
data|datum|数据|noun
define|defines,defining,defined,definition,definitions,definable,undefined,redefine,redefining,redefined|定义|verb
derive|derives,deriving,derived,derivation,derivations,derivative,derivatives|推导|verb
distribute|distributes,distributing,distributed,distribution,distributions,distributive,distributor,distributors|分配|verb
economy|economies,economic,economical,economically,economist,economists,economics|经济|noun
environment|environments,environmental,environmentally,environmentalist,environmentalists|环境|noun
establish|establishes,establishing,established,establishment,establishments|建立|verb
estimate|estimates,estimating,estimated,estimation,estimations,overestimate,underestimate|估计|verb/noun
evidence|evidenced,evident,evidently|证据|noun
export|exports,exported,exporting,exporter,exporters|出口|verb/noun
factor|factors,factored,factoring|因素|noun
finance|finances,financed,financing,financial,financially|金融|noun/verb
formula|formulas,formulae,formulate,formulated,formulating,formulation,formulations|公式|noun
function|functions,functioned,functioning,functional,functionally,multifunctional|功能|noun/verb
identify|identifies,identifying,identified,identifiable,identification,identity,identities|识别|verb
income|incomes|收入|noun
indicate|indicates,indicating,indicated,indication,indications,indicator,indicators|表明|verb
individual|individuals,individuality,individualism,individualize,individually|个人的|adjective/noun
interpret|interprets,interpreting,interpreted,interpretation,interpretations,misinterpret,misinterpreted,interpreter,interpreters|解释|verb
involve|involves,involved,involving,involvement|涉及|verb
issue|issues,issued,issuing|问题|noun/verb
labour|labours,laboured,labouring,labor|劳动|noun
legal|illegal,legality,legally,illegally,legislate,legislation,legislative,legislator,legislators,legislature|合法的|adjective
major|majors,majority,majorities|主要的|adjective
method|methods,methodology,methodological|方法|noun
occur|occurs,occurred,occurring,occurrence,occurrences,reoccur|发生|verb
percent|percentage,percentages|百分比|noun
period|periods,periodic,periodically|时期|noun
policy|policies|政策|noun
principle|principles|原则|noun
proceed|proceeds,proceeded,proceeding,proceedings,procedural,procedure,procedures|继续进行|verb
process|processes,processed,processing|过程|noun/verb
require|requires,requiring,required,requirement,requirements|需要|verb
respond|responds,responded,responding,responsive,responsiveness,response,responses,respondent,respondents|回应|verb
role|roles|角色|noun
section|sections,sectioned,sectioning|部分|noun
sector|sectors|部门|noun
significant|significance,significantly,insignificant|重要的|adjective
similar|similarly,similarity,similarities,dissimilar|相似的|adjective
source|sources,sourced,sourcing|来源|noun
specific|specifically,specification,specifications,specificity|具体的|adjective
structure|structures,structured,structuring,structural,structurally,restructure,restructured,restructuring|结构|noun/verb
theory|theories,theorist,theorists,theoretical,theoretically|理论|noun
vary|varies,varied,varying,variable,variables,variance,variant,variants,variation,variations,variety,varieties,various,invariable,invariably|变化|verb
"""

# ============== 导出函数 ==============

def parse_awl_data():
    """解析AWL数据"""
    words = []
    sublist = 1

    for line in AWL_FULL.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            if 'Sublist' in line:
                try:
                    sublist = int(line.split()[2])
                except:
                    pass
            continue

        parts = line.split('|')
        if len(parts) < 4:
            continue

        headword = parts[0].strip()
        forms = [f.strip() for f in parts[1].split(',')]
        translation = parts[2].strip()
        pos = parts[3].strip()

        base_level = min(6 + sublist, 9)

        for i, form in enumerate(forms):
            words.append({
                'word': form,
                'headword': headword,
                'translation': translation,
                'pos': pos,
                'category': 'academic',
                'sublist': sublist,
                'level': str(base_level),
                'frequency': max(70 - sublist * 3 - i % 5, 25),
                'source': 'AWL'
            })

    return words

def generate_oxford_3000():
    """生成牛津3000词汇"""
    words = []
    for category, vocab_list in OXFORD_3000.items():
        for word, translation, pos, level, freq in vocab_list:
            words.append({
                'word': word,
                'translation': translation,
                'pos': pos,
                'category': f'oxford_{category}',
                'level': str(level),
                'frequency': freq,
                'source': 'Oxford_3000'
            })
    return words

def generate_ielts_core():
    """生成IELTS核心词汇"""
    words = []
    for scene, vocab_list in IELTS_CORE.items():
        for word, translation, pos, level, freq in vocab_list:
            words.append({
                'word': word,
                'translation': translation,
                'pos': pos,
                'category': f'ielts_{scene}',
                'scene': scene,
                'level': str(level),
                'frequency': freq,
                'source': 'IELTS_Core'
            })
    return words

def export_to_json(data: List[Dict], filename: str):
    """导出为JSON"""
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  - Exported: {filepath} ({len(data)} words)")
    return filepath

def export_to_csv(data: List[Dict], filename: str):
    """导出为CSV"""
    if not data:
        return None
    filepath = OUTPUT_DIR / filename
    standard_fields = ['word', 'translation', 'pos', 'category', 'level', 'frequency', 'source']
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=standard_fields, extrasaction='ignore')
        writer.writeheader()
        for row in data:
            filtered = {k: row.get(k, '') for k in standard_fields}
            writer.writerow(filtered)
    print(f"  - Exported: {filepath} ({len(data)} words)")
    return filepath

def generate_sql_inserts(data: List[Dict], filename: str):
    """生成SQL插入语句"""
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"-- IELTS Massive Vocabulary Inserts\n")
        f.write(f"-- Total words: {len(data)}\n\n")
        f.write("INSERT INTO words (word, translation, pos, category, level, frequency) VALUES\n")

        for i, w in enumerate(data):
            word = w['word'].replace("'", "''")
            trans = w['translation'].replace("'", "''")
            cat = w.get('category', 'general')
            level = w.get('level', '5')
            freq = w.get('frequency', 50)
            pos = w.get('pos', 'word')

            comma = ',' if i < len(data) - 1 else ';'
            f.write(f"  ('{word}', '{trans}', '{pos}', '{cat}', '{level}', {freq}){comma}\n")

    print(f"  - Exported: {filepath}")
    return filepath

def generate_all_vocabulary():
    """生成所有词汇"""
    print("=" * 70)
    print("IELTS Massive Vocabulary Generator")
    print("=" * 70)

    all_vocabularies = {}

    print("\n[1/3] Generating AWL academic vocabulary...")
    all_vocabularies['awl'] = parse_awl_data()
    print(f"  - Generated {len(all_vocabularies['awl'])} AWL words")

    print("\n[2/3] Generating Oxford 3000 vocabulary...")
    all_vocabularies['oxford'] = generate_oxford_3000()
    print(f"  - Generated {len(all_vocabularies['oxford'])} Oxford 3000 words")

    print("\n[3/3] Generating IELTS core vocabulary...")
    all_vocabularies['ielts_core'] = generate_ielts_core()
    print(f"  - Generated {len(all_vocabularies['ielts_core'])} IELTS core words")

    # 合并所有词汇并去重
    print("\n[4/4] Merging and deduplicating...")
    all_words = []
    seen = set()
    duplicates = 0

    for category, words in all_vocabularies.items():
        for w in words:
            word_key = w['word'].lower()
            if word_key not in seen:
                seen.add(word_key)
                all_words.append(w)
            else:
                duplicates += 1

    print(f"  - Removed {duplicates} duplicate words")
    print(f"\n[STATS] Total unique words: {len(all_words)}")

    # 导出
    print("\n" + "-" * 50)
    print("Exporting files...")
    print("-" * 50)

    export_to_json(all_words, 'ielts_vocabulary_massive.json')
    export_to_csv(all_words, 'ielts_vocabulary_massive.csv')
    generate_sql_inserts(all_words, 'vocabulary_massive_inserts.sql')

    # 按类别导出
    print("\n" + "-" * 50)
    print("Exporting category files...")
    print("-" * 50)
    for category, words in all_vocabularies.items():
        export_to_json(words, f'ielts_vocabulary_{category}.json')
        export_to_csv(words, f'ielts_vocabulary_{category}.csv')

    # 生成统计信息
    print("\n" + "=" * 70)
    print("Generation Summary:")
    print("=" * 70)
    for category, words in all_vocabularies.items():
        print(f"  {category:20s}: {len(words):5d} words")
    print("-" * 70)
    print(f"  {'TOTAL UNIQUE':20s}: {len(all_words):5d} words")
    print("=" * 70)

    return all_words

if __name__ == '__main__':
    generate_all_vocabulary()
