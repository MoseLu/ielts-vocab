import { apiFetch } from '../../lib'
import type { Word } from './types'

export interface FollowReadSegment {
  id: string
  letter_start: number
  letter_end: number
  letters: string
  phonetic: string
  audio_phonetic?: string
  start_ms: number
  end_ms: number
}

export interface FollowReadAudioClip {
  id: string
  kind: 'full' | 'split' | string
  label: string
  url: string
  playback_rate: number
  track_segments: boolean
}

export interface FollowReadPayload {
  word: string
  phonetic: string
  definition: string
  pos: string
  audio_url: string
  audio_profile: 'full_chunk_full' | string
  audio_playback_rate: number
  chunk_audio_url: string
  chunk_audio_profile: 'full_chunk_full_merged' | string
  estimated_duration_ms: number
  segments: FollowReadSegment[]
  audio_sequence: FollowReadAudioClip[]
}

export function fetchFollowReadWord(word: Word): Promise<FollowReadPayload> {
  const params = new URLSearchParams({ w: word.word })
  if (word.phonetic) params.set('phonetic', word.phonetic)
  if (word.definition) params.set('definition', word.definition)
  if (word.pos) params.set('pos', word.pos)
  return apiFetch<FollowReadPayload>(`/api/tts/follow-read-word?${params.toString()}`)
}
