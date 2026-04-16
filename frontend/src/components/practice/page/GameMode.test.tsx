import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import GameMode from './GameMode'


const fetchGamePracticeStateMock = vi.fn()
const submitWordMasteryAttemptMock = vi.fn()

vi.mock('../../../lib/gamePractice', () => ({
  fetchGamePracticeState: (...args: unknown[]) => fetchGamePracticeStateMock(...args),
  submitWordMasteryAttempt: (...args: unknown[]) => submitWordMasteryAttemptMock(...args),
}))


function buildState(imageStatus: 'queued' | 'generating' | 'ready' | 'failed') {
  return {
    scope: { bookId: 'ielts_reading_premium', chapterId: '1', day: null },
    activeWord: {
      word: 'control',
      phonetic: '/kənˈtrəʊl/',
      pos: 'n.',
      definition: '控制；管理',
      chapter_id: '1',
      chapter_title: 'Chapter 1',
      overall_status: 'new',
      current_round: 0,
      pending_dimensions: ['recognition', 'meaning', 'listening', 'speaking', 'dictation'],
      listening_confusables: [],
      examples: [{ en: 'The teacher has good control of the class.', zh: '老师很好地控制了课堂。' }],
      dimension_states: {
        recognition: { status: 'not_started', pass_streak: 0, attempt_count: 0 },
        meaning: { status: 'not_started', pass_streak: 0, attempt_count: 0 },
        listening: { status: 'not_started', pass_streak: 0, attempt_count: 0 },
        speaking: { status: 'not_started', pass_streak: 0, attempt_count: 0 },
        dictation: { status: 'not_started', pass_streak: 0, attempt_count: 0 },
      },
      image: {
        status: imageStatus,
        senseKey: 'control-n-abc123-edu-illustration-v1',
        url: imageStatus === 'ready' ? 'https://oss.example/control.png' : null,
        alt: 'control 词义配图',
        styleVersion: 'edu-illustration-v1',
        model: 'wanx-v1',
        generatedAt: imageStatus === 'ready' ? '2026-04-16T08:00:00' : null,
      },
    },
    activeDimension: 'recognition',
    unlockProgress: { completed: 0, total: 5 },
    masteryProgress: { completed: 0, total: 20, currentRound: 0, targetRound: 4 },
    reviewQueue: [],
    pendingDimensions: ['recognition', 'meaning', 'listening', 'speaking', 'dictation'],
    summary: { totalWords: 50, passedWords: 0, unlockedWords: 0, dueWords: 0, newWords: 50 },
  } as const
}


describe('GameMode', () => {
  beforeEach(() => {
    fetchGamePracticeStateMock.mockReset()
    submitWordMasteryAttemptMock.mockReset()
  })

  it('renders the ready image for the active game word', async () => {
    fetchGamePracticeStateMock.mockResolvedValue(buildState('ready'))

    render(
      <GameMode
        bookId="ielts_reading_premium"
        chapterId="1"
        vocabulary={[]}
        playWord={() => {}}
      />,
    )

    const image = await screen.findByRole('img', { name: 'control 词义配图' })
    expect(image).toHaveAttribute('src', 'https://oss.example/control.png')
    expect(screen.getByText('已就绪')).toBeInTheDocument()
  })

  it('shows a generating placeholder when the image is not ready yet', async () => {
    fetchGamePracticeStateMock.mockResolvedValue(buildState('queued'))

    render(
      <GameMode
        bookId="ielts_reading_premium"
        chapterId="1"
        vocabulary={[]}
        playWord={() => {}}
      />,
    )

    expect(await screen.findByText('配图生成中')).toBeInTheDocument()
    expect(screen.getByText('排队中')).toBeInTheDocument()
  })

  it('falls back to a placeholder when image generation failed', async () => {
    fetchGamePracticeStateMock.mockResolvedValue(buildState('failed'))

    render(
      <GameMode
        bookId="ielts_reading_premium"
        chapterId="1"
        vocabulary={[]}
        playWord={() => {}}
      />,
    )

    expect(await screen.findByText('暂时使用占位图，稍后重试')).toBeInTheDocument()
    expect(screen.getByText('稍后重试')).toBeInTheDocument()
  })
})
