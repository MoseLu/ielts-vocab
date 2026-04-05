import {
  type WrongWordCollectionScope,
  type WrongWordDimension,
  type WrongWordRecord,
  WRONG_WORD_DIMENSIONS,
  getWrongWordDimensionHistoryWrong,
  isWrongWordPendingInDimension,
} from '../../../features/vocabulary/wrongWordsStore'

export function getScopedWrongWordDimensions(
  word: Partial<WrongWordRecord>,
  scope: WrongWordCollectionScope,
): WrongWordDimension[] {
  return WRONG_WORD_DIMENSIONS.filter(dimension => {
    if (scope === 'history') {
      return getWrongWordDimensionHistoryWrong(word, dimension) > 0
    }

    return isWrongWordPendingInDimension(word, dimension)
  })
}

export function normalizeWrongWordKey(word: string): string {
  return word.trim().toLowerCase()
}

export function dedupeWrongWordKeys(keys: string[]): string[] {
  const result: string[] = []
  const seen = new Set<string>()

  keys.forEach(key => {
    const normalized = normalizeWrongWordKey(key)
    if (!normalized || seen.has(normalized)) return
    seen.add(normalized)
    result.push(normalized)
  })

  return result
}

export function isSameWrongWordKeyList(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index])
}
