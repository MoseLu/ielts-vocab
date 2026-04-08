import type { UserDetail } from './AdminDashboard.types'

export type FavoriteWordRecord = UserDetail['favorite_words'][number]
export type FavoriteWordExportFormat = 'csv' | 'txt' | 'json'

function sanitizeFilenameSegment(value: string) {
  return value.trim().replace(/[\\/:*?"<>|]+/g, '-').replace(/\s+/g, '-').slice(0, 40) || 'user'
}

function escapeCsvValue(value: string) {
  if (!/[",\n]/.test(value)) return value
  return `"${value.replace(/"/g, '""')}"`
}

function stringifyValue(value: string | null | undefined) {
  return String(value ?? '').trim()
}

function resolveSourceBook(word: FavoriteWordRecord) {
  return stringifyValue(word.source_book_title) || stringifyValue(word.source_book_id)
}

function resolveSourceChapter(word: FavoriteWordRecord) {
  return stringifyValue(word.source_chapter_title) || stringifyValue(word.source_chapter_id)
}

export function buildFavoriteWordsExportContent(words: FavoriteWordRecord[], format: FavoriteWordExportFormat) {
  if (format === 'json') {
    return JSON.stringify(words, null, 2)
  }

  if (format === 'txt') {
    return words.map(word => [
      `单词: ${word.word}`,
      `音标: ${stringifyValue(word.phonetic) || '—'}`,
      `词性: ${stringifyValue(word.pos) || '—'}`,
      `释义: ${stringifyValue(word.definition) || '—'}`,
      `来源词书: ${resolveSourceBook(word) || '—'}`,
      `来源章节: ${resolveSourceChapter(word) || '—'}`,
      `收藏时间: ${stringifyValue(word.created_at) || stringifyValue(word.updated_at) || '—'}`,
    ].join('\n')).join('\n\n')
  }

  const header = ['word', 'phonetic', 'pos', 'definition', 'source_book', 'source_chapter', 'created_at']
  const rows = words.map(word => [
    word.word,
    stringifyValue(word.phonetic),
    stringifyValue(word.pos),
    stringifyValue(word.definition),
    resolveSourceBook(word),
    resolveSourceChapter(word),
    stringifyValue(word.created_at) || stringifyValue(word.updated_at),
  ].map(escapeCsvValue).join(','))
  return [header.join(','), ...rows].join('\n')
}

function resolveMimeType(format: FavoriteWordExportFormat) {
  if (format === 'json') return 'application/json;charset=utf-8'
  if (format === 'csv') return 'text/csv;charset=utf-8'
  return 'text/plain;charset=utf-8'
}

export function downloadFavoriteWordsExport(
  words: FavoriteWordRecord[],
  username: string,
  format: FavoriteWordExportFormat,
) {
  const content = buildFavoriteWordsExportContent(words, format)
  const blob = new Blob([content], { type: resolveMimeType(format) })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `favorite-words-${sanitizeFilenameSegment(username)}.${format}`
  anchor.click()
  URL.revokeObjectURL(url)
}
