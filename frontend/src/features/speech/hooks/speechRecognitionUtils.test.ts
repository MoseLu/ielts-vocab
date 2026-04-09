import { describe, expect, it } from 'vitest'
import { normalizeAudioLevel, SPEECH_IDLE_LEVEL, SPEECH_MIN_ACTIVE_LEVEL } from './speechRecognitionUtils'

describe('normalizeAudioLevel', () => {
  it('treats near-silence as idle', () => {
    const input = new Float32Array(2048).fill(0.0005)

    expect(normalizeAudioLevel(input)).toBe(SPEECH_IDLE_LEVEL)
  })

  it('boosts normal speech into a clearly visible waveform range', () => {
    const input = Float32Array.from({ length: 2048 }, (_, index) => (
      Math.sin(index / 9) * 0.035
    ))

    expect(normalizeAudioLevel(input)).toBeGreaterThan(0.45)
  })

  it('clamps weak but audible input above the active floor', () => {
    const input = Float32Array.from({ length: 2048 }, (_, index) => (
      Math.sin(index / 7) * 0.008
    ))

    expect(normalizeAudioLevel(input)).toBeGreaterThanOrEqual(SPEECH_MIN_ACTIVE_LEVEL)
  })
})
