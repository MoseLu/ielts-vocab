export const MAX_CONFUSABLE_CUSTOM_GROUPS = 12
export const MAX_CONFUSABLE_CUSTOM_WORDS_PER_GROUP = 8

const WORD_TOKEN_RE = /[A-Za-z]+(?:[-'][A-Za-z]+)*/g
const GROUP_CONTINUATION_RE = /[，,;；、/]\s*$/

export interface CustomConfusableChapter {
  id: number | string
  title: string
  word_count?: number
  group_count?: number
  is_custom?: boolean
}

export interface ParsedConfusableDraft {
  groups: string[][]
  groupCount: number
  issues: string[]
}

export function parseConfusableCustomDraft(draft: string): ParsedConfusableDraft {
  const issues: string[] = []
  const groups: string[][] = []
  const rawSections = draft
    .split(/\r?\n\s*\r?\n/g)
    .map(section => section.trim())
    .filter(Boolean)

  const parseGroupWords = (rawGroup: string): string[] => {
    const tokens = rawGroup.match(WORD_TOKEN_RE) ?? []
    const seen = new Set<string>()
    const words: string[] = []

    tokens.forEach(token => {
      const normalized = token.trim().toLowerCase()
      if (!normalized || seen.has(normalized)) return
      seen.add(normalized)
      words.push(normalized)
    })

    return words
  }

  rawSections.forEach(section => {
    const sectionLines = section
      .split(/\r?\n/)
      .map(line => line.trim())
      .filter(Boolean)

    const shouldMergeAsSingleGroup =
      sectionLines.length === 1 ||
      sectionLines.every(line => (line.match(WORD_TOKEN_RE) ?? []).length <= 1) ||
      sectionLines.some(line => GROUP_CONTINUATION_RE.test(line))

    const rawGroups = shouldMergeAsSingleGroup ? [section] : sectionLines

    rawGroups.forEach(rawGroup => {
      const words = parseGroupWords(rawGroup)
      const groupIndex = groups.length + 1

      if (words.length < 2) {
        issues.push(`第 ${groupIndex} 组至少需要 2 个不同单词`)
      } else if (words.length > MAX_CONFUSABLE_CUSTOM_WORDS_PER_GROUP) {
        issues.push(`第 ${groupIndex} 组最多支持 ${MAX_CONFUSABLE_CUSTOM_WORDS_PER_GROUP} 个单词`)
      }

      groups.push(words)
    })
  })

  if (groups.length > MAX_CONFUSABLE_CUSTOM_GROUPS) {
    issues.push(`一次最多创建 ${MAX_CONFUSABLE_CUSTOM_GROUPS} 组易混词`)
  }

  return {
    groups,
    groupCount: groups.length,
    issues,
  }
}
