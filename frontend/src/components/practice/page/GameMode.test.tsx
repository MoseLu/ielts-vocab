import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import GameMode from './GameMode'

const fetchGamePracticeStateMock = vi.fn()
const submitWordMasteryAttemptMock = vi.fn()

vi.mock('../../../lib/gamePractice', () => ({
  fetchGamePracticeState: (...args: unknown[]) => fetchGamePracticeStateMock(...args),
  submitWordMasteryAttempt: (...args: unknown[]) => submitWordMasteryAttemptMock(...args),
}))

function buildWordState(imageStatus: 'queued' | 'ready' | 'failed') {
  return {
    scope: { bookId: 'ielts_reading_premium', chapterId: null, day: null },
    campaign: {
      title: 'a couple of',
      scopeLabel: '整本词书战役',
      totalWords: 3375,
      passedWords: 0,
      totalSegments: 675,
      clearedSegments: 0,
      currentSegment: 1,
    },
    segment: {
      index: 1,
      title: '第 1 试炼段',
      clearedWords: 0,
      totalWords: 5,
      bossStatus: 'locked',
      rewardStatus: 'locked',
    },
    currentNode: {
      nodeType: 'word',
      nodeKey: 'word:a-couple-of',
      segmentIndex: 0,
      title: 'a couple of',
      subtitle: 'phrase. 两个；几个',
      status: 'pending',
      dimension: 'recognition',
      promptText: null,
      targetWords: ['a couple of'],
      failedDimensions: [],
      bossFailures: 0,
      rewardFailures: 0,
      lastEncounterType: null,
      word: {
        word: 'a couple of',
        phonetic: '/ə ˈkʌp(ə)l əv/',
        pos: 'phrase.',
        definition: '两个；几个',
        chapter_id: '1',
        chapter_title: 'Chapter 1',
        listening_confusables: [],
        examples: [{ en: 'I bought a couple of books.', zh: '我买了几本书。' }],
        overall_status: 'new',
        current_round: 0,
        pending_dimensions: ['recognition', 'meaning', 'listening', 'speaking', 'dictation'],
        dimension_states: {
          recognition: { status: 'not_started', pass_streak: 0, attempt_count: 0 },
          meaning: { status: 'not_started', pass_streak: 0, attempt_count: 0 },
          listening: { status: 'not_started', pass_streak: 0, attempt_count: 0 },
          speaking: { status: 'not_started', pass_streak: 0, attempt_count: 0 },
          dictation: { status: 'not_started', pass_streak: 0, attempt_count: 0 },
        },
        image: {
          status: imageStatus,
          senseKey: 'a-couple-of-phrase-abc123-sense-scene-v2',
          url: imageStatus === 'ready' ? 'https://oss.example/a-couple-of.png' : null,
          alt: 'a couple of 词义场景',
          styleVersion: 'sense-scene-v2',
          model: 'wanx-v1',
          generatedAt: imageStatus === 'ready' ? '2026-04-16T08:00:00' : null,
        },
      },
    },
    nodeType: 'word',
    speakingBoss: {
      nodeType: 'speaking_boss',
      nodeKey: 'speaking_boss:0',
      segmentIndex: 0,
      title: '第 1 段 Boss关',
      subtitle: '段末结算口语试炼',
      status: 'locked',
      dimension: 'speaking',
      promptText: '围绕 a couple of 做一段 30 秒复述。',
      targetWords: ['a couple of', 'ability'],
      failedDimensions: [],
      bossFailures: 0,
      rewardFailures: 0,
      lastEncounterType: null,
      word: null,
    },
    speakingReward: {
      nodeType: 'speaking_reward',
      nodeKey: 'speaking_reward:0',
      segmentIndex: 0,
      title: '第 1 段奖励关',
      subtitle: '非阻塞奖励口语关',
      status: 'locked',
      dimension: 'speaking',
      promptText: '用 a couple of 造一句更完整的英语表达。',
      targetWords: ['a couple of'],
      failedDimensions: [],
      bossFailures: 0,
      rewardFailures: 0,
      lastEncounterType: null,
      word: null,
    },
    recoveryPanel: {
      queue: [{
        nodeKey: 'word:allow',
        nodeType: 'word',
        title: 'allow',
        subtitle: 'meaning / dictation',
        failedDimensions: ['meaning', 'dictation'],
        bossFailures: 0,
        rewardFailures: 0,
        updatedAt: '2026-04-16T08:00:00',
      }],
      bossQueue: [],
      recentMisses: [{
        nodeKey: 'word:allow',
        nodeType: 'word',
        title: 'allow',
        subtitle: 'meaning / dictation',
        failedDimensions: ['meaning', 'dictation'],
        bossFailures: 0,
        rewardFailures: 0,
        updatedAt: '2026-04-16T08:00:00',
      }],
      resumeNode: {
        nodeKey: 'word:allow',
        nodeType: 'word',
        title: 'allow',
        subtitle: 'meaning / dictation',
        failedDimensions: ['meaning', 'dictation'],
        bossFailures: 0,
        rewardFailures: 0,
        updatedAt: '2026-04-16T08:00:00',
      },
    },
  } as const
}

function buildBossState() {
  return {
    ...buildWordState('queued'),
    currentNode: {
      nodeType: 'speaking_boss',
      nodeKey: 'speaking_boss:0',
      segmentIndex: 0,
      title: '第 1 段 Boss关',
      subtitle: '段末结算口语试炼',
      status: 'pending',
      dimension: 'speaking',
      promptText: '围绕 a couple of、ability 做一段 30 秒复述，要求自然串联这些词。',
      targetWords: ['a couple of', 'ability'],
      failedDimensions: [],
      bossFailures: 2,
      rewardFailures: 0,
      lastEncounterType: 'speaking_boss',
      word: null,
    },
    nodeType: 'speaking_boss',
    segment: {
      index: 1,
      title: '第 1 试炼段',
      clearedWords: 5,
      totalWords: 5,
      bossStatus: 'pending',
      rewardStatus: 'locked',
    },
    speakingBoss: {
      nodeType: 'speaking_boss',
      nodeKey: 'speaking_boss:0',
      segmentIndex: 0,
      title: '第 1 段 Boss关',
      subtitle: '段末结算口语试炼',
      status: 'pending',
      dimension: 'speaking',
      promptText: '围绕 a couple of、ability 做一段 30 秒复述，要求自然串联这些词。',
      targetWords: ['a couple of', 'ability'],
      failedDimensions: [],
      bossFailures: 2,
      rewardFailures: 0,
      lastEncounterType: 'speaking_boss',
      word: null,
    },
    recoveryPanel: {
      queue: [],
      bossQueue: [{
        nodeKey: 'speaking_boss:0',
        nodeType: 'speaking_boss',
        title: '第 1 段',
        subtitle: 'speaking_boss',
        failedDimensions: [],
        bossFailures: 2,
        rewardFailures: 0,
        updatedAt: '2026-04-16T08:00:00',
      }],
      recentMisses: [],
      resumeNode: {
        nodeKey: 'speaking_boss:0',
        nodeType: 'speaking_boss',
        title: '第 1 段',
        subtitle: 'speaking_boss',
        failedDimensions: [],
        bossFailures: 2,
        rewardFailures: 0,
        updatedAt: '2026-04-16T08:00:00',
      },
    },
  } as const
}

describe('GameMode', () => {
  beforeEach(() => {
    fetchGamePracticeStateMock.mockReset()
    submitWordMasteryAttemptMock.mockReset()
  })

  it('renders the ready scene card for the active word node', async () => {
    fetchGamePracticeStateMock.mockResolvedValue(buildWordState('ready'))

    render(
      <GameMode
        bookId="ielts_reading_premium"
        chapterId="1"
      />,
    )

    await waitFor(() => expect(fetchGamePracticeStateMock).toHaveBeenCalledWith({
      bookId: 'ielts_reading_premium',
      chapterId: null,
      day: undefined,
    }))
    expect(await screen.findByRole('img', { name: 'a couple of 词义场景' })).toHaveAttribute(
      'src',
      'https://oss.example/a-couple-of.png',
    )
    expect(screen.getByText('独立错词体系')).toBeInTheDocument()
    expect(screen.getByText('整本词书 0/3375 已通关')).toBeInTheDocument()
    expect(screen.queryByText('待复习队列')).not.toBeInTheDocument()
    expect(screen.queryByText('已就绪')).not.toBeInTheDocument()
  })

  it('shows the queued placeholder when the scene card is still generating', async () => {
    fetchGamePracticeStateMock.mockResolvedValue(buildWordState('queued'))

    render(
      <GameMode
        bookId="ielts_reading_premium"
        chapterId="1"
      />,
    )

    expect(await screen.findByText('雷达扫描中')).toBeInTheDocument()
    expect(screen.getByText('排队生成')).toBeInTheDocument()
    expect(screen.getByText('场景构建中，稍后会补上更贴词义的画面。')).toBeInTheDocument()
  })

  it('renders the boss mission card when the campaign advances to a speaking boss node', async () => {
    fetchGamePracticeStateMock.mockResolvedValue(buildBossState())

    render(
      <GameMode
        bookId="ielts_reading_premium"
        chapterId="1"
      />,
    )

    expect((await screen.findAllByText('口语 Boss')).length).toBeGreaterThan(0)
    expect(screen.getByText('闯过 Boss')).toBeInTheDocument()
    expect(screen.getByText('稍后重打')).toBeInTheDocument()
    expect(screen.getByText('Boss 重打队列')).toBeInTheDocument()
    expect(screen.getAllByText('a couple of').length).toBeGreaterThan(0)
  })
})
