import type { WordDetailResponse, WordSearchResult } from '../../../lib'

export type WordMemoryNote = {
  badge: '谐音' | '联想'
  text: string
}

type BuildWordMemoryNoteParams = {
  detailData: WordDetailResponse | null
  result: WordSearchResult
}

type RootSegment = NonNullable<WordDetailResponse['root']>['segments'][number]

const SPECIAL_HOMOPHONE_WORDS: Record<string, string> = {
  animal: '安妮猫',
  minute: '迷你特',
  minutes: '迷你茨',
  park: '帕克',
  social: '收手',
  system: '西斯特姆',
}

const SOUND_CHUNKS: Array<{ chunk: string; sound: string }> = [
  { chunk: 'ture', sound: '彻' },
  { chunk: 'sure', sound: '舍' },
  { chunk: 'sion', sound: '申' },
  { chunk: 'tion', sound: '申' },
  { chunk: 'cial', sound: '肖' },
  { chunk: 'ment', sound: '门特' },
  { chunk: 'ness', sound: '尼斯' },
  { chunk: 'less', sound: '勒斯' },
  { chunk: 'ship', sound: '西普' },
  { chunk: 'able', sound: '诶博' },
  { chunk: 'ing', sound: '英' },
  { chunk: 'ous', sound: '厄斯' },
  { chunk: 'ive', sound: '伊夫' },
  { chunk: 'ize', sound: '艾兹' },
  { chunk: 'ise', sound: '艾兹' },
  { chunk: 'sys', sound: '西斯' },
  { chunk: 'tem', sound: '特姆' },
  { chunk: 'ani', sound: '安妮' },
  { chunk: 'mal', sound: '猫' },
  { chunk: 'min', sound: '迷你' },
  { chunk: 'ute', sound: '特' },
  { chunk: 'par', sound: '帕' },
  { chunk: 'ark', sound: '克' },
  { chunk: 'ch', sound: '奇' },
  { chunk: 'ck', sound: '克' },
  { chunk: 'ph', sound: '夫' },
  { chunk: 'qu', sound: '库' },
  { chunk: 'sh', sound: '什' },
  { chunk: 'th', sound: '斯' },
  { chunk: 'wh', sound: '维' },
  { chunk: 'ai', sound: '艾' },
  { chunk: 'al', sound: '奥' },
  { chunk: 'am', sound: '安' },
  { chunk: 'an', sound: '安' },
  { chunk: 'ar', sound: '阿尔' },
  { chunk: 'ea', sound: '伊' },
  { chunk: 'ee', sound: '伊' },
  { chunk: 'en', sound: '恩' },
  { chunk: 'er', sound: '尔' },
  { chunk: 'ie', sound: '艾' },
  { chunk: 'oa', sound: '欧' },
  { chunk: 'oo', sound: '乌' },
  { chunk: 'or', sound: '奥尔' },
  { chunk: 'ou', sound: '欧' },
]

const LETTER_SOUNDS: Record<string, string> = {
  a: '啊',
  b: '比',
  c: '西',
  d: '迪',
  e: '伊',
  f: '夫',
  g: '吉',
  h: '哈',
  i: '艾',
  j: '杰',
  k: '克',
  l: '勒',
  m: '姆',
  n: '恩',
  o: '欧',
  p: '皮',
  q: '奇',
  r: '尔',
  s: '斯',
  t: '特',
  u: '优',
  v: '维',
  w: '沃',
  x: '克斯',
  y: '伊',
  z: '兹',
}

function normalizeWord(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z]/g, '')
}

function trimDefinition(value: string | null | undefined): string {
  const compact = String(value ?? '')
    .replace(/\s+/g, ' ')
    .trim()
  const primary = compact.split(/[；;。.!?\n]/u).find(Boolean)?.trim() ?? ''
  if (!primary) return '这个词义'
  return primary.length > 18 ? `${primary.slice(0, 18)}…` : primary
}

function buildConfusableSuffix(result: WordSearchResult): string {
  const candidate = result.listening_confusables?.[0]
  if (!candidate || candidate.word.trim().toLowerCase() === result.word.trim().toLowerCase()) {
    return ''
  }

  const definition = trimDefinition(candidate.definition)
  return ` 也顺手和 ${candidate.word}（${definition}）分开记。`
}

function transliterateWord(word: string): string | null {
  const normalizedWord = normalizeWord(word)
  if (!normalizedWord) return null

  const special = SPECIAL_HOMOPHONE_WORDS[normalizedWord]
  if (special) return special
  if (normalizedWord.length < 3 || normalizedWord.length > 8) return null

  const sounds: string[] = []
  let index = 0
  let singleLetterMatches = 0

  while (index < normalizedWord.length) {
    const chunk = SOUND_CHUNKS.find(item => normalizedWord.startsWith(item.chunk, index))
    if (chunk) {
      sounds.push(chunk.sound)
      index += chunk.chunk.length
      continue
    }

    const letterSound = LETTER_SOUNDS[normalizedWord[index]]
    if (!letterSound) return null
    singleLetterMatches += 1
    if (singleLetterMatches > 2) return null
    sounds.push(letterSound)
    index += 1
  }

  if (sounds.length === 0 || sounds.length > 4) return null
  return sounds.join('')
}

function formatRootCue(segment: RootSegment): string {
  return `${segment.text}（${segment.meaning}）`
}

function buildAssociationText(
  detailData: WordDetailResponse | null,
  result: WordSearchResult,
  definition: string,
  confusableSuffix: string,
): string {
  const rootSegments = detailData?.root?.segments?.filter(
    (segment): segment is RootSegment => Boolean(segment?.text && segment?.meaning),
  ) ?? []
  if (rootSegments.length > 0) {
    const rootCue = rootSegments.slice(0, 2).map(formatRootCue).join(' + ')
    return `先抓 ${rootCue} 这几个词形线索，再把整体意思落到“${definition}”上。${confusableSuffix}`.trim()
  }

  const phonetic = detailData?.phonetic || result.phonetic
  if (phonetic) {
    return `先把读音 ${phonetic} 和“${definition}”绑定，再用例句把这个意思固定下来。${confusableSuffix}`.trim()
  }

  return `先记住它常表示“${definition}”，再在例句里反复回想这个场景。${confusableSuffix}`.trim()
}

export function buildWordMemoryNote({
  detailData,
  result,
}: BuildWordMemoryNoteParams): WordMemoryNote {
  const definition = trimDefinition(detailData?.definition || result.definition)
  const confusableSuffix = buildConfusableSuffix(result)
  const transliteration = transliterateWord(result.word)

  if (transliteration) {
    return {
      badge: '谐音',
      text: `${result.word} 可先听成“${transliteration}”，再把这个声音挂到“${definition}”上。${confusableSuffix}`.trim(),
    }
  }

  return {
    badge: '联想',
    text: buildAssociationText(detailData, result, definition, confusableSuffix),
  }
}
