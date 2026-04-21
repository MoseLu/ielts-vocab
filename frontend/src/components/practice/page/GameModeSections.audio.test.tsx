import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WordMissionScreen } from './GameModeSections'

const playWordAudioMock = vi.fn(() => Promise.resolve(true))
const speechSynthesisSpeakMock = vi.fn()

vi.mock('../utils.audio', () => ({
  playWordAudio: (...args: unknown[]) => playWordAudioMock(...args),
}))

vi.mock('../../../lib/appSettings', () => ({
  readAppSettingsFromStorage: () => ({ playbackSpeed: '1.15', volume: '70' }),
}))

describe('GameModeSections audio', () => {
  beforeEach(() => {
    playWordAudioMock.mockReset()
    speechSynthesisSpeakMock.mockReset()
    ;(window as Window & { speechSynthesis: { speak: typeof speechSynthesisSpeakMock; cancel: ReturnType<typeof vi.fn> } }).speechSynthesis = {
      speak: speechSynthesisSpeakMock,
      cancel: vi.fn(),
    }
  })

  it('routes the listening and dictation playback buttons through shared word audio instead of speech synthesis', async () => {
    const user = userEvent.setup()
    const baseNode = {
      nodeType: 'word',
      nodeKey: 'word:major',
      segmentIndex: 0,
      title: 'major',
      subtitle: 'adj. 主要的',
      status: 'pending',
      promptText: null,
      targetWords: ['major'],
      failedDimensions: [],
      bossFailures: 0,
      rewardFailures: 0,
      lastEncounterType: null,
      word: {
        word: 'major',
        phonetic: '/ˈmeɪdʒə(r)/',
        pos: 'adj.',
        definition: '主要的',
        chapter_id: '1',
        chapter_title: 'Chapter 1',
        listening_confusables: [],
        examples: [],
        current_round: 0,
        image: {
          status: 'queued',
          senseKey: 'major',
          url: null,
          alt: 'major',
          styleVersion: 'sense-scene-v2',
          model: 'wanx-v1',
          generatedAt: null,
        },
        dimension_states: {
          recognition: { pass_streak: 0 },
          meaning: { pass_streak: 0 },
          listening: { pass_streak: 0 },
          speaking: { pass_streak: 0 },
          dictation: { pass_streak: 0 },
        },
      },
    } as const

    const { rerender } = render(
      <WordMissionScreen
        node={{ ...baseNode, dimension: 'listening' }}
        bookId="book-1"
        chapterId="1"
        answerInput=""
        selectedChoice={null}
        isSubmitting={false}
        banner={null}
        error={null}
        onAnswerChange={() => {}}
        onSelectChoice={() => {}}
        onSubmitAttempt={vi.fn(() => Promise.resolve())}
        onRefreshAfterSpeaking={() => {}}
      />,
    )

    await user.click(screen.getByRole('button', { name: '播放单词' }))
    expect(playWordAudioMock).toHaveBeenLastCalledWith('major', { playbackSpeed: '1.15', volume: '70' }, undefined, undefined, {
      origin: 'game-mode',
      wordKey: 'major',
    })

    rerender(
      <WordMissionScreen
        node={{ ...baseNode, dimension: 'dictation' }}
        bookId="book-1"
        chapterId="1"
        answerInput=""
        selectedChoice={null}
        isSubmitting={false}
        banner={null}
        error={null}
        onAnswerChange={() => {}}
        onSelectChoice={() => {}}
        onSubmitAttempt={vi.fn(() => Promise.resolve())}
        onRefreshAfterSpeaking={() => {}}
      />,
    )

    await user.click(screen.getByRole('button', { name: '播放单词' }))
    expect(playWordAudioMock).toHaveBeenCalledTimes(2)
    expect(speechSynthesisSpeakMock).not.toHaveBeenCalled()
  })
})
