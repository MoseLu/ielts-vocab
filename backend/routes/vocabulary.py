from flask import Blueprint, jsonify

vocabulary_bp = Blueprint('vocabulary', __name__)

# Vocabulary data - same as frontend
WORD_LIST = [
    {'word': 'abandon', 'phonetic': '/əˈbændən/', 'pos': 'v.', 'definition': '放弃；遗弃'},
    {'word': 'ability', 'phonetic': '/əˈbɪləti/', 'pos': 'n.', 'definition': '能力'},
    {'word': 'able', 'phonetic': '/ˈeɪbl/', 'pos': 'adj.', 'definition': '能够的；有能力的'},
    {'word': 'about', 'phonetic': '/əˈbaʊt/', 'pos': 'prep.', 'definition': '关于；大约'},
    {'word': 'above', 'phonetic': '/əˈbʌv/', 'pos': 'prep.', 'definition': '在...上面'},
    {'word': 'abroad', 'phonetic': '/əˈbrɔːd/', 'pos': 'adv.', 'definition': '在国外'},
    {'word': 'absence', 'phonetic': '/ˈæbsəns/', 'pos': 'n.', 'definition': '缺席；不在'},
    {'word': 'absolute', 'phonetic': '/ˈæbsəluːt/', 'pos': 'adj.', 'definition': '绝对的'},
    {'word': 'absorb', 'phonetic': '/əbˈzɔːrb/', 'pos': 'v.', 'definition': '吸收；理解'},
    {'word': 'abstract', 'phonetic': '/ˈæbstrækt/', 'pos': 'adj.', 'definition': '抽象的'},
    {'word': 'abundant', 'phonetic': '/əˈbʌndənt/', 'pos': 'adj.', 'definition': '丰富的'},
    {'word': 'academic', 'phonetic': '/ˌækəˈdemɪk/', 'pos': 'adj.', 'definition': '学术的'},
    {'word': 'accept', 'phonetic': '/əkˈsept/', 'pos': 'v.', 'definition': '接受；承认'},
    {'word': 'access', 'phonetic': '/ˈækses/', 'pos': 'n.', 'definition': '进入；访问'},
    {'word': 'accident', 'phonetic': '/ˈæksɪdənt/', 'pos': 'n.', 'definition': '事故'},
    {'word': 'accommodation', 'phonetic': '/əˌkɒməˈdeɪʃn/', 'pos': 'n.', 'definition': '住宿'},
    {'word': 'accompany', 'phonetic': '/əˈkʌmpəni/', 'pos': 'v.', 'definition': '陪伴'},
    {'word': 'accomplish', 'phonetic': '/əˈkʌmplɪʃ/', 'pos': 'v.', 'definition': '完成'},
    {'word': 'account', 'phonetic': '/əˈkaʊnt/', 'pos': 'n.', 'definition': '账户'},
    {'word': 'accurate', 'phonetic': '/ˈækjərət/', 'pos': 'adj.', 'definition': '准确的'},
    {'word': 'achieve', 'phonetic': '/əˈtʃiːv/', 'pos': 'v.', 'definition': '达到；完成'},
    {'word': 'acknowledge', 'phonetic': '/əkˈnɒlɪdʒ/', 'pos': 'v.', 'definition': '承认；认可'},
    {'word': 'acquire', 'phonetic': '/əˈkwaɪər/', 'pos': 'v.', 'definition': '获得；学到'},
    {'word': 'across', 'phonetic': '/əˈkrɒs/', 'pos': 'prep.', 'definition': '穿过'},
    {'word': 'active', 'phonetic': '/ˈæktɪv/', 'pos': 'adj.', 'definition': '积极的；活跃的'},
    {'word': 'activity', 'phonetic': '/ækˈtɪvəti/', 'pos': 'n.', 'definition': '活动'},
    {'word': 'actual', 'phonetic': '/ˈæktʃuəl/', 'pos': 'adj.', 'definition': '实际的'},
    {'word': 'adapt', 'phonetic': '/əˈdæpt/', 'pos': 'v.', 'definition': '适应；改编'},
    {'word': 'add', 'phonetic': '/æd/', 'pos': 'v.', 'definition': '添加'},
    {'word': 'address', 'phonetic': '/əˈdres/', 'pos': 'n.', 'definition': '地址'},
    {'word': 'adequate', 'phonetic': '/ˈædikwət/', 'pos': 'adj.', 'definition': '足够的'},
    {'word': 'adjust', 'phonetic': '/əˈdʒʌst/', 'pos': 'v.', 'definition': '调整；适应'},
    {'word': 'administration', 'phonetic': '/ədˌmɪnɪˈstreɪʃn/', 'pos': 'n.', 'definition': '管理；行政'},
    {'word': 'admire', 'phonetic': '/ədˈmaɪər/', 'pos': 'v.', 'definition': '钦佩；欣赏'},
    {'word': 'admit', 'phonetic': '/ədˈmɪt/', 'pos': 'v.', 'definition': '承认；允许进入'},
    {'word': 'adopt', 'phonetic': '/əˈdɒpt/', 'pos': 'v.', 'definition': '采用；收养'},
    {'word': 'adult', 'phonetic': '/ˈædʌlt/', 'pos': 'n.', 'definition': '成年人'},
    {'word': 'advance', 'phonetic': '/ədˈvæns/', 'pos': 'v.', 'definition': '前进；进步'},
    {'word': 'advantage', 'phonetic': '/ədˈvæntɪdʒ/', 'pos': 'n.', 'definition': '优势；好处'},
    {'word': 'adventure', 'phonetic': '/ədˈventʃər/', 'pos': 'n.', 'definition': '冒险'},
    {'word': 'advertise', 'phonetic': '/ˈædvərtaɪz/', 'pos': 'v.', 'definition': '做广告'},
    {'word': 'advice', 'phonetic': '/ədˈvaɪs/', 'pos': 'n.', 'definition': '建议；劝告'},
    {'word': 'advise', 'phonetic': '/ədˈvaɪz/', 'pos': 'v.', 'definition': '建议；劝告'},
    {'word': 'affair', 'phonetic': '/əˈfer/', 'pos': 'n.', 'definition': '事件；事务'},
    {'word': 'affect', 'phonetic': '/əˈfekt/', 'pos': 'v.', 'definition': '影响'},
    {'word': 'afford', 'phonetic': '/əˈfɔːrd/', 'pos': 'v.', 'definition': '负担得起'},
    {'word': 'afraid', 'phonetic': '/əˈfreɪd/', 'pos': 'adj.', 'definition': '害怕的'},
    {'word': 'after', 'phonetic': '/ˈæftər/', 'pos': 'prep.', 'definition': '在...之后'},
    {'word': 'afternoon', 'phonetic': '/ˌæftərˈnuːn/', 'pos': 'n.', 'definition': '下午'},
    {'word': 'again', 'phonetic': '/əˈɡen/', 'pos': 'adv.', 'definition': '再；又'},
    {'word': 'against', 'phonetic': '/əˈɡenst/', 'pos': 'prep.', 'definition': '反对；靠着'},
    {'word': 'age', 'phonetic': '/eɪdʒ/', 'pos': 'n.', 'definition': '年龄'},
    {'word': 'agency', 'phonetic': '/ˈeɪdʒənsi/', 'pos': 'n.', 'definition': '代理；机构'},
    {'word': 'agent', 'phonetic': '/ˈeɪdʒənt/', 'pos': 'n.', 'definition': '代理人；经纪人'},
    {'word': 'agree', 'phonetic': '/əˈɡriː/', 'pos': 'v.', 'definition': '同意'},
    {'word': 'agreement', 'phonetic': '/əˈɡriːmənt/', 'pos': 'n.', 'definition': '协议；同意'},
    {'word': 'ahead', 'phonetic': '/əˈhed/', 'pos': 'adv.', 'definition': '在前；向前'},
    {'word': 'aid', 'phonetic': '/eɪd/', 'pos': 'n.', 'definition': '帮助；援助'},
    {'word': 'aim', 'phonetic': '/eɪm/', 'pos': 'v.', 'definition': '瞄准；旨在'},
    {'word': 'air', 'phonetic': '/er/', 'pos': 'n.', 'definition': '空气；天空'},
    {'word': 'aircraft', 'phonetic': '/ˈerkræft/', 'pos': 'n.', 'definition': '飞机'},
    {'word': 'airline', 'phonetic': '/ˈerlaɪn/', 'pos': 'n.', 'definition': '航空公司'},
    {'word': 'airport', 'phonetic': '/ˈerpɔːrt/', 'pos': 'n.', 'definition': '机场'},
    {'word': 'alarm', 'phonetic': '/əˈlɑːrm/', 'pos': 'n.', 'definition': '警报；惊恐'},
    {'word': 'album', 'phonetic': '/ˈælbəm/', 'pos': 'n.', 'definition': '专辑；相册'},
    {'word': 'alcohol', 'phonetic': '/ˈælkəhɔːl/', 'pos': 'n.', 'definition': '酒精'},
    {'word': 'alike', 'phonetic': '/əˈlaɪk/', 'pos': 'adj.', 'definition': '相似的'},
    {'word': 'alive', 'phonetic': '/əˈlaɪv/', 'pos': 'adj.', 'definition': '活着的'},
    {'word': 'allow', 'phonetic': '/əˈlaʊ/', 'pos': 'v.', 'definition': '允许'},
    {'word': 'almost', 'phonetic': '/ˈɔːlmoʊst/', 'pos': 'adv.', 'definition': '几乎'},
    {'word': 'alone', 'phonetic': '/əˈloʊn/', 'pos': 'adj.', 'definition': '单独的'},
    {'word': 'along', 'phonetic': '/əˈlɔːŋ/', 'pos': 'prep.', 'definition': '沿着'},
    {'word': 'already', 'phonetic': '/ɔːlˈredi/', 'pos': 'adv.', 'definition': '已经'},
    {'word': 'also', 'phonetic': '/ˈɔːlsoʊ/', 'pos': 'adv.', 'definition': '也'},
    {'word': 'alter', 'phonetic': '/ˈɔːltər/', 'pos': 'v.', 'definition': '改变'},
    {'word': 'alternative', 'phonetic': '/ɔːlˈtɜːrnətɪv/', 'pos': 'adj.', 'definition': '替代的'},
    {'word': 'although', 'phonetic': '/ɔːlˈðoʊ/', 'pos': 'conj.', 'definition': '虽然'},
    {'word': 'always', 'phonetic': '/ˈɔːlweɪz/', 'pos': 'adv.', 'definition': '总是'},
    {'word': 'amaze', 'phonetic': '/əˈmeɪz/', 'pos': 'v.', 'definition': '使惊奇'},
    {'word': 'ambition', 'phonetic': '/æmˈbɪʃn/', 'pos': 'n.', 'definition': '雄心；抱负'},
    {'word': 'ambulance', 'phonetic': '/ˈæmbjələns/', 'pos': 'n.', 'definition': '救护车'},
    {'word': 'among', 'phonetic': '/əˈmʌŋ/', 'pos': 'prep.', 'definition': '在...之中'},
    {'word': 'amount', 'phonetic': '/əˈmaʊnt/', 'pos': 'n.', 'definition': '数量'},
    {'word': 'amuse', 'phonetic': '/əˈmjuːz/', 'pos': 'v.', 'definition': '使愉快'},
    {'word': 'analyze', 'phonetic': '/ˈænəlaɪz/', 'pos': 'v.', 'definition': '分析'},
    {'word': 'ancient', 'phonetic': '/ˈeɪnʃənt/', 'pos': 'adj.', 'definition': '古代的'},
    {'word': 'and', 'phonetic': '/ænd/', 'pos': 'conj.', 'definition': '和'},
    {'word': 'anger', 'phonetic': '/ˈæŋɡər/', 'pos': 'n.', 'definition': '愤怒'},
    {'word': 'angle', 'phonetic': '/ˈæŋɡl/', 'pos': 'n.', 'definition': '角度'},
    {'word': 'angry', 'phonetic': '/ˈæŋɡri/', 'pos': 'adj.', 'definition': '生气的'},
    {'word': 'animal', 'phonetic': '/ˈænɪml/', 'pos': 'n.', 'definition': '动物'},
    {'word': 'announce', 'phonetic': '/əˈnaʊns/', 'pos': 'v.', 'definition': '宣布'},
    {'word': 'annoy', 'phonetic': '/əˈnɔɪ/', 'pos': 'v.', 'definition': '使烦恼'},
    {'word': 'annual', 'phonetic': '/ˈænjuəl/', 'pos': 'adj.', 'definition': '每年的'},
    {'word': 'another', 'phonetic': '/əˈnʌðər/', 'pos': 'adj.', 'definition': '另一个'},
    {'word': 'answer', 'phonetic': '/ˈænsər/', 'pos': 'v.', 'definition': '回答'},
    {'word': 'anticipate', 'phonetic': '/ænˈtɪsɪpeɪt/', 'pos': 'v.', 'definition': '预期'},
    {'word': 'anxiety', 'phonetic': '/æŋˈzaɪəti/', 'pos': 'n.', 'definition': '焦虑'},
    {'word': 'anxious', 'phonetic': '/ˈæŋkʃəs/', 'pos': 'adj.', 'definition': '焦虑的'},
    {'word': 'any', 'phonetic': '/ˈeni/', 'pos': 'adj.', 'definition': '任何'},
    {'word': 'anybody', 'phonetic': '/ˈenibɒdi/', 'pos': 'pron.', 'definition': '任何人'}
]


def generate_vocabulary():
    """Generate 30 days of vocabulary"""
    words = []
    for day in range(1, 31):
        start_idx = (day - 1) * 100
        for i in range(100):
            idx = (start_idx + i) % len(WORD_LIST)
            words.append({
                'id': start_idx + i + 1,
                'day': day,
                **WORD_LIST[idx]
            })
    return words


# Pre-generate vocabulary
VOCABULARY_DATA = generate_vocabulary()


@vocabulary_bp.route('', methods=['GET'])
def get_vocabulary():
    """Get all vocabulary"""
    return jsonify({'vocabulary': VOCABULARY_DATA}), 200


@vocabulary_bp.route('/day/<int:day>', methods=['GET'])
def get_day_vocabulary(day):
    """Get vocabulary for a specific day"""
    if day < 1 or day > 30:
        return jsonify({'error': 'Day must be between 1 and 30'}), 400

    day_vocabulary = [w for w in VOCABULARY_DATA if w['day'] == day]
    return jsonify({'vocabulary': day_vocabulary}), 200
