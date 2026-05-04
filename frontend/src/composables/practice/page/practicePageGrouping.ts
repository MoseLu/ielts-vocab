export interface PracticeGroupWindow {
  start: number
  end: number
  total: number
  groupSize: number | null
}

export function resolvePracticeGroupSize(settings: {
  reviewLimit?: string
  reviewLimitCustomized?: boolean
}): number | null {
  if (settings.reviewLimitCustomized !== true) return null
  if (settings.reviewLimit === 'unlimited') return null

  const groupSize = Number.parseInt(String(settings.reviewLimit), 10)
  return Number.isFinite(groupSize) && groupSize > 0 ? groupSize : null
}

export function buildPracticeGroupWindows(total: number, groupSize: number | null): PracticeGroupWindow[] {
  const safeTotal = Math.max(0, Math.floor(total))
  if (safeTotal <= 0) return []
  if (!groupSize || groupSize >= safeTotal) {
    return [{ start: 0, end: safeTotal, total: safeTotal, groupSize }]
  }

  const windows: PracticeGroupWindow[] = []
  for (let start = 0; start < safeTotal; start += groupSize) {
    windows.push({
      start,
      end: Math.min(start + groupSize, safeTotal),
      total: safeTotal,
      groupSize,
    })
  }

  const last = windows[windows.length - 1]
  if (last && last.end - last.start < groupSize && windows.length > 1) {
    windows[windows.length - 2] = {
      ...windows[windows.length - 2],
      end: last.end,
    }
    windows.pop()
  }
  return windows
}

export function resolvePracticeGroupWindow(
  total: number,
  groupSize: number | null,
  currentIndex = 0,
): PracticeGroupWindow | null {
  const windows = buildPracticeGroupWindows(total, groupSize)
  if (!windows.length) return null

  const safeIndex = Math.max(0, Math.min(Math.floor(currentIndex), Math.max(total - 1, 0)))
  return windows.find(window => safeIndex >= window.start && safeIndex < window.end) ?? windows[0]
}

export function sliceQueueForPracticeGroup(
  queue: number[],
  group: PracticeGroupWindow | null,
): number[] {
  if (!group) return queue
  return queue.slice(group.start, group.end)
}
