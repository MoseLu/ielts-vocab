import type { WrongWordRecord } from '../../../features/vocabulary/wrongWordsStore'

function escapeCsvValue(value: string) {
  if (!/[",\n]/.test(value)) return value
  return `"${value.replace(/"/g, '""')}"`
}

function stringifyValue(value: string | null | undefined) {
  return String(value ?? '').trim()
}

function formatDateStamp(date: Date) {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}${month}${day}`
}

function normalizeExportWord(value: string | null | undefined) {
  return stringifyValue(value).toLocaleLowerCase('en')
}

export function sortWrongWordsForCsvExport(words: WrongWordRecord[]) {
  return [...words].sort((left, right) => {
    const leftWord = normalizeExportWord(left.word)
    const rightWord = normalizeExportWord(right.word)
    if (leftWord && !rightWord) return -1
    if (!leftWord && rightWord) return 1
    if (leftWord !== rightWord) return leftWord.localeCompare(rightWord, 'en')

    return stringifyValue(left.definition).localeCompare(stringifyValue(right.definition), 'zh-Hans')
  })
}

export function buildWrongWordsCsvExportContent(words: WrongWordRecord[]) {
  const header = ['单词', '音标', '释义']
  const rows = sortWrongWordsForCsvExport(words).map(word => [
    stringifyValue(word.word),
    stringifyValue(word.phonetic) || '—',
    stringifyValue(word.definition) || '—',
  ].map(escapeCsvValue).join(','))

  return [header.join(','), ...rows].join('\n')
}

export function downloadWrongWordsCsvExport(words: WrongWordRecord[]) {
  const content = buildWrongWordsCsvExportContent(words)
  const blob = new Blob(['\uFEFF', content], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')

  anchor.href = url
  anchor.download = `wrong-words-selected-${formatDateStamp(new Date())}.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}
