import { useSyncExternalStore } from 'react'

export interface HeaderHelpFaqSection {
  label: string
  items: string[]
}

export interface HeaderHelpFaqItem {
  id: string
  eyebrow: string
  title: string
  badge: string
  description: string
  facts: string[]
  sections: HeaderHelpFaqSection[]
  tone: 'accent' | 'error' | 'success' | 'neutral'
}

const listeners = new Set<() => void>()
let planHelpFaqItems: HeaderHelpFaqItem[] = []

function emitChange() {
  listeners.forEach(listener => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function getSnapshot() {
  return planHelpFaqItems
}

export function setPlanHelpFaqItems(items: HeaderHelpFaqItem[]) {
  planHelpFaqItems = items
  emitChange()
}

export function clearPlanHelpFaqItems() {
  if (planHelpFaqItems.length === 0) return

  planHelpFaqItems = []
  emitChange()
}

export function usePlanHelpFaqItems() {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
}
