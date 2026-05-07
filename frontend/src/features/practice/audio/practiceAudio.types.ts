import type { FollowReadPayload, FollowReadSegment } from './followReadApi'

export type WordAudioSourcePreference = 'url' | 'buffer'

export interface PracticeAudioRequestContext {
  requestId?: string
  origin: string
  wordKey?: string | null
  queueIndex?: number | null
  autoplay?: boolean
}

export interface WordAudioRequest {
  kind: 'word'
  word: string
  sourcePreference?: WordAudioSourcePreference
}

export interface ExampleAudioRequest {
  kind: 'example'
  sentence: string
  word: string
}

export interface FollowSequenceAudioRequest {
  kind: 'follow-sequence'
  payload: FollowReadPayload
}

export type PracticeAudioRequest =
  | WordAudioRequest
  | ExampleAudioRequest
  | FollowSequenceAudioRequest

export interface PracticeAudioPlaySettings {
  playbackSpeed?: string | number
  volume?: string | number
}

export interface PreparedAudioClip {
  clipId: string
  buffer: ArrayBuffer | null
  fallbackUrl: string | null
  cacheKey: string | null
  durationMs: number | null
  playbackRate: number
  trackTimeline: boolean
}

export interface PreparedAudioAsset {
  assetId: string
  kind: PracticeAudioRequest['kind']
  wordKey: string | null
  cacheKey: string | null
  clips: PreparedAudioClip[]
  request: PracticeAudioRequest
  timeline?: FollowReadSegment[]
}

export type PracticeAudioState =
  | 'idle'
  | 'preparing'
  | 'playing'
  | 'ended'
  | 'blocked'
  | 'error'

export interface PracticeAudioSnapshot {
  state: PracticeAudioState
  requestId: string | null
  origin: string | null
  wordKey: string | null
  queueIndex: number | null
  autoplay: boolean
  assetId: string | null
  clipIndex: number
  clipCount: number
  currentTimeMs: number
  durationMs: number | null
  error: string | null
}

export type PracticeAudioListener = (snapshot: PracticeAudioSnapshot) => void
