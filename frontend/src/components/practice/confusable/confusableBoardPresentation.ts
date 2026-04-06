import type { MatchWord } from '../confusableMatch'

const GROUP_ACCENTS = [
  'var(--accent)',
  'var(--tone-blue)',
  'var(--success)',
  'var(--warning)',
  'var(--tone-indigo)',
]

export type WordDiffPart = {
  text: string
  isDiff: boolean
}

function hashKey(input: string): number {
  let hash = 0
  for (let index = 0; index < input.length; index += 1) {
    hash = (hash * 31 + input.charCodeAt(index)) >>> 0
  }
  return hash
}

function findSharedPrefix(words: string[]): string {
  if (!words.length) return ''
  let prefix = words[0].toLowerCase()
  for (const word of words.slice(1)) {
    let cursor = 0
    const next = word.toLowerCase()
    while (cursor < prefix.length && cursor < next.length && prefix[cursor] === next[cursor]) {
      cursor += 1
    }
    prefix = prefix.slice(0, cursor)
    if (!prefix) break
  }
  return prefix
}

export function getConfusableGroupAccent(groupKey: string): string {
  return GROUP_ACCENTS[hashKey(groupKey) % GROUP_ACCENTS.length]
}

export function summarizeConfusableWords(words: MatchWord[], limit = 4): string {
  const labels = words.map(word => word.word)
  if (labels.length <= limit) return labels.join(' / ')
  return `${labels.slice(0, limit).join(' / ')} / …`
}

export function buildConfusableContrastNote(words: MatchWord[]): string {
  const labels = words.map(word => word.word)
  const prefix = findSharedPrefix(labels)
  if (prefix.length >= 3) {
    return `这组词都带有 ${prefix} 的共同词形，重点区分后半段变化和对应词义。`
  }
  if (labels.length >= 2) {
    return `这组词外形接近，尤其容易在中段和结尾混淆，先看词形差异，再记中文义。`
  }
  return '这组词形相近，先抓住单词轮廓，再记住对应中文义。'
}

export function buildWordDiffParts(word: string, compareTo?: string): WordDiffPart[] {
  if (!compareTo || compareTo.toLowerCase() === word.toLowerCase()) {
    return [{ text: word, isDiff: false }]
  }

  const source = Array.from(word)
  const target = Array.from(compareTo)
  const maxLength = Math.max(source.length, target.length)
  const parts: WordDiffPart[] = []
  let buffer = ''
  let currentDiff = false

  for (let index = 0; index < maxLength; index += 1) {
    const char = source[index] ?? ''
    const other = target[index] ?? ''
    const isDiff = char.toLowerCase() !== other.toLowerCase()

    if (index === 0) {
      currentDiff = isDiff
      buffer = char
      continue
    }

    if (isDiff === currentDiff) {
      buffer += char
      continue
    }

    if (buffer) {
      parts.push({ text: buffer, isDiff: currentDiff })
    }
    buffer = char
    currentDiff = isDiff
  }

  if (buffer) {
    parts.push({ text: buffer, isDiff: currentDiff })
  }

  return parts.filter(part => part.text.length > 0)
}
