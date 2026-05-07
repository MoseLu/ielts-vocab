import type { GameCampaignState, GameMapPathNode } from '../../../../lib'
import { responsiveLayoutSlotStyle } from './gameTemplateLayout'

export type SegmentSlotStyle = ReturnType<typeof responsiveLayoutSlotStyle> & {
  '--map-node-delay': string
}

export type SegmentLabelStyle = SegmentSlotStyle & {
  '--map-label-scale': string
  '--map-label-font-size': string
}

export const WORD_SLOT_IDS = [
  'map.word.1',
  'map.word.2',
  'map.word.3',
  'map.word.4',
  'map.word.5',
] as const

export const DESKTOP_MAP_LAYOUT = 'wordChainMap'
export const MOBILE_MAP_LAYOUT = 'mobileWordChainMap'

export const SAMPLE_WORD_TITLES = ['language', 'context', 'evidence', 'analysis', 'structure'] as const

export const DECORATIVE_LABEL_NODES = [
  { nodeKey: 'template:boss', title: 'Boss', slotId: 'map.boss', status: 'boss' },
  { nodeKey: 'template:refill', title: '回流', slotId: 'map.refill', status: 'refill' },
  { nodeKey: 'template:reward', title: '宝箱', slotId: 'map.reward', status: 'reward' },
] as const

export const MAP_NODE_STATUS_LABEL = {
  current: '当前',
  cleared: '已亮',
  locked: '待练',
  refill: '回流',
  boss: 'Boss',
  reward: '奖励',
} as const

export const MAP_NODE_STATUS_CLASS = {
  current: 'active',
  cleared: 'cleared',
  locked: 'locked',
  refill: 'refill',
  boss: 'boss',
  reward: 'cleared',
} as const

export type MapNodeStatus = keyof typeof MAP_NODE_STATUS_LABEL

export function formatCount(value: number): string {
  return Math.max(0, value).toLocaleString('zh-CN')
}

export function progressPercent(done: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((done / total) * 100)))
}

export function taskFocusLabel(state: GameCampaignState): string {
  const task = state.taskFocus?.task
  if (task === 'due-review') return '到期复习'
  if (task === 'error-review') return '错维回流'
  if (task === 'speaking') return '口语补练'
  if (task === 'add-book') return '添加词书'
  return '主线新词'
}

export function nodeSlotId(node: GameMapPathNode, status: MapNodeStatus, wordIndex: number): string {
  if (status === 'boss' || node.nodeType === 'speaking_boss') return 'map.boss'
  if (status === 'reward' || node.nodeType === 'speaking_reward') return 'map.reward'
  return WORD_SLOT_IDS[Math.min(wordIndex, WORD_SLOT_IDS.length - 1)]
}

export function mapSlotStyle(slotId: string): ReturnType<typeof responsiveLayoutSlotStyle> {
  return responsiveLayoutSlotStyle(DESKTOP_MAP_LAYOUT, slotId, MOBILE_MAP_LAYOUT, slotId)
}

export function segmentSlotStyle(slotId: string, index: number): SegmentSlotStyle {
  return {
    ...mapSlotStyle(slotId),
    '--map-node-delay': `${index * 60}ms`,
  }
}

function labelWeight(text: string): number {
  return Array.from(text).reduce((total, char) => total + (/[\u4e00-\u9fff]/u.test(char) ? 1.7 : 1), 0)
}

function mapLabelScale(text: string): string {
  const weight = labelWeight(text)
  if (weight >= 24) return '0.68'
  if (weight >= 13) return '0.78'
  if (weight >= 10) return '0.86'
  return '1'
}

function mapLabelFontSize(text: string): string {
  const weight = labelWeight(text)
  if (weight >= 24) return 'clamp(var(--size-6), 0.55vw, var(--size-8))'
  if (weight >= 13) return 'clamp(var(--size-6), 0.8vw, var(--size-10))'
  if (weight >= 10) return 'clamp(var(--size-8), 0.9vw, var(--size-11))'
  return 'clamp(var(--size-6), 1.05vw, var(--size-13))'
}

export function segmentLabelStyle(slotId: string, index: number, title: string): SegmentLabelStyle {
  return {
    ...segmentSlotStyle(slotId, index),
    '--map-label-scale': mapLabelScale(title),
    '--map-label-font-size': mapLabelFontSize(title),
  }
}

export function compactTemplateNodeTitle(node: { slotId: string; title: string }): string {
  if (node.slotId === 'map.boss') return 'Boss'
  if (node.slotId === 'map.refill') return '回流'
  if (node.slotId === 'map.reward') return '宝箱'
  return node.title
}
