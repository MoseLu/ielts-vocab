from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[2] / 'scripts'
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from premium_phonetic_audit_support import (  # noqa: E402
    SourceResult,
    audit_word,
    has_unsafe_marker,
    normalize_ipa_text,
    parse_cambridge_phonetics,
    parse_longman_phonetics,
    parse_oxford_phonetics,
    source_slug,
)


def test_normalize_ipa_preserves_optional_markers():
    assert normalize_ipa_text(' trænˈzækʃ(ə)n ') == '/trænˈzækʃ(ə)n/'
    assert has_unsafe_marker('/trænˈzækʃ(ə)n/') is True


def test_parse_oxford_phonetics_reads_phon_span():
    html = '<div class="phons_br"><span class="phon">/trænˈzækʃn/</span></div>'

    assert parse_oxford_phonetics(html) == ('/trænˈzækʃn/',)


def test_parse_oxford_phonetics_ignores_outer_phonetics_container():
    html = (
        '<span class="phonetics">'
        '<span class="phon">/trænˈzækʃn/</span>'
        '</span>'
    )

    assert parse_oxford_phonetics(html) == ('/trænˈzækʃn/',)


def test_parse_oxford_phonetics_ignores_verb_form_audio():
    html = (
        '<div class="webtop"><span class="phonetics">'
        '<div class="phons_br"><span class="phon">/beə(r)/</span></div>'
        '</span><div class="collapse">'
        '<div class="phons_br"><span class="phon">/bɔːn/</span></div>'
    )

    assert parse_oxford_phonetics(html) == ('/beə(r)/',)


def test_parse_cambridge_phonetics_keeps_nested_ipa_text():
    html = (
        '<span class="pron dpron">/'
        '<span class="ipa dipa">trænˈzæk.ʃ<span class="sp dsp">ə</span>n</span>'
        '/</span>'
    )

    assert parse_cambridge_phonetics(html) == ('/trænˈzæk.ʃən/',)


def test_parse_cambridge_phonetics_prefers_uk_region():
    html = (
        '<span class="uk dpron-i"><span class="pron dpron">/'
        '<span class="ipa dipa">brɪtɪʃ</span>/</span></span>'
        '<span class="us dpron-i"><span class="pron dpron">/'
        '<span class="ipa dipa">juːes</span>/</span></span>'
    )

    assert parse_cambridge_phonetics(html) == ('/brɪtɪʃ/',)


def test_parse_longman_phonetics_keeps_nested_optional_text():
    html = '<span class="PRON">trænˈzækʃ<span class="i">ə</span>n</span>'

    assert parse_longman_phonetics(html) == ('/trænˈzækʃən/',)


def test_parse_longman_phonetics_ignores_inflections():
    html = (
        '<span class="frequent Head"><span class="HWD">bear</span>'
        '<span class="PronCodes">/<span class="PRON">beə</span>/</span>'
        '<span class="POS"> verb</span>'
        '<span class="Inflections"><span class="PRON">bɔːn</span></span>'
        '</span>'
    )

    assert parse_longman_phonetics(html) == ('/beə/',)


def test_audit_word_marks_safe_consensus_auto_fixable():
    record = audit_word(
        'transaction',
        '/trænˈzækʃ(ə)n/',
        [
            SourceResult('oxford', ('/trænˈzækʃn/',), True),
            SourceResult('wiktionary', ('/trænˈzækʃn/',), True),
        ],
    )

    assert record.status == 'confirmed'
    assert record.consensus_phonetic == '/trænˈzækʃn/'
    assert record.auto_fixable is True
    assert record.confidence == 2


def test_audit_word_accepts_two_of_three_source_vote():
    record = audit_word(
        'abuse',
        '/əˈbjuːz/',
        [
            SourceResult('oxford', ('/əˈbjuːs/',), True),
            SourceResult('cambridge', ('/əˈbjuːs/',), True),
            SourceResult('longman', ('/əˈbjuːz/',), True),
        ],
    )

    assert record.status == 'confirmed'
    assert record.consensus_phonetic == '/əˈbjuːs/'
    assert record.auto_fixable is True
    assert record.confidence == 2
    assert record.voters == ['cambridge', 'oxford']


def test_audit_word_rejects_tied_source_votes():
    record = audit_word(
        'foot',
        '/fʊt/',
        [
            SourceResult('oxford', ('/fʊt/', '/fiːt/'), True),
            SourceResult('cambridge', ('/fʊt/', '/fiːt/'), True),
            SourceResult('longman', (), False),
        ],
    )

    assert record.status == 'conflict'
    assert record.auto_fixable is False
    assert record.confidence == 2


def test_audit_word_does_not_auto_fix_optional_consensus():
    record = audit_word(
        'transaction',
        '/trænˈzækʃən/',
        [
            SourceResult('cambridge', ('/trænˈzækʃ(ə)n/',), True),
            SourceResult('longman', ('/trænˈzækʃ(ə)n/',), True),
        ],
    )

    assert record.status == 'unsafe_optional'
    assert record.auto_fixable is False


def test_audit_word_marks_conflicting_sources():
    record = audit_word(
        'revolutionary',
        '/ˌrevəˈluːʃənəri/',
        [
            SourceResult('oxford', ('/ˌrevəˈluːʃənəri/',), True),
            SourceResult('cambridge', ('/ˌrevəˈluːʃənri/',), True),
        ],
    )

    assert record.status == 'conflict'
    assert record.auto_fixable is False


def test_source_slug_keeps_phrase_as_phrase_slug():
    assert source_slug('The rest of') == 'the-rest-of'
