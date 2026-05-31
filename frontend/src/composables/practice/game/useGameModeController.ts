import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fetchGamePracticeState, startGamePracticeSession, submitWordMasteryAttempt } from '../../../lib/gamePractice'
import type { GameCampaignDimension, GameCampaignState, GameLevelCard, GameLevelKind } from '../../../lib'
import {
  LEVEL_KIND_LABELS,
  LEVEL_KIND_ORDER,
  buildGameScope,
  buildWordPayload,
  getChallengeStep,
  getLevelKind,
} from '../../../features/practice/gameMode/gameData'

export interface BattleBannerState {
  tone: 'success' | 'warning'
  message: string
}

export interface GameAttemptMeta {
  inputMode?: string
  hintUsed?: boolean
  boostType?: string
}

export interface GameModeControllerOptions {
  bookId: string | null
  chapterId: string | null
  currentDay?: number
  surface?: 'map' | 'mission'
  themeId?: string | null
  themeChapterId?: string | null
  task?: string | null
  taskDimension?: GameCampaignDimension | null
  onEnterMission?: () => void
}

const KIND_TO_DIMENSION: Record<GameLevelKind, GameCampaignDimension> = {
  spelling: 'dictation',
  pronunciation: 'speaking',
  definition: 'meaning',
  speaking: 'recognition',
  example: 'listening',
}

function buildFallbackLevelCards(state: GameCampaignState): GameLevelCard[] {
  const currentNode = state.currentNode
  if (!currentNode) return []
  const activeKind = getLevelKind(currentNode)
  const activeStep = Math.max(1, getChallengeStep(currentNode))

  return LEVEL_KIND_ORDER.map((kind, index) => {
    const step = index + 1
    let status: GameLevelCard['status'] = 'locked'
    if (step < activeStep) status = 'passed'
    if (step === activeStep) status = 'active'
    if (currentNode.status === 'pending' && step === activeStep) status = 'pending'
    if (currentNode.status === 'ready' && step === activeStep) status = 'ready'

    return {
      kind,
      dimension: KIND_TO_DIMENSION[kind],
      label: LEVEL_KIND_LABELS[kind],
      subtitle: state.segment.title,
      assetKey: kind,
      step,
      status,
      passStreak: step < activeStep ? 4 : kind === activeKind ? Math.min(4, Math.max(1, state.session?.hits ?? 0)) : 0,
      attemptCount: kind === activeKind ? 1 : 0,
    }
  })
}

export function useGameModeController({
  bookId,
  chapterId,
  currentDay,
  surface = 'mission',
  themeId,
  themeChapterId,
  task,
  taskDimension,
  onEnterMission,
}: GameModeControllerOptions) {
  const [state, setState] = useState<GameCampaignState | null>(null)
  const [answerInput, setAnswerInput] = useState('')
  const [selectedChoice, setSelectedChoice] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isStarting, setIsStarting] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [banner, setBanner] = useState<BattleBannerState | null>(null)
  const [showMapAfterResult, setShowMapAfterResult] = useState(false)
  const bannerTimerRef = useRef<number | null>(null)
  const autoStartedNodeRef = useRef<string | null>(null)
  const scope = useMemo(
    () => buildGameScope({ bookId, chapterId, day: currentDay, themeId, themeChapterId, task, taskDimension }),
    [bookId, chapterId, currentDay, task, taskDimension, themeChapterId, themeId],
  )

  const refreshState = useCallback(async () => {
    setError(null)
    const nextState = await fetchGamePracticeState(scope)
    setState(nextState)
  }, [scope])

  const setBattleBanner = useCallback((nextBanner: BattleBannerState | null) => {
    if (bannerTimerRef.current) {
      window.clearTimeout(bannerTimerRef.current)
      bannerTimerRef.current = null
    }
    setBanner(nextBanner)
    if (nextBanner && typeof window !== 'undefined') {
      bannerTimerRef.current = window.setTimeout(() => {
        setBanner(null)
        bannerTimerRef.current = null
      }, 2200)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    fetchGamePracticeState(scope).then(nextState => {
      if (cancelled) return
      setState(nextState)
    }).catch(loadError => {
      if (cancelled) return
      setError(loadError instanceof Error ? loadError.message : '五维战役状态加载失败')
    }).finally(() => {
      if (!cancelled) setIsLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [scope])

  useEffect(() => {
    setAnswerInput('')
    setSelectedChoice(null)
  }, [state?.currentNode?.nodeKey])

  useEffect(() => {
    return () => {
      if (bannerTimerRef.current) {
        window.clearTimeout(bannerTimerRef.current)
      }
    }
  }, [])

  const startSession = useCallback(async () => {
    setIsStarting(true)
    setError(null)
    try {
      const response = await startGamePracticeSession(scope)
      setState(response.game_state)
      setShowMapAfterResult(false)
      setBattleBanner(null)
      return true
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : '词关启动失败')
      return false
    } finally {
      setIsStarting(false)
    }
  }, [scope, setBattleBanner])

  const enterMission = useCallback(async () => {
    if (!state?.currentNode) return
    if (state.session?.status === 'active') {
      onEnterMission?.()
      return
    }
    const started = await startSession()
    if (started) onEnterMission?.()
  }, [onEnterMission, startSession, state])

  useEffect(() => {
    const nodeKey = state?.currentNode?.nodeKey
    const sessionStatus = state?.session?.status ?? 'active'
    if (surface !== 'mission' || !nodeKey || sessionStatus !== 'launcher' || isStarting) return
    if (autoStartedNodeRef.current === nodeKey) return
    autoStartedNodeRef.current = nodeKey
    void startSession()
  }, [isStarting, startSession, state?.currentNode?.nodeKey, state?.session?.status, surface])

  const submitWordNode = useCallback(async (passed: boolean, meta: GameAttemptMeta = {}) => {
    if (!state?.currentNode || state.currentNode.nodeType !== 'word' || !state.currentNode.word || !state.currentNode.dimension) {
      return
    }
    const levelKind = getLevelKind(state.currentNode)
    setIsSubmitting(true)
    setError(null)
    try {
      const response = await submitWordMasteryAttempt({
        bookId: scope.bookId,
        chapterId: scope.chapterId,
        day: scope.day,
        themeId: scope.themeId,
        themeChapterId: scope.themeChapterId,
        task: scope.task,
        taskDimension: scope.taskDimension,
        nodeType: 'word',
        word: state.currentNode.word.word,
        dimension: state.currentNode.dimension,
        passed,
        sourceMode: 'game',
        entry: scope.task ?? 'game',
        wordPayload: buildWordPayload(state.currentNode.word),
        levelKind,
        hintUsed: Boolean(meta.hintUsed),
        inputMode: meta.inputMode ?? (levelKind === 'spelling' ? 'typing' : 'pointer'),
        boostType: meta.boostType ?? null,
      })
      setState(response.game_state)
      setBattleBanner({
        tone: passed ? 'success' : 'warning',
        message: passed ? '非常棒，当前关已结算，继续推进。' : '这关已记入回流区，稍后还会再出现。',
      })
      setAnswerInput('')
      setSelectedChoice(null)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : '词链提交失败')
    } finally {
      setIsSubmitting(false)
    }
  }, [scope, setBattleBanner, state])

  const submitSpeakingNode = useCallback(async (passed: boolean, meta: GameAttemptMeta = {}) => {
    if (!state?.currentNode || state.currentNode.nodeType === 'word') return
    setIsSubmitting(true)
    setError(null)
    try {
      const response = await submitWordMasteryAttempt({
        bookId: scope.bookId,
        chapterId: scope.chapterId,
        day: scope.day,
        themeId: scope.themeId,
        themeChapterId: scope.themeChapterId,
        task: scope.task,
        taskDimension: scope.taskDimension,
        nodeType: state.currentNode.nodeType,
        segmentIndex: state.currentNode.segmentIndex,
        promptText: state.currentNode.promptText,
        passed,
        sourceMode: 'game',
        levelKind: 'speaking',
        hintUsed: Boolean(meta.hintUsed),
        inputMode: meta.inputMode ?? 'speech',
      })
      setState(response.game_state)
      setBattleBanner({
        tone: passed ? 'success' : 'warning',
        message: passed ? '非常棒，Boss 已结算，战役继续。' : '这关已回流到 Boss 队列，稍后重打。',
      })
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : '口语节点提交失败')
    } finally {
      setIsSubmitting(false)
    }
  }, [scope, setBattleBanner, state])

  const handleWordSpeakingEvaluated = useCallback((passed: boolean) => {
    void refreshState()
    setError(null)
    setBattleBanner({
      tone: passed ? 'success' : 'warning',
      message: passed ? '发音维度已点亮，继续冲击下一关。' : '发音还没稳住，这一维会回到后续链路中。',
    })
  }, [refreshState, setBattleBanner])

  const levelCards = state
    ? state.levelCards.length > 0 ? state.levelCards : buildFallbackLevelCards(state)
    : []

  return {
    answerInput,
    banner,
    enterMission,
    error,
    handleWordSpeakingEvaluated,
    isLoading,
    isStarting,
    isSubmitting,
    levelCards,
    scope,
    selectedChoice,
    setAnswerInput,
    setSelectedChoice,
    setShowMapAfterResult,
    showMapAfterResult,
    startSession,
    state,
    submitSpeakingNode,
    submitWordNode,
  }
}
