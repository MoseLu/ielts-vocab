import { describe, expect, it, vi } from 'vitest'
import { evaluateFollowReadPronunciation, explainFollowReadPronunciation } from './followReadScoring'

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
      segmentFeedback: [
        { text: 'al', score: 52, status: 'weak', comment: 'al 需要重读。' },
      ],
      provider: 'dashscope',
      model: 'qwen-audio-turbo',
    })

    const result = await evaluateFollowReadPronunciation({
      word: 'alpha',
      phonetic: '/a/',
      bookId: 'book-1',
      chapterId: '2',
      durationSeconds: 3,
      segments: [
        { text: 'al', phonetic: 'æl' },
        { text: 'pha', phonetic: 'fə' },
      ],
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
    expect(JSON.parse(String(formData.get('segments')))).toEqual([
      { text: 'al', phonetic: 'æl' },
      { text: 'pha', phonetic: 'fə' },
    ])
    expect(formData.get('audio')).toBeInstanceOf(File)
    expect(formData.get('referenceAudio')).toBeInstanceOf(File)
  })

  it('parses Azure phoneme feedback and requests async explanation', async () => {
    apiFetchMock.mockResolvedValueOnce({
      word: 'language',
      score: 86,
      band: 'pass',
      passed: true,
      transcript: 'language',
      feedback: {
        summary: '发音整体清晰。',
        stress: '重音稳定。',
        vowel: '元音稳定。',
        consonant: '辅音稳定。',
        ending: '收音完整。',
        rhythm: '韵律仅供参考。',
      },
      segmentFeedback: [
        { text: 'lan', phonetic: 'læŋ', score: 90, status: 'good' },
      ],
      phonemeFeedback: [
        {
          expectedPhoneme: 'æ',
          score: 88,
          status: 'good',
          candidatePhonemes: [{ phoneme: 'e', confidence: 62 }],
        },
      ],
      dimensions: {
        phonemeAccuracy: 86,
        completeness: 92,
        fluency: 81,
        prosody: 75,
      },
      scoringProvider: 'azure-pronunciation-dual-locale',
      assessmentVersion: 'azure-pilot-v1',
      explanationToken: 'signed-token',
    })
    apiFetchMock.mockResolvedValueOnce({ summary: '把 æ 保持得更饱满。' })

    const result = await evaluateFollowReadPronunciation({
      word: 'language',
      segments: [{ text: 'lan', phonetic: 'læŋ' }],
      audio: new Blob(['user-audio'], { type: 'audio/webm' }),
    })
    const summary = await explainFollowReadPronunciation(result.explanationToken || '')

    expect(result.phonemeFeedback[0].candidatePhonemes[0]).toEqual({ phoneme: 'e', confidence: 62 })
    expect(result.dimensions?.prosody).toBe(75)
    expect(summary).toBe('把 æ 保持得更饱满。')
    expect(apiFetchMock).toHaveBeenLastCalledWith('/api/ai/follow-read/explain', {
      method: 'POST',
      body: JSON.stringify({ token: 'signed-token' }),
    })
  })
})
