import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import GameMode from './GameMode'

const fetchGamePracticeStateMock = vi.fn()
const startGamePracticeSessionMock = vi.fn()
const submitWordMasteryAttemptMock = vi.fn()

vi.mock('../../../lib/gamePractice', () => ({
  fetchGamePracticeState: (...args: unknown[]) => fetchGamePracticeStateMock(...args),
  startGamePracticeSession: (...args: unknown[]) => startGamePracticeSessionMock(...args),
  submitWordMasteryAttempt: (...args: unknown[]) => submitWordMasteryAttemptMock(...args),
}))

function buildLevelCards(activeKind: 'spelling' | 'pronunciation' | 'definition' | 'speaking' | 'example' = 'spelling') {
  return [
    { kind: 'spelling', dimension: 'dictation', label: '拼写强化', subtitle: '听音后完整拼出目标词', assetKey: 'spell', step: 1, status: activeKind === 'spelling' ? 'active' : 'ready', passStreak: 0, attemptCount: 0 },
    { kind: 'pronunciation', dimension: 'speaking', label: '发音训练', subtitle: '跟读单词并完成发音判定', assetKey: 'pronunciation', step: 2, status: activeKind === 'pronunciation' ? 'active' : 'ready', passStreak: 0, attemptCount: 0 },
    { kind: 'definition', dimension: 'meaning', label: '释义理解', subtitle: '把词义和场景绑定起来', assetKey: 'definition', step: 3, status: activeKind === 'definition' ? 'active' : 'ready', passStreak: 0, attemptCount: 0 },
    { kind: 'speaking', dimension: 'recognition', label: '口语录音', subtitle: '开口使用目标词完成短句', assetKey: 'speaking', step: 4, status: activeKind === 'speaking' ? 'active' : 'ready', passStreak: 0, attemptCount: 0 },
    { kind: 'example', dimension: 'listening', label: '例句应用', subtitle: '在语境中选出正确用词', assetKey: 'example', step: 5, status: activeKind === 'example' ? 'active' : 'ready', passStreak: 0, attemptCount: 0 },
  ] as const
}

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
      dimension: 'dictation',
      levelKind: 'spelling',
      levelLabel: '拼写强化',
      promptText: null,
      targetWords: ['a couple of'],
      failedDimensions: ['dictation'],
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
      levelKind: 'speaking',
      levelLabel: '口语录音',
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
      levelKind: 'speaking',
      levelLabel: '口语录音',
      promptText: '用 a couple of 造一句更完整的英语表达。',
      targetWords: ['a couple of'],
      failedDimensions: [],
      bossFailures: 0,
      rewardFailures: 0,
      lastEncounterType: null,
      word: null,
    },
    levelCards: buildLevelCards('spelling'),
    rewards: {
      coins: 120,
      diamonds: 0,
      exp: 180,
      stars: 0,
      chest: 'normal',
      bestHits: 0,
    },
    session: {
      status: 'active',
      score: 0,
      hits: 0,
      bestHits: 0,
      hintsRemaining: 2,
      hintUsage: 0,
      energy: 3,
      energyMax: 5,
      nextEnergyAt: null,
      enabledBoosts: { spellingBoost: true, applicationBoost: true },
      resultOverlay: null,
      boostModule: null,
    },
    launcher: {
      lessonId: 'lesson-1',
      title: '第 1 试炼段',
      estimatedMinutes: 5,
      energyCost: 2,
      passScore: 70,
      segmentIndex: 0,
      boosts: { spellingBoost: true, applicationBoost: true },
    },
    animationPayload: {
      sceneTheme: 'spelling',
      mascotState: 'idle',
      feedbackTone: null,
      showResultLayer: false,
    },
    boostModule: null,
    recoveryPanel: {
      queue: [{
        nodeKey: 'word:allow',
        nodeType: 'word',
        title: 'allow',
        subtitle: 'definition / spelling',
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
        subtitle: 'definition / spelling',
        failedDimensions: ['meaning', 'dictation'],
        bossFailures: 0,
        rewardFailures: 0,
        updatedAt: '2026-04-16T08:00:00',
      }],
      resumeNode: {
        nodeKey: 'word:allow',
        nodeType: 'word',
        title: 'allow',
        subtitle: 'definition / spelling',
        failedDimensions: ['meaning', 'dictation'],
        bossFailures: 0,
        rewardFailures: 0,
        updatedAt: '2026-04-16T08:00:00',
      },
    },
  } as const
}

describe('GameMode', () => {
  beforeEach(() => {
    fetchGamePracticeStateMock.mockReset()
    startGamePracticeSessionMock.mockReset()
    submitWordMasteryAttemptMock.mockReset()
  })

  it('renders the active spelling mission without map chrome', async () => {
    fetchGamePracticeStateMock.mockResolvedValue(buildWordState('ready'))

    render(<GameMode bookId="ielts_reading_premium" chapterId="1" />)

    await waitFor(() => expect(fetchGamePracticeStateMock).toHaveBeenCalledWith({
      bookId: 'ielts_reading_premium',
      chapterId: null,
      day: undefined,
    }))
    expect(await screen.findByRole('img', { name: 'a couple of 词义场景' })).toHaveAttribute(
      'src',
      'https://oss.example/a-couple-of.png',
    )
    expect(screen.getAllByText('拼写强化').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: '播放单词' })).toBeInTheDocument()
    expect(screen.queryByText('独立错词体系')).not.toBeInTheDocument()
    expect(screen.queryByRole('img', { name: '五维词关地图' })).not.toBeInTheDocument()
  })

  it('shows the generation placeholder when the scene image is not ready', async () => {
    fetchGamePracticeStateMock.mockResolvedValue(buildWordState('queued'))

    render(<GameMode bookId="ielts_reading_premium" chapterId="1" />)

    expect(await screen.findByText('场景生成中')).toBeInTheDocument()
    expect(screen.getByText('完成当前维度即可点亮关卡。')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: 'a couple of 词义场景' })).not.toBeInTheDocument()
  })

  it('renders the main game map as invisible scene entrances on the map surface', async () => {
    const onEnterMission = vi.fn()
    const activeState = buildWordState('ready')
    fetchGamePracticeStateMock.mockResolvedValue({
      ...activeState,
      session: {
        status: 'launcher',
        score: 0,
        hits: 0,
        bestHits: 0,
        hintsRemaining: 2,
        hintUsage: 0,
        energy: 3,
        energyMax: 5,
        nextEnergyAt: null,
        enabledBoosts: { spellingBoost: true, applicationBoost: true },
        resultOverlay: null,
        boostModule: null,
      },
    })
    startGamePracticeSessionMock.mockResolvedValue({ game_state: activeState })

    render(
      <GameMode
        bookId="ielts_reading_premium"
        chapterId="1"
        surface="map"
        onEnterMission={onEnterMission}
      />,
    )

    expect(await screen.findByRole('img', { name: '五维词关地图' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '返回学习计划' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /开始词关/ })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '进入 1/5 拼写强化' }))

    await waitFor(() => expect(startGamePracticeSessionMock).toHaveBeenCalled())
    expect(onEnterMission).toHaveBeenCalled()
  })

  it('auto-starts a direct mission route instead of rendering the map launcher', async () => {
    const activeState = buildWordState('ready')
    fetchGamePracticeStateMock.mockResolvedValue({
      ...activeState,
      session: {
        ...activeState.session,
        status: 'launcher',
      },
    })
    startGamePracticeSessionMock.mockResolvedValue({ game_state: activeState })

    render(<GameMode bookId="ielts_reading_premium" chapterId="1" />)

    expect(await screen.findByText('正在进入词关...')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: '五维词关地图' })).not.toBeInTheDocument()
    await waitFor(() => expect(startGamePracticeSessionMock).toHaveBeenCalled())
  })

  it('renders the result overlay when the segment settles into result mode', async () => {
    fetchGamePracticeStateMock.mockResolvedValue({
      ...buildWordState('ready'),
      rewards: {
        coins: 280,
        diamonds: 10,
        exp: 210,
        stars: 3,
        chest: 'golden',
        bestHits: 4,
      },
      session: {
        status: 'result',
        score: 96,
        hits: 4,
        bestHits: 4,
        hintsRemaining: 1,
        hintUsage: 1,
        energy: 1,
        energyMax: 5,
        nextEnergyAt: null,
        enabledBoosts: { spellingBoost: true, applicationBoost: true },
        resultOverlay: {
          title: '试炼达线',
          score: 96,
          passed: true,
        },
        boostModule: null,
      },
    })

    render(<GameMode bookId="ielts_reading_premium" chapterId="1" />)

    expect(await screen.findByRole('heading', { name: '试炼达线' })).toBeInTheDocument()
    expect(screen.getByText('通关成功')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '继续词关' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '回到地图' })).toBeInTheDocument()
  })
})
