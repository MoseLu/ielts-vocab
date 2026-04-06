import {
  type WrongWordCollectionScope,
  type WrongWordDimension,
  type WrongWordRecord,
  WRONG_WORD_DIMENSIONS,
  WRONG_WORD_DIMENSION_LABELS,
  WRONG_WORD_DIMENSION_TITLES,
  getWrongWordDimensionHistoryWrong,
  getWrongWordDimensionProgress,
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

export function describeWrongWordDimension(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
) {
  const historyWrong = getWrongWordDimensionHistoryWrong(word, dimension)
  const progress = getWrongWordDimensionProgress(word, dimension)

  return {
    label: WRONG_WORD_DIMENSION_LABELS[dimension],
    detail: `累计错 ${historyWrong} 次`,
    status: progress.pending ? `还差 ${progress.remaining} 次过关` : '这一项已过关',
    title: progress.pending
      ? `${WRONG_WORD_DIMENSION_TITLES[dimension]}：累计错 ${historyWrong} 次，还差 ${progress.remaining} 次连续答对就能转成已过关`
      : `${WRONG_WORD_DIMENSION_TITLES[dimension]}：累计错 ${historyWrong} 次，目前这一项已经过关`,
    pending: progress.pending,
  }
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
