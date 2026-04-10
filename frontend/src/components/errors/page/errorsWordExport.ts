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

export function buildWrongWordsCsvExportContent(words: WrongWordRecord[]) {
  const header = ['序号', '错词', '中文意思']
  const rows = words.map((word, index) => [
    String(index + 1),
    stringifyValue(word.word),
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
