export type QuickMemoryModeVariant = 'quickmemory' | 'test'

export interface QuickMemorySessionResult {
  wordIdx: number
  choice: 'known' | 'unknown'
  wasFuzzy: boolean
}
