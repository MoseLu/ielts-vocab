import json

import pytest

import services.books_catalog_service as books_catalog_service
import services.word_memory_note_file_generation as word_memory_note_file_generation
import services.word_memory_note_enrichment as word_memory_note_enrichment
from models import WordCatalogEntry


def _seed_catalog():
    return [
        {
            'word': 'stout',
            'phonetic': '/staʊt/',
            'pos': 'adj.',
            'definition': '粗壮的；结实的',
            'examples': [{'en': 'The old oak tree remained stout in the storm.', 'zh': '老橡树在风暴里依旧粗壮坚挺。'}],
            'book_id': 'ielts_reading_premium',
            'book_title': 'Reading Premium',
        },
        {
            'word': 'a bit',
            'phonetic': '/ə bɪt/',
            'pos': 'adv.',
            'definition': '稍微；有点',
            'examples': [{'en': 'I am a bit tired after the lecture.', 'zh': '讲座结束后我有点累。'}],
            'book_id': 'ielts_listening_premium',
            'book_title': 'Listening Premium',
        },
    ]


def test_collect_memory_word_seeds_reads_catalog_entries(monkeypatch):
    class _FakeRecord:
        def __init__(self, word, book_refs, definition='定义'):
            self.word = word
            self.normalized_word = word.lower()
            self.phonetic = '/test/'
            self.pos = 'n.'
            self.definition = definition
            self._book_refs = book_refs

        def get_examples(self):
            return [{'en': f'{self.word} example', 'zh': '例句'}]

        def get_book_refs(self):
            return list(self._book_refs)

    monkeypatch.setattr(
        word_memory_note_enrichment.word_catalog_repository,
        'list_all_word_catalog_entries',
        lambda: [
            _FakeRecord('zeta', [{'book_id': 'ielts_reading_premium'}]),
            _FakeRecord('alpha', [{'book_id': 'ielts_listening_premium'}]),
            _FakeRecord('other', [{'book_id': 'ielts_comprehensive'}]),
        ],
    )
    monkeypatch.setattr(word_memory_note_enrichment, 'collect_word_seeds', lambda _book_ids: [])

    seeds = word_memory_note_enrichment.collect_memory_word_seeds()

    assert [seed['normalized_word'] for seed in seeds] == ['alpha', 'zeta']
    assert seeds[0]['book_ids'] == ['ielts_listening_premium']
    assert seeds[1]['book_ids'] == ['ielts_reading_premium']


def test_collect_memory_word_seeds_keeps_vocab_union_when_catalog_is_partial(monkeypatch):
    class _FakeRecord:
        word = 'Alpha'
        normalized_word = 'alpha'
        phonetic = '/record/'
        pos = 'n.'
        definition = '记录定义'

        def get_examples(self):
            return [{'en': 'Record example.', 'zh': '记录例句'}]

        def get_book_refs(self):
            return [{'book_id': 'ielts_reading_premium'}]

    monkeypatch.setattr(
        word_memory_note_enrichment,
        'collect_word_seeds',
        lambda _book_ids: [
            {
                'word': 'alpha',
                'display_word': 'alpha',
                'normalized_word': 'alpha',
                'phonetic': '/seed/',
                'pos': 'n.',
                'definition': '原始定义',
                'definitions': ['原始定义'],
                'examples': [{'en': 'Seed example.', 'zh': '原始例句'}],
                'book_refs': [{'book_id': 'ielts_reading_premium'}],
                'book_ids': ['ielts_reading_premium'],
            },
            {
                'word': 'beta',
                'display_word': 'beta',
                'normalized_word': 'beta',
                'phonetic': '/beta/',
                'pos': 'n.',
                'definition': '第二个定义',
                'definitions': ['第二个定义'],
                'examples': [],
                'book_refs': [{'book_id': 'ielts_listening_premium'}],
                'book_ids': ['ielts_listening_premium'],
            },
        ],
    )
    monkeypatch.setattr(
        word_memory_note_enrichment.word_catalog_repository,
        'list_all_word_catalog_entries',
        lambda: [_FakeRecord()],
    )

    seeds = word_memory_note_enrichment.collect_memory_word_seeds()

    assert [seed['normalized_word'] for seed in seeds] == ['alpha', 'beta']
    assert seeds[0]['definition'] == '记录定义'
    assert seeds[0]['book_ids'] == ['ielts_reading_premium']
    assert seeds[1]['definition'] == '第二个定义'


def test_memory_note_enrichment_persists_server_notes(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', lambda *_args, **_kwargs: {
        'stout': {
            'word': 'stout',
            'badge': '词根词缀',
            'text': '先想一个人站得又稳又壮，再把“粗壮的；结实的”这个意思挂上去。',
        },
        'a bit': {
            'word': 'a bit',
            'badge': '联想',
            'text': '想象老师说再等一小会儿，就是“稍微；有点”这么一点点。',
        },
    })

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            batch_size=2,
            overwrite=True,
            sleep_seconds=0,
        )

        assert stats['enriched'] == 2
        assert stats['failed'] == 0

        stout = WordCatalogEntry.query.filter_by(normalized_word='stout').first()
        phrase = WordCatalogEntry.query.filter_by(normalized_word='a bit').first()
        assert stout.get_memory_note()['source'] == 'llm_memory'
        assert stout.get_memory_note()['badge'] == '词根词缀'
        assert '粗壮的' in stout.get_memory_note()['text']
        assert '稍微' in phrase.get_memory_note()['text']


def test_memory_note_file_generation_writes_json_items(app, monkeypatch, tmp_path):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', lambda *_args, **_kwargs: {
        'stout': {
            'word': 'stout',
            'badge': '词根词缀',
            'text': '先想一个人站得又稳又壮，再把“粗壮的；结实的”这个意思挂上去。',
        },
        'a bit': {
            'word': 'a bit',
            'badge': '扩展',
            'text': '想象老师说再等一小会儿，就是“稍微；有点”这么一点点。',
        },
    })
    output_path = tmp_path / 'premium_word_mnemonics.json'

    with app.app_context():
        stats = word_memory_note_file_generation.enrich_premium_book_memory_note_file(
            output_path=output_path,
            batch_size=2,
            overwrite=True,
            sleep_seconds=0,
        )

    payload = json.loads(output_path.read_text(encoding='utf-8'))
    assert stats['enriched'] == 2
    assert stats['coverage']['missing_words'] == []
    assert payload['items']['stout']['badge'] == '词根词缀'
    assert payload['items']['a bit']['book_ids'] == ['ielts_listening_premium']


def test_memory_note_enrichment_rejects_formulaic_phrase_output(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', lambda *_args, **_kwargs: {
        'a bit': {
            'word': 'a bit',
            'badge': '联想',
            'text': 'a + bit',
        },
    })

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            words=['a bit'],
            batch_size=1,
            overwrite=True,
            sleep_seconds=0,
        )

        assert stats['enriched'] == 0
        assert stats['failed'] == 1
        assert stats['failed_words'] == ['a bit']

        phrase = WordCatalogEntry.query.filter_by(normalized_word='a bit').first()
        assert phrase is None or phrase.get_memory_note() is None


def test_memory_note_enrichment_rejects_missing_definition_anchor(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', lambda *_args, **_kwargs: {
        'stout': {
            'word': 'stout',
            'badge': '联想',
            'text': '想象一个人站得特别稳，整个人看起来很有力量。',
        },
    })

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            words=['stout'],
            batch_size=1,
            overwrite=True,
            sleep_seconds=0,
        )

        assert stats['enriched'] == 0
        assert stats['failed'] == 1
        assert stats['failed_words'] == ['stout']


def test_memory_note_enrichment_rejects_illogical_word_chain_story():
    seed = {
        'display_word': 'universe',
        'normalized_word': 'universe',
        'definitions': ['宇宙'],
        'is_phrase': False,
    }

    with pytest.raises(ValueError, match='formulaic'):
        word_memory_note_enrichment._sanitize_memory_note_payload(seed, {
            'word': 'universe',
            'badge': '串记',
            'text': '未来去宇宙（universe）上大学（university）是普遍的（universal）',
        })


def test_definition_anchor_accepts_core_phrase_meaning():
    assert word_memory_note_enrichment._has_definition_anchor(
        '想到考试方法调整会带来很大的差异。',
        ['短语. 明显的差异；很大的不同'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '老师说还要再等几个学生。',
        ['再几个的；多几个的（用于可数名词，表示数量不多但额外的一些）'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '像把线拉直对齐，使想法与经理一致。',
        ['使一致；使一致（align 的过去式和过去分词）'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '人类学家是研究人类社会的学者。',
        ['[人类] 人类学家；sub'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '猿类与人类有许多共同特征。',
        ['猿（ape 的复数形式）'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '数字直冲20%的峰值，表示高达。',
        ['短语，表示“高达；和……一样高”，用于比较或强调数量、程度或高度'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '坐在考场里评估学生的进步。',
        ['对……进行评估（assess 过去时形式）'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '下午茶配饼干，别饿死。',
        ['<英>饼干；<英>饼干( biscuit的名词复数 )'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        'bottles（瓶子）排排坐，回收玻璃瓶。',
        ['瓶子'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '让免疫系统逐步增强。',
        ['phrase. 建立；逐步增长；加强'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '表示“通过使用”某物达成目的。',
        ['+；v.ing 通过使用'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '描述某事物具有某种特征。',
        ['描述…的特征；使具有…特征'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '俱乐部专用的会议室。',
        ['俱乐部会议室'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '小公司与大公司在赛道上激烈竞争。',
        ['phrase. 与…竞争'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '对某事作出最终决定。',
        ['phrase. 对…作出决定'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '工作日期间很忙。',
        ['phrase. 工作日内'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '寄到电子邮箱地址的场景。',
        ['phrase. 电子邮件地址'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '向外送出烟雾或热量。',
        ['发出；放出；发出，放出( emit的现在分词 )'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '时间充裕，足够完成所有任务。',
        ['足够的 时间'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '适应环境或融入群体。',
        ['phrase. 相适应；相融合'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '加油站里汽油味浓烈。',
        ['汽油【美】'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '从某种意义上说。',
        ['英义；派生；笔记'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '进入现场说的人就是口译员。',
        ['作口译的人'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '问题就是冒出来的麻烦事。',
        ['事件'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '想象考试有点难。',
        ['phrase. 有点儿'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '酒店每天提供的三餐。',
        ['一餐；一顿饭；“meal”的复数'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '指投影文件，老师用它展示笔记。',
        ['phrase. 投影的文件名'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '读关于某事的内容。',
        ['phr. 阅读关于……的内容；通过阅读了解到'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '射手扣动扳机，箭矢疾射而出。',
        ['射击；拍摄（电影）；疾驰；n. 照片；射门'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '把优点装进箱子展示出来。',
        ['展示优点的场合（或机会）；展示…的优点'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '社会与经济双轮驱动。',
        ['社会的与经济的'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '指做某事的时间安排或时机选择。',
        ['时间的安排；时间的选择'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '跨越形状变成新样。',
        ['transform的变形'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '科技改变生活。',
        ['transform的变形'],
    )
    assert word_memory_note_enrichment._has_definition_anchor(
        '将军统领所有种类的士兵。',
        ['一般的；普遍的；总的；大致的；首席的；n. 将军'],
    )


def test_formula_check_allows_cjk_phrase_scene_with_operator():
    assert not word_memory_note_enrichment._looks_like_formula_text(
        'all 所有 + around 周围，所有人都在周围，即“四处”或“周围”。',
        is_phrase=True,
    )


def test_memory_note_enrichment_emits_progress_updates(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', lambda *_args, **_kwargs: {
        'stout': {
            'word': 'stout',
            'badge': '联想',
            'text': '先想一个人站得又稳又壮，再把“粗壮的；结实的”这个意思挂上去。',
        },
        'a bit': {
            'word': 'a bit',
            'badge': '联想',
            'text': '想象老师说再等一小会儿，就是“稍微；有点”这么一点点。',
        },
    })
    snapshots = []

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            batch_size=1,
            overwrite=True,
            sleep_seconds=0,
            progress_callback=lambda current: snapshots.append(current),
        )

        assert stats['enriched'] == 2
        assert snapshots
        assert snapshots[-1]['enriched'] == 2
        assert snapshots[-1]['completed_batches'] == snapshots[-1]['total_batches'] == 2


def test_memory_note_enrichment_retries_rate_limit_until_success(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    sleeps = []
    attempts = {'count': 0}

    def fake_request(*_args, **_kwargs):
        attempts['count'] += 1
        if attempts['count'] == 1:
            raise RuntimeError('minimax-primary http 429: usage limit exceeded (2056)')
        return {
            'stout': {
                'word': 'stout',
                'badge': '联想',
                'text': '先想一个人站得又稳又壮，再把“粗壮的；结实的”这个意思挂上去。',
            },
        }

    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', fake_request)
    monkeypatch.setattr(word_memory_note_enrichment.time, 'sleep', lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(word_memory_note_enrichment.random, 'uniform', lambda *_args: 0.0)

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            words=['stout'],
            batch_size=1,
            overwrite=True,
            sleep_seconds=0,
            rate_limit_base_sleep_seconds=3,
            rate_limit_max_sleep_seconds=30,
        )

        assert attempts['count'] == 2
        assert stats['enriched'] == 1
        assert stats['failed'] == 0
        assert stats['rate_limit_retries'] == 1
        assert stats['rate_limit_wait_seconds'] == 3
        assert sleeps == [3]


def test_memory_note_enrichment_stops_on_real_quota_exhaustion(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(
        word_memory_note_enrichment,
        'request_memory_note_batch',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError('your current token plan not support model, MiniMax-M2.7 (2061)'),
        ),
    )

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            words=['stout'],
            batch_size=1,
            overwrite=True,
            sleep_seconds=0,
        )

        assert stats['quota_exhausted'] is True
        assert 'token plan not support model' in stats['stop_reason']
        assert stats['failed'] == 1
        assert stats['enriched'] == 0
