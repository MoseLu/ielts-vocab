const LISTENING_INFLECTION_DEFINITION_RE = /(?:复数|现在分词|过去式|过去分词|第三人称单数|\bpl\.)/i

type ListeningInflectionCandidate = {
  word: string
  definition?: string | null
}

type ListeningConfusabilityCandidate = {
  word: string
  phonetic?: string | null
}

function normalizeInflectionWord(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[’‘`]/g, "'")
    .replace(/[‐‑‒–—―]/g, '-')
    .replace(/^[\s"'“”‘’.,!?;:()[\]{}]+/, '')
    .replace(/[\s"'“”‘’.,!?;:()[\]{}]+$/, '')
    .replace(/\s+/g, ' ')
}

function listeningInflectionBaseKeys(word: string): string[] {
  const key = normalizeInflectionWord(word)
  if (!key || key.includes(' ')) return []

  const keys = new Set<string>()
  const add = (value: string) => {
    const normalized = normalizeInflectionWord(value)
    if (normalized && normalized !== key) keys.add(normalized)
  }

  if (key.endsWith('ies') && key.length > 4) add(`${key.slice(0, -3)}y`)
  if (key.endsWith('ves') && key.length > 4) {
    add(`${key.slice(0, -3)}f`)
    add(`${key.slice(0, -3)}fe`)
  }
  if (/(?:ches|shes|xes|zes|ses|oes)$/.test(key) && key.length > 4) add(key.slice(0, -2))
  if (key.endsWith('s') && key.length > 3 && !/(?:ss|us|is)$/.test(key)) add(key.slice(0, -1))
  if (key.endsWith('ing') && key.length > 5) {
    const stem = key.slice(0, -3)
    add(stem)
    add(`${stem}e`)
    if (stem.length > 2 && stem[stem.length - 1] === stem[stem.length - 2]) add(stem.slice(0, -1))
  }
  if (key.endsWith('ied') && key.length > 4) add(`${key.slice(0, -3)}y`)
  if (key.endsWith('ed') && key.length > 4) {
    const stem = key.slice(0, -2)
    add(stem)
    add(`${stem}e`)
    if (stem.length > 2 && stem[stem.length - 1] === stem[stem.length - 2]) add(stem.slice(0, -1))
  }

  return [...keys]
}

function levenshtein(left: string, right: string): number {
  const row = Array.from({ length: right.length + 1 }, (_value, index) => index)
  for (let leftIndex = 1; leftIndex <= left.length; leftIndex += 1) {
    let previousDiagonal = row[0]
    row[0] = leftIndex
    for (let rightIndex = 1; rightIndex <= right.length; rightIndex += 1) {
      const previousValue = row[rightIndex]
      row[rightIndex] = left[leftIndex - 1] === right[rightIndex - 1]
        ? previousDiagonal
        : 1 + Math.min(previousDiagonal, row[rightIndex], row[rightIndex - 1])
      previousDiagonal = previousValue
    }
  }
  return row[right.length]
}

function commonLength(left: string, right: string, fromEnd = false): number {
  let length = 0
  while (
    length < left.length
    && length < right.length
    && (
      fromEnd
        ? left[left.length - 1 - length] === right[right.length - 1 - length]
        : left[length] === right[length]
    )
  ) {
    length += 1
  }
  return length
}

function phoneticSimilarity(left: string | null | undefined, right: string | null | undefined): number {
  const normalizedLeft = String(left ?? '').replace(/[/[\]ˈˌ.: ]/g, '').toLowerCase()
  const normalizedRight = String(right ?? '').replace(/[/[\]ˈˌ.: ]/g, '').toLowerCase()
  if (!normalizedLeft || !normalizedRight) return 0
  return 1 - levenshtein(normalizedLeft, normalizedRight) / Math.max(normalizedLeft.length, normalizedRight.length)
}

export function isInflectedListeningDistractor(
  word: ListeningInflectionCandidate,
  knownWordKeys: Set<string>,
): boolean {
  if (LISTENING_INFLECTION_DEFINITION_RE.test(word.definition ?? '')) return true
  return listeningInflectionBaseKeys(word.word).some(key => knownWordKeys.has(key))
}

export function isStrongListeningDistractor(
  currentWord: ListeningConfusabilityCandidate,
  candidate: ListeningConfusabilityCandidate,
): boolean {
  const targetWord = normalizeInflectionWord(currentWord.word)
  const candidateWord = normalizeInflectionWord(candidate.word)
  if (!targetWord || !candidateWord) return false

  const spellingSimilarity = 1 - levenshtein(targetWord, candidateWord) / Math.max(targetWord.length, candidateWord.length, 1)
  return (
    phoneticSimilarity(currentWord.phonetic, candidate.phonetic) >= 0.62
    || spellingSimilarity >= 0.65
    || (
      spellingSimilarity >= 0.55
      && commonLength(targetWord, candidateWord) >= 3
      && commonLength(targetWord, candidateWord, true) >= 1
    )
  )
}
