import { describe, expect, it, vi } from 'vitest'
import { evaluateFollowReadPronunciation } from './followReadScoring'

const apiFetchMock = vi.fn()

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

describe('followReadScoring', () => {
  it('posts user audio and reference audio as multipart form data', async () => {
    apiFetchMock.mockResolvedValue({
      word: 'alpha',
      score: 76,
      band: 'near_pass',
      passed: false,
      transcript: 'alpha',
      feedback: {
        summary: 'Close.',
        stress: 'Stress is close.',
        vowel: 'Open the vowel.',
        consonant: 'Clear consonants.',
        ending: 'Finish the ending.',
        rhythm: 'Keep a steady rhythm.',
      },
      weakSegments: ['al'],
      provider: 'dashscope',
      model: 'qwen-audio-turbo',
    })

    const result = await evaluateFollowReadPronunciation({
      word: 'alpha',
      phonetic: '/a/',
      bookId: 'book-1',
      chapterId: '2',
      durationSeconds: 3,
      audio: new Blob(['user-audio'], { type: 'audio/webm' }),
      referenceAudio: new Blob(['reference-audio'], { type: 'audio/mpeg' }),
    })

    expect(result.band).toBe('near_pass')
    expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/follow-read/evaluate', {
      method: 'POST',
      body: expect.any(FormData),
    })
    const formData = apiFetchMock.mock.calls[0][1].body as FormData
    expect(formData.get('word')).toBe('alpha')
    expect(formData.get('phonetic')).toBe('/a/')
    expect(formData.get('bookId')).toBe('book-1')
    expect(formData.get('chapterId')).toBe('2')
    expect(formData.get('durationSeconds')).toBe('3')
    expect(formData.get('audio')).toBeInstanceOf(File)
    expect(formData.get('referenceAudio')).toBeInstanceOf(File)
  })
})
