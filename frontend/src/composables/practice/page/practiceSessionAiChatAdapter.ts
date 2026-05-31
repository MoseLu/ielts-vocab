import * as AIChat from '../../../hooks/useAIChat'

export { AIChat }

export function normalizeDuration(total: number | null, extra = 0): number {
  return Math.max(0, Math.round(total ?? 0) + Math.max(0, Math.round(extra)))
}

export function getOptionalAIChatFunction<T extends (...args: any[]) => any>(key: string): T | null {
  try {
    const value = Reflect.get(AIChat as object, key)
    return typeof value === 'function' ? (value as T) : null
  } catch {
    return null
  }
}

export function getAIChatNumber(key: string, fallback: number): number {
  try {
    const value = Reflect.get(AIChat as object, key)
    return typeof value === 'number' ? value : fallback
  } catch {
    return fallback
  }
}
