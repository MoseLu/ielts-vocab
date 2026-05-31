import type { MatchCard } from './confusableMatch'

export type ActiveLine = {
  id: string
  groupKey: string
  path: string
}

export function measureLine(
  boardElement: HTMLDivElement | null,
  fromElement: HTMLElement | null,
  toElement: HTMLElement | null,
  groupKey: string,
): ActiveLine | null {
  if (!boardElement || !fromElement || !toElement) return null

  const boardRect = boardElement.getBoundingClientRect()
  const fromRect = fromElement.getBoundingClientRect()
  const toRect = toElement.getBoundingClientRect()
  const x1 = fromRect.left + fromRect.width / 2 - boardRect.left
  const y1 = fromRect.top + fromRect.height / 2 - boardRect.top
  const x2 = toRect.left + toRect.width / 2 - boardRect.left
  const y2 = toRect.top + toRect.height / 2 - boardRect.top
  const railY = Math.max(14, Math.min(y1, y2) - 24)

  return {
    id: `${fromElement.dataset.cardId ?? 'from'}-${toElement.dataset.cardId ?? 'to'}`,
    groupKey,
    path: `M ${x1} ${y1} L ${x1} ${railY} L ${x2} ${railY} L ${x2} ${y2}`,
  }
}

export function getSelectionHint(selectedCard: MatchCard | null): string {
  if (!selectedCard) return '每个小棋盘都是一整组易混词，组内词数不固定，优先在当前组内完成消除。'
  return selectedCard.side === 'word'
    ? `继续点击对应中文：${selectedCard.word}`
    : `继续点击对应英文：${selectedCard.label}`
}
