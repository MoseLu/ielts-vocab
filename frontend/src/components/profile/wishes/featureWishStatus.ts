export type FeatureWishEditableStatus = 'open' | 'planned' | 'done'

export const WISH_STATUS_OPTIONS: Array<{ value: FeatureWishEditableStatus; label: string }> = [
  { value: 'open', label: '待评估' },
  { value: 'planned', label: '已排期' },
  { value: 'done', label: '已完成' },
]

const WISH_STATUS_LABELS: Record<string, string> = {
  open: '待评估',
  planned: '已排期',
  done: '已完成',
  closed: '已完成',
}

export function statusLabel(status: string | null | undefined) {
  return WISH_STATUS_LABELS[status || 'open'] ?? status ?? '待评估'
}

export function statusTone(status: string | null | undefined): FeatureWishEditableStatus {
  if (status === 'done' || status === 'closed') return 'done'
  if (status === 'planned') return 'planned'
  return 'open'
}

export function editableStatusValue(status: string | null | undefined): FeatureWishEditableStatus {
  return statusTone(status)
}
