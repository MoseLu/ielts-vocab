import { describe, expect, it } from 'vitest'
import { WordDetailResponseSchema, type WordDetailResponse, type WordSearchResult } from '../../../lib'
import { buildMemoryRelatedCandidates, buildWordMemoryNote } from './globalWordMemoryNote'

function buildResult(overrides: Partial<WordSearchResult> = {}): WordSearchResult {
  return {
    word: 'park',
    phonetic: '/pɑːk/',
    pos: 'n.',
    definition: '公园；园区',
    book_id: 'book-a',
    book_title: 'Book A',
    match_type: 'exact',
    ...overrides,
  }
}

function buildDetail(overrides: Partial<WordDetailResponse> = {}): WordDetailResponse {
  return {
    word: 'responsibility',
    phonetic: '/rɪˌspɒnsəˈbɪləti/',
    pos: 'n.',
    definition: '责任；职责',
    root: {
      word: 'responsibility',
      normalized_word: 'responsibility',
      segments: [{ kind: '词根', text: 'spons', meaning: '承诺、担保' }],
      summary: '把 spons 看成“承诺”的抓手。',
    },
    english: {
      word: 'responsibility',
      normalized_word: 'responsibility',
      entries: [],
    },
    examples: [],
    derivatives: [],
    note: {
      word: 'responsibility',
      content: '',
    },
    ...overrides,
  }
}

describe('buildWordMemoryNote', () => {
  it('builds a homophone cue for short familiar words', () => {
    const note = buildWordMemoryNote({
      detailData: null,
      result: buildResult(),
    })

    expect(note.badge).toBe('谐音')
    expect(note.text).toContain('帕克')
    expect(note.text).toContain('公园')
  })

  it('falls back to association cues for longer words', () => {
    const note = buildWordMemoryNote({
      detailData: buildDetail(),
      result: buildResult({
        word: 'responsibility',
        phonetic: '/rɪˌspɒnsəˈbɪləti/',
        definition: '责任；职责',
      }),
    })

    expect(note.badge).toBe('联想')
    expect(note.text).toContain('spons')
    expect(note.text).toContain('责任')
  })

  it('mentions nearby confusable words when available', () => {
    const note = buildWordMemoryNote({
      detailData: null,
      result: buildResult({
        word: 'system',
        phonetic: '/ˈsɪstəm/',
        definition: '系统；体系',
        listening_confusables: [{
          word: 'symptom',
          phonetic: '/ˈsɪmptəm/',
          pos: 'n.',
          definition: '症状',
        }],
      }),
    })

    expect(note.badge).toBe('谐音')
    expect(note.text).toContain('西斯特姆')
    expect(note.text).toContain('symptom')
  })

  it('prefers server-provided memory notes when available', () => {
    const note = buildWordMemoryNote({
      detailData: buildDetail({
        memory: {
          badge: '联想',
          text: '先想象自己把责任扛在肩上，再把“责任；职责”这个意思挂上去。',
          source: 'llm_memory',
          updated_at: '2026-04-21T12:00:00Z',
        },
      }),
      result: buildResult({
        word: 'responsibility',
        phonetic: '/rɪˌspɒnsəˈbɪləti/',
        definition: '责任；职责',
      }),
    })

    expect(note.badge).toBe('联想')
    expect(note.text).toBe('先想象自己把责任扛在肩上，再把“责任；职责”这个意思挂上去。')
  })

  it('accepts newer server-provided memory badges', () => {
    const response = buildDetail({
      memory: {
        badge: '词根词缀',
        text: '先抓 spons 这个“承诺”线索，再落到“责任；职责”。',
        source: 'premium_word_mnemonics',
      },
    })
    const parsed = WordDetailResponseSchema.parse(response)
    const note = buildWordMemoryNote({
      detailData: parsed,
      result: buildResult({ word: 'responsibility', definition: '责任；职责' }),
    })

    expect(note.badge).toBe('词根词缀')
    expect(note.text).toContain('责任')
  })

  it('filters unrelated listening distractors from memory related words', () => {
    const candidates = buildMemoryRelatedCandidates(buildResult({
      word: 'racism',
      definition: '种族主义；种族歧视',
      listening_confusables: [
        { word: 'races', phonetic: '/ˈreɪsɪz/', pos: 'n.', definition: '比赛' },
        { word: 'racial', phonetic: '/ˈreɪʃ(ə)l/', pos: 'adj.', definition: '种族的' },
        { word: 'recipes', phonetic: '/ˈresəpiz/', pos: 'n.', definition: '食谱；配方' },
        { word: 'rack', phonetic: '/ræk/', pos: 'n.', definition: '行李架' },
        { word: 'race', phonetic: '/reɪs/', pos: 'n.', definition: '赛跑；竞争；种族' },
      ],
    }))

    expect(candidates.map(candidate => candidate.word)).toEqual(['races', 'racial', 'race'])
  })
})
