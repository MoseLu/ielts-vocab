import type { GameCampaignDimension } from '../../../lib'
import { useGameModeController } from '../../../composables/practice/game/useGameModeController'
import { GameMapShell } from './game-mode/GameMapShell'
import { GameResultOverlay } from './game-mode/GameResultOverlay'
import { Loading } from '../../ui'
import {
  SpeakingMissionScreen,
  WordMissionScreen,
} from './GameModeSections'

interface GameModeProps {
  bookId: string | null
  chapterId: string | null
  currentDay?: number
  surface?: 'map' | 'mission'
  themeId?: string | null
  themeChapterId?: string | null
  task?: string | null
  taskDimension?: GameCampaignDimension | null
  onBackToPlan?: () => void
  onEnterMission?: () => void
  onExitToMap?: () => void
  onSelectThemeChapter?: (chapterId: string, page: number) => void
}

export default function GameMode({
  bookId,
  chapterId,
  currentDay,
  surface = 'mission',
  themeId,
  themeChapterId,
  task,
  taskDimension,
  onBackToPlan,
  onEnterMission,
  onExitToMap,
  onSelectThemeChapter,
}: GameModeProps) {
  const {
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
  } = useGameModeController({
    bookId,
    chapterId,
    currentDay,
    surface,
    themeId,
    themeChapterId,
    task,
    taskDimension,
    onEnterMission,
  })

  if (isLoading) {
    return <Loading fullScreen />
  }

  if (error && !state) {
    return <section className="practice-game-mode practice-game-mode--error">{error}</section>
  }

  if (!state?.currentNode) {
    return (
      <section className="practice-game-mode practice-game-mode--done">
        <strong>整本战役已打通。</strong>
        <span>五维链、Boss 关和奖励关都已完成。</span>
      </section>
    )
  }

  const currentNode = state.currentNode
  const activeWord = currentNode.word
  const sessionStatus = state.session?.status ?? 'active'

  if (surface === 'map') {
    return (
      <section className="practice-game-mode practice-game-mode--map">
        <GameMapShell
          state={state}
          levelCards={levelCards}
          isStarting={isStarting}
          error={error}
          onStart={() => void enterMission()}
          onBackToPlan={onBackToPlan}
          onSelectThemeChapter={onSelectThemeChapter}
        />
      </section>
    )
  }

  if (sessionStatus === 'result' && !showMapAfterResult) {
    return (
      <section className="practice-game-mode">
        <GameResultOverlay
          state={state}
          onContinue={() => void startSession()}
          onBackToMap={() => {
            if (onExitToMap) {
              onExitToMap()
              return
            }
            setShowMapAfterResult(true)
          }}
        />
      </section>
    )
  }

  if (sessionStatus === 'launcher') {
    return <Loading fullScreen />
  }

  if (showMapAfterResult) {
    return (
      <GameMapShell
        state={state}
        levelCards={levelCards}
        isStarting={isStarting}
        error={error}
        onStart={() => void startSession()}
        onBackToPlan={onBackToPlan}
        onSelectThemeChapter={onSelectThemeChapter}
      />
    )
  }

  return (
    <section className="practice-game-mode practice-game-mode--mission">
      <div className="practice-game-mode__mission">
        {currentNode.nodeType === 'word' && activeWord ? (
          <WordMissionScreen
            node={currentNode}
            bookId={scope.bookId}
            chapterId={scope.chapterId}
            answerInput={answerInput}
            selectedChoice={selectedChoice}
            isSubmitting={isSubmitting}
            banner={banner}
            error={error}
            forceRefillLayout={state.taskFocus?.task === 'error-review'}
            onAnswerChange={setAnswerInput}
            onSelectChoice={setSelectedChoice}
            onSubmitAttempt={submitWordNode}
            onRefreshAfterSpeaking={handleWordSpeakingEvaluated}
            onExitToMap={onExitToMap}
          />
        ) : (
          <SpeakingMissionScreen
            node={currentNode}
            isSubmitting={isSubmitting}
            banner={banner}
            error={error}
            onSubmitNode={submitSpeakingNode}
            onExitToMap={onExitToMap}
          />
        )}
      </div>
    </section>
  )
}
