import { PRACTICE_MODE_LABELS, type PracticeMode } from '@ielts-vocab/app-core'
import type { NavigateOptions } from '../navigation/types'
import type { PracticeEntryKey } from './PracticeEntryPanel'

export const PRACTICE_MODES: PracticeMode[] = ['smart', 'quickmemory', 'test', 'listening', 'meaning', 'dictation', 'follow', 'radio', 'errors']

export const PRACTICE_MODE_HINTS: Record<PracticeMode, string> = {
  smart: '按当前词书和复习状态智能出题',
  quickmemory: '快速认词，写入复习队列',
  test: '听音判断熟悉度，写入复习队列',
  listening: '听音辨义，训练反应速度',
  meaning: '看中文，主动拼出英文',
  dictation: '听音写词，抓住拼写细节',
  follow: '跟读发音，记录语音表现',
  radio: '连续播放，适合碎片复习',
  errors: '读取错词队列，直接开始清理',
}

export function scoreLabel(label: string, value: number) {
  return `${label} ${value}`
}

export function entryForMode(mode?: PracticeMode): PracticeEntryKey {
  if (mode === 'errors') return 'errors'
  if (mode === 'follow') return 'follow'
  if (mode === 'quickmemory' || mode === 'test') return 'ebbinghaus'
  return 'regular'
}

export function entryLabel(entry: PracticeEntryKey | null, mode: PracticeMode) {
  if (entry === 'errors') return '错词练习'
  if (entry === 'ebbinghaus') return '艾宾浩斯'
  if (entry === 'follow') return '跟读练习'
  return PRACTICE_MODE_LABELS[mode]
}

export function searchableText(value: unknown) {
  return String(value ?? '').toLowerCase()
}

export function isRecognitionReviewMode(mode?: PracticeMode) {
  return mode === 'quickmemory' || mode === 'test'
}

export function hasExplicitScope(options?: NavigateOptions) {
  return Boolean(options?.bookId || options?.chapterId != null)
}

export function initialEntry(options?: NavigateOptions): PracticeEntryKey | null {
  if (!options?.bookId && !options?.mode) return null
  if (hasExplicitScope(options) && isRecognitionReviewMode(options.mode)) return 'regular'
  return entryForMode(options.mode)
}

export function initialDueReviewRequested(options?: NavigateOptions) {
  return isRecognitionReviewMode(options?.mode) && !hasExplicitScope(options)
}
