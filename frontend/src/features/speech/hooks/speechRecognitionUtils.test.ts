import { describe, expect, it } from 'vitest'
import { normalizeAudioLevel, SPEECH_IDLE_LEVEL, SPEECH_MIN_ACTIVE_LEVEL } from './speechRecognitionUtils'

describe('normalizeAudioLevel', () => {
  it('treats near-silence as idle', () => {
    const input = new Float32Array(2048).fill(0.0005)

    expect(normalizeAudioLevel(input)).toBe(SPEECH_IDLE_LEVEL)
  })

  it('keeps normal speech in a visible waveform range without flattening it', () => {
    const input = Float32Array.from({ length: 2048 }, (_, index) => (
      Math.sin(index / 9) * 0.12
    ))

    expect(normalizeAudioLevel(input)).toBeGreaterThan(0.07)
    expect(normalizeAudioLevel(input)).toBeLessThan(0.1)
  })

  it('still detects weak but audible input', () => {
    const input = Float32Array.from({ length: 2048 }, (_, index) => (
      Math.sin(index / 7) * 0.05
    ))

    expect(normalizeAudioLevel(input)).toBeGreaterThan(0.03)
    expect(normalizeAudioLevel(input)).toBeGreaterThan(SPEECH_MIN_ACTIVE_LEVEL)
  })
})
