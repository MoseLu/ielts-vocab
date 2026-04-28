import type { CSSProperties } from 'react'
import rawLayouts from './gameTemplateLayouts.json'

export type GameTemplateLayoutId = keyof typeof rawLayouts

type TemplateSlotId =
  typeof rawLayouts[GameTemplateLayoutId]['slots'][number]['id']

type SlotStyle = CSSProperties & {
  '--template-slot-left': string
  '--template-slot-top': string
  '--template-slot-width': string
  '--template-slot-height': string
  '--template-slot-center-x': string
  '--template-slot-center-y': string
  '--template-mobile-slot-left'?: string
  '--template-mobile-slot-top'?: string
  '--template-mobile-slot-width'?: string
  '--template-mobile-slot-height'?: string
  '--map-node-x': string
  '--map-node-y': string
}

export type GameTemplateSlot = {
  id: string
  x: number
  y: number
  width: number
  height: number
  allowOverlap?: boolean
}

export type GameTemplateLayout = {
  image: string
  naturalSize: { width: number; height: number }
  slots: GameTemplateSlot[]
}

export const GAME_TEMPLATE_LAYOUTS = rawLayouts as Record<GameTemplateLayoutId, GameTemplateLayout>

const REQUIRED_TEMPLATE_SLOTS: Record<GameTemplateLayoutId, string[]> = {
  learningCenter: ['learningCenter.hero', 'learningCenter.todayPlan', 'learningCenter.actions'],
  wordChainMap: ['map.hud.level', 'map.hud.energy', 'map.hud.coins', 'map.hud.diamonds', 'map.title', 'map.word.1', 'map.word.5', 'map.side.word', 'map.action', 'map.bottom.word', 'map.bottom.progress'],
  mobileWordChainMap: ['map.hud.level', 'map.hud.energy', 'map.hud.coins', 'map.hud.diamonds', 'map.title', 'map.word.1', 'map.word.5', 'map.side.word', 'map.action', 'map.bottom.word', 'map.bottom.progress'],
  wordMission: ['mission.hud', 'mission.objective', 'mission.answerPanel'],
  refillState: ['refill.hud', 'refill.list', 'refill.objective', 'refill.answerPanel', 'refill.action'],
  stageSettlement: ['settlement.medal', 'settlement.copy', 'settlement.rewards', 'settlement.actions'],
  mobileWordMission: ['mobileMission.hud', 'mobileMission.objective', 'mobileMission.answerPanel'],
}

function pct(value: number, total: number): string {
  return `${((value / total) * 100).toFixed(4)}%`
}

function intersects(a: GameTemplateSlot, b: GameTemplateSlot): boolean {
  return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y
}

export function findTemplateSlot(layoutId: GameTemplateLayoutId, slotId: TemplateSlotId | string): GameTemplateSlot {
  const slot = GAME_TEMPLATE_LAYOUTS[layoutId].slots.find(item => item.id === slotId)
  if (!slot) throw new Error(`Missing game template slot "${slotId}" in "${layoutId}"`)
  return slot
}

export function assertTemplateSlots(layoutId: GameTemplateLayoutId, slotIds: string[]): void {
  for (const slotId of slotIds) findTemplateSlot(layoutId, slotId)
}

export function layoutSlotStyle(layoutId: GameTemplateLayoutId, slotId: TemplateSlotId | string): SlotStyle {
  const layout = GAME_TEMPLATE_LAYOUTS[layoutId]
  const slot = findTemplateSlot(layoutId, slotId)
  const centerX = slot.x + slot.width / 2
  const centerY = slot.y + slot.height / 2
  return {
    '--template-slot-left': pct(slot.x, layout.naturalSize.width),
    '--template-slot-top': pct(slot.y, layout.naturalSize.height),
    '--template-slot-width': pct(slot.width, layout.naturalSize.width),
    '--template-slot-height': pct(slot.height, layout.naturalSize.height),
    '--template-slot-center-x': pct(centerX, layout.naturalSize.width),
    '--template-slot-center-y': pct(centerY, layout.naturalSize.height),
    '--map-node-x': pct(centerX, layout.naturalSize.width),
    '--map-node-y': pct(centerY, layout.naturalSize.height),
  }
}

export function responsiveLayoutSlotStyle(
  layoutId: GameTemplateLayoutId,
  slotId: TemplateSlotId | string,
  mobileLayoutId: GameTemplateLayoutId,
  mobileSlotId: TemplateSlotId | string,
): SlotStyle {
  const desktopStyle = layoutSlotStyle(layoutId, slotId)
  const mobileLayout = GAME_TEMPLATE_LAYOUTS[mobileLayoutId]
  const mobileSlot = findTemplateSlot(mobileLayoutId, mobileSlotId)
  return {
    ...desktopStyle,
    '--template-mobile-slot-left': pct(mobileSlot.x, mobileLayout.naturalSize.width),
    '--template-mobile-slot-top': pct(mobileSlot.y, mobileLayout.naturalSize.height),
    '--template-mobile-slot-width': pct(mobileSlot.width, mobileLayout.naturalSize.width),
    '--template-mobile-slot-height': pct(mobileSlot.height, mobileLayout.naturalSize.height),
  }
}

export function isGameTemplateDebugLayoutEnabled(): boolean {
  if (typeof window === 'undefined') return false
  const params = new URLSearchParams(window.location.search)
  return params.has('debugLayout') || window.localStorage.getItem('debugLayout') === '1'
}

export function validateGameTemplateLayouts(): string[] {
  const issues: string[] = []
  for (const [layoutId, layout] of Object.entries(GAME_TEMPLATE_LAYOUTS) as Array<[GameTemplateLayoutId, GameTemplateLayout]>) {
    if (!layout.image.startsWith('oss:game-template:')) issues.push(`${layoutId}: image must use an OSS template key`)
    if (layout.naturalSize.width <= 0 || layout.naturalSize.height <= 0) issues.push(`${layoutId}: invalid natural size`)
    for (const requiredSlot of REQUIRED_TEMPLATE_SLOTS[layoutId]) {
      if (!layout.slots.some(slot => slot.id === requiredSlot)) issues.push(`${layoutId}: missing required slot ${requiredSlot}`)
    }
    for (const slot of layout.slots) {
      if (slot.x < 0 || slot.y < 0 || slot.width <= 0 || slot.height <= 0) issues.push(`${layoutId}:${slot.id}: invalid rect`)
      if (slot.x + slot.width > layout.naturalSize.width || slot.y + slot.height > layout.naturalSize.height) {
        issues.push(`${layoutId}:${slot.id}: rect exceeds natural size`)
      }
    }
    const strictSlots = layout.slots.filter(slot => !slot.allowOverlap)
    for (let index = 0; index < strictSlots.length; index += 1) {
      for (let next = index + 1; next < strictSlots.length; next += 1) {
        if (intersects(strictSlots[index], strictSlots[next])) {
          issues.push(`${layoutId}: overlapping slots ${strictSlots[index].id} and ${strictSlots[next].id}`)
        }
      }
    }
  }
  return issues
}
