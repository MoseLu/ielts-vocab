export interface QuickMemorySessionResult {
  wordIdx: number
  choice: 'known' | 'unknown'
  wasFuzzy: boolean
}
