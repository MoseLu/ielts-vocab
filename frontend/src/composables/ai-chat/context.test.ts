import { beforeEach, describe, expect, it, vi } from 'vitest'
import { buildAIChatContext } from './context'
import { writeWrongWordsToStorage } from '../../features/vocabulary/wrongWordsStore'

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

describe('buildAIChatContext', () => {
  it('includes only recent wrong words in assistant context when timestamps exist', () => {
    const now = Date.now()
    writeWrongWordsToStorage([
      {
        word: 'abandon',
        updated_at: new Date(now - 2 * 60 * 60 * 1000).toISOString(),
      },
      {
        word: 'abate',
        updated_at: new Date(now - 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        word: 'abbey',
        updated_at: new Date(now - 5 * 24 * 60 * 60 * 1000).toISOString(),
      },
    ])

    const context = buildAIChatContext()

    expect(context.recentWrongWords).toEqual(['abandon', 'abate'])
  })

  it('falls back to storage order when wrong-word timestamps are missing', () => {
    writeWrongWordsToStorage([
      { word: 'abandon' },
      { word: 'abate' },
      { word: 'abbey' },
    ])

    const context = buildAIChatContext()

    expect(context.recentWrongWords).toEqual(['abandon', 'abate', 'abbey'])
  })
})
