import { describe, expect, it } from 'vitest'
import { buildFavoriteWordsExportContent } from './adminFavoriteWordsExport'

const favoriteWords = [
  {
    word: 'compile',
    normalized_word: 'compile',
    phonetic: '/kəmˈpaɪl/',
    pos: 'v.',
    definition: 'to collect information',
    source_book_id: 'ielts_reading_premium',
    source_book_title: '雅思阅读精讲',
    source_chapter_id: '3',
    source_chapter_title: '第3章',
    created_at: '2026-04-07T08:00:00+00:00',
    updated_at: '2026-04-07T08:00:00+00:00',
  },
]

describe('buildFavoriteWordsExportContent', () => {
  it('builds csv content', () => {
    const content = buildFavoriteWordsExportContent(favoriteWords, 'csv')

    expect(content).toContain('word,phonetic,pos,definition,source_book,source_chapter,created_at')
    expect(content).toContain('compile,/kəmˈpaɪl/,v.,to collect information,雅思阅读精讲,第3章,2026-04-07T08:00:00+00:00')
  })

  it('builds txt content', () => {
    const content = buildFavoriteWordsExportContent(favoriteWords, 'txt')

    expect(content).toContain('单词: compile')
    expect(content).toContain('来源词书: 雅思阅读精讲')
    expect(content).toContain('收藏时间: 2026-04-07T08:00:00+00:00')
  })

  it('builds json content', () => {
    const content = buildFavoriteWordsExportContent(favoriteWords, 'json')

    expect(content).toContain('"normalized_word": "compile"')
    expect(content).toContain('"source_book_title": "雅思阅读精讲"')
  })
})
