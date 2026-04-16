import {
  type CustomBookChapterDraft,
  type CustomBookWordDraft,
  createChapterDraft,
} from './customBookDraft'

const WORD_COLUMNS = ['word', 'term', 'vocab', 'vocabulary', '单词', '词']
const PHONETIC_COLUMNS = ['phonetic', 'pronunciation', '音标']
const POS_COLUMNS = ['pos', 'part_of_speech', '词性']
const DEFINITION_COLUMNS = ['definition', 'translation', 'meaning', '释义', '中文']
const CHAPTER_COLUMNS = ['chapter', 'chapter_title', 'chaptertitle', 'title', 'unit', '章节']

function normalizeHeader(value: string): string {
  return value.trim().toLowerCase().replace(/[\s-]+/g, '_')
}

function parseCsvRows(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let inQuotes = false

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index]
    const nextChar = text[index + 1]

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        cell += '"'
        index += 1
      } else {
        inQuotes = !inQuotes
      }
      continue
    }

    if (char === ',' && !inQuotes) {
      row.push(cell.trim())
      cell = ''
      continue
    }

    if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && nextChar === '\n') index += 1
      row.push(cell.trim())
      if (row.some(value => value.length > 0)) rows.push(row)
      row = []
      cell = ''
      continue
    }

    cell += char
  }

  row.push(cell.trim())
  if (row.some(value => value.length > 0)) rows.push(row)
  return rows
}

function findColumn(headers: string[], candidates: string[]): number {
  return headers.findIndex(header => candidates.includes(header))
}

function buildEntryFromRow(row: string[], columns: Record<string, number>): CustomBookWordDraft | null {
  const wordIndex = columns.word
  const word = (wordIndex >= 0 ? row[wordIndex] : row[0])?.trim()
  if (!word) return null

  return {
    word,
    phonetic: columns.phonetic >= 0 ? row[columns.phonetic]?.trim() : undefined,
    pos: columns.pos >= 0 ? row[columns.pos]?.trim() : undefined,
    definition: columns.definition >= 0 ? row[columns.definition]?.trim() : undefined,
  }
}

function chunkEntries(
  entries: CustomBookWordDraft[],
  chapterWordTarget: number,
  startIndex: number,
): CustomBookChapterDraft[] {
  const chunkSize = Math.max(1, chapterWordTarget)
  const chapters: CustomBookChapterDraft[] = []
  for (let index = 0; index < entries.length; index += chunkSize) {
    const chunk = entries.slice(index, index + chunkSize)
    const chapterNumber = startIndex + chapters.length + 1
    chapters.push(createChapterDraft(chapters.length + 1, {
      title: `第${chapterNumber}章`,
      entries: chunk,
    }))
  }
  return chapters
}

export function parseCustomBookCsv(
  text: string,
  chapterWordTarget: number,
  startIndex = 0,
): CustomBookChapterDraft[] {
  const rows = parseCsvRows(text.trim().replace(/^\uFEFF/, ''))
  if (rows.length === 0) return []

  const headerCandidates = rows[0].map(normalizeHeader)
  const wordColumn = findColumn(headerCandidates, WORD_COLUMNS)
  const hasKnownHeader = wordColumn >= 0 || findColumn(headerCandidates, CHAPTER_COLUMNS) >= 0
  const dataRows = hasKnownHeader ? rows.slice(1) : rows
  const columns = {
    word: hasKnownHeader ? wordColumn : 0,
    phonetic: hasKnownHeader ? findColumn(headerCandidates, PHONETIC_COLUMNS) : 1,
    pos: hasKnownHeader ? findColumn(headerCandidates, POS_COLUMNS) : 2,
    definition: hasKnownHeader ? findColumn(headerCandidates, DEFINITION_COLUMNS) : 3,
    chapter: hasKnownHeader ? findColumn(headerCandidates, CHAPTER_COLUMNS) : -1,
  }

  if (columns.chapter < 0) {
    const entries = dataRows
      .map(row => buildEntryFromRow(row, columns))
      .filter((entry): entry is CustomBookWordDraft => Boolean(entry))
    return chunkEntries(entries, chapterWordTarget, startIndex)
  }

  const grouped = new Map<string, CustomBookWordDraft[]>()
  for (const row of dataRows) {
    const entry = buildEntryFromRow(row, columns)
    if (!entry) continue
    const chapterTitle = row[columns.chapter]?.trim() || `第${startIndex + grouped.size + 1}章`
    grouped.set(chapterTitle, [...(grouped.get(chapterTitle) ?? []), entry])
  }

  return Array.from(grouped, ([title, entries], index) => (
    createChapterDraft(index + 1, { title, entries })
  ))
}
