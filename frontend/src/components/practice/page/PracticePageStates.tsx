import type { NavigateFunction } from 'react-router-dom'
import type { ReactNode } from 'react'
import type { AppSettings, Chapter, PracticeMode, Word, WordListActionControls, WordStatuses } from '../types'
import PracticeControlBar from '../PracticeControlBar'
import WordListPanel from '../WordListPanel'
import RadioMode from '../RadioMode'
import QuickMemoryMode from '../QuickMemoryMode'
import SettingsPanel from '../../settings/SettingsPanel'
import { PageSkeleton } from '../../ui'
import { buildNextErrorReviewWords, type ErrorReviewRoundResults } from '../errorReviewSession'
import { PracticeRoundSummary } from './PracticeRoundSummary'
function formatSessionDuration(seconds: number): string {
  const safeSeconds = Math.max(0, Math.round(seconds))
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  const remainingSeconds = safeSeconds % 60
  if (hours > 0) return minutes > 0 ? `${hours}小时${minutes}分` : `${hours}小时`
  if (minutes > 0) return remainingSeconds > 0 ? `${minutes}分${remainingSeconds}秒` : `${minutes}分`
  return `${remainingSeconds}秒`
}
interface ReviewQueueSummary {
  due_count: number
  upcoming_count: number
  returned_count: number
  review_window_days: number
  offset: number
  limit: number | null
  total_count: number
  has_more: boolean
  next_offset: number | null
}
interface PracticePageLoadingStateProps {
  navigate: NavigateFunction
  mode?: PracticeMode
  noListeningPresets: boolean
  reviewMode: boolean
  reviewQueueError: string | null
  quickMemoryReviewQueueResolved: boolean
}
export function PracticePageLoadingState({
  navigate,
  mode,
  noListeningPresets,
  reviewMode,
  reviewQueueError,
  quickMemoryReviewQueueResolved,
}: PracticePageLoadingStateProps) {
  if (mode === 'listening' && noListeningPresets) {
    return (
      <div className="practice-session-layout">
        <div className="practice-complete">
          <div className="complete-emoji" aria-hidden="true">!</div>
          <h2>当前词表暂无可用听音辨析</h2>
          <p className="practice-complete-copy">
            这个范围内的单词还没有准备好完整的听音干扰组，请切换到其他词书、章节或练习模式。
          </p>
          <button className="complete-btn" onClick={() => navigate('/plan')}>返回主页</button>
        </div>
      </div>
    )
  }
  if (reviewMode && mode === 'quickmemory' && reviewQueueError) {
    return (
      <div className="practice-session-layout">
        <div className="practice-complete">
          <div className="complete-emoji" aria-hidden="true">!</div>
          <h2>到期复习暂时打不开</h2>
          <p className="practice-complete-copy">{reviewQueueError}</p>
          <button className="complete-btn" onClick={() => window.location.reload()}>重新加载</button>
        </div>
      </div>
    )
  }
  if (reviewMode && mode === 'quickmemory' && quickMemoryReviewQueueResolved) {
    return (
      <div className="practice-session-layout">
        <div className="practice-complete">
          <div className="complete-emoji" aria-hidden="true">✓</div>
          <h2>暂无待复习的单词</h2>
          <p className="practice-complete-copy">
            目前没有到期需要复习的单词，继续学习新词后再来！
          </p>
          <button className="complete-btn" onClick={() => navigate('/plan')}>返回主页</button>
        </div>
      </div>
    )
  }
  return <div className="practice-session-layout"><PageSkeleton variant="practice" /></div>
}
interface PracticePageCompletedStateProps {
  navigate: NavigateFunction
  bookId: string | null
  chapterId: string | null
  currentDay?: number
  mode?: PracticeMode
  correctCount: number
  wrongCount: number
  errorMode: boolean
  errorReviewRound: number
  reviewMode: boolean
  sessionDurationSeconds?: number | null
  reviewSummary: ReviewQueueSummary | null
  vocabulary: Word[]
  errorRoundResults: ErrorReviewRoundResults
  onContinueReview: () => void
  onContinueErrorReview: () => void
}
export function PracticePageCompletedState({
  navigate,
  bookId,
  currentDay,
  mode,
  correctCount,
  wrongCount,
  errorMode,
  errorReviewRound,
  reviewMode,
  sessionDurationSeconds,
  reviewSummary,
  vocabulary,
  errorRoundResults,
  onContinueReview,
  onContinueErrorReview,
}: PracticePageCompletedStateProps) {
  const reviewRemaining = reviewSummary?.has_more
    ? reviewSummary.total_count - reviewSummary.offset - reviewSummary.returned_count
    : 0
  const nextErrorRoundWords = errorMode ? buildNextErrorReviewWords(vocabulary, errorRoundResults) : []
  const sessionDurationText = sessionDurationSeconds != null
    ? formatSessionDuration(sessionDurationSeconds)
    : null
  const totalAnswered = correctCount + wrongCount
  const accuracy = totalAnswered > 0 ? `${Math.round((correctCount / totalAnswered) * 100)}%` : '0%'
  const isFollowMode = mode === 'follow'
  const contextLabel = isFollowMode
    ? '跟读练习'
    : errorMode
    ? '错词复习'
    : reviewMode
      ? '到期复习'
      : bookId
        ? '本章练习'
        : currentDay != null
          ? `Day ${currentDay}`
          : '本轮练习'
  const note = isFollowMode
    ? '跟读模式只记录学习时长，不计入测试正确率、错词或掌握度。'
    : errorMode
    ? `第 ${errorReviewRound} 轮已完成，剩余 ${nextErrorRoundWords.length} 个单词需要继续巩固。`
    : reviewMode
      ? (reviewSummary?.has_more
          ? `当前批次已完成，还可以继续复习 ${Math.max(reviewRemaining, 0)} 个到期单词。`
          : '当前批次的到期单词已经清完。')
      : null
  const actions = []

  if (errorMode && nextErrorRoundWords.length > 0) {
    actions.push({
      label: `继续第${errorReviewRound + 1}轮`,
      onClick: onContinueErrorReview,
      tone: 'primary' as const,
    })
  } else if (reviewMode && reviewSummary?.has_more) {
    actions.push({
      label: `继续复习${reviewRemaining > 0 ? `（还有 ${reviewRemaining} 个）` : ''}`,
      onClick: onContinueReview,
      tone: 'primary' as const,
    })
  }
  actions.push({
    label: '返回主页',
    onClick: () => navigate('/plan'),
    tone: actions.length > 0 ? 'secondary' as const : 'primary' as const,
  })

  return (
    <div className="practice-session-layout">
      <PracticeRoundSummary
        contextLabel={contextLabel}
        stats={[
          ...(!isFollowMode ? [
            { value: correctCount, label: '正确', tone: 'accent' as const },
            { value: wrongCount, label: '错误', tone: 'error' as const },
            { value: accuracy, label: '正确率', tone: 'warning' as const },
          ] : []),
          ...(sessionDurationText ? [{ value: sessionDurationText, label: '本次用时', tone: 'neutral' as const }] : []),
        ]}
        note={note}
        chipTitle={errorMode && nextErrorRoundWords.length > 0 ? '继续巩固' : undefined}
        chips={errorMode ? nextErrorRoundWords.slice(0, 18).map(word => word.word) : undefined}
        actions={actions}
      />
    </div>
  )
}
export function PracticePagePauseOverlay({
  isPaused,
  mode,
  queue,
  queueIndex,
  correctCount,
  wrongCount,
  onResume,
  onExit,
}: {
  isPaused: boolean
  mode?: PracticeMode
  queue: number[]
  queueIndex: number
  correctCount: number
  wrongCount: number
  onResume: () => void
  onExit: () => void
}) {
  if (!isPaused) return null
  return (
    <div className="practice-pause-overlay">
      <div className="practice-pause-card">
        <div className="practice-pause-icon-wrap">
          <svg viewBox="0 0 24 24" fill="currentColor" width="34" height="34">
            <rect x="5" y="3" width="4" height="18" rx="1.5" />
            <rect x="15" y="3" width="4" height="18" rx="1.5" />
          </svg>
        </div>
        <h2 className="practice-pause-title">练习已暂停</h2>
        {mode !== 'radio' && (
          <div className="practice-pause-stats">
            <span className="practice-pause-stat">
              {mode === 'quickmemory'
                ? <>共 <strong>{queue.length}</strong> 个单词</>
                : <>第 <strong>{queueIndex}</strong> / {queue.length} 个单词</>}
            </span>
            {mode !== 'quickmemory' && (correctCount > 0 || wrongCount > 0) && (
              <span className="practice-pause-sub">
                <span className="practice-pause-correct">正确 {correctCount}</span>
                <span className="practice-pause-wrong">错误 {wrongCount}</span>
              </span>
            )}
          </div>
        )}
        <p className="practice-pause-hint">进度已自动保存。退出后再次回到本章节，仍可从这里继续。</p>
        <div className="practice-pause-actions">
          <button className="practice-pause-resume" onClick={onResume}>继续练习</button>
          <button className="practice-pause-exit" onClick={onExit}>退出到主页</button>
        </div>
      </div>
    </div>
  )
}
interface SharedLayoutProps {
  mode?: PracticeMode
  currentDay?: number
  practiceBookId: string | null
  practiceChapterId: string | null
  errorMode: boolean
  vocabulary: Word[]
  currentChapterTitle: string
  bookChapters: Chapter[]
  showWordList: boolean
  showPracticeSettings: boolean
  onWordListToggle: () => void
  onSettingsToggle: () => void
  onModeChange: (mode: PracticeMode) => void
  onDayChange?: (day: number) => void
  navigate: NavigateFunction
  buildChapterPath?: (chapterId: string | number) => string
  onExitHome: () => void
  favoriteSlot?: ReactNode
  speakingSlot?: ReactNode
  wordListActionControls?: WordListActionControls
}
interface PracticePageRadioLayoutProps extends SharedLayoutProps {
  queue: number[]
  radioIndex: number
  wordStatuses: WordStatuses
  settings: AppSettings
  radioQuickSettings: {
    playbackSpeed: string
    playbackCount: string
    loopMode: boolean
    interval: string
  }
  onRadioSettingChange: (key: 'playbackSpeed' | 'playbackCount' | 'loopMode' | 'interval', value: string | boolean) => void
  onIndexChange: (index: number) => void
  markRadioSessionInteraction: () => Promise<void>
  handleRadioProgressChange: (wordsStudied: number) => void
  isCurrentSessionActive: (at?: number) => boolean
}
export function PracticePageRadioLayout(props: PracticePageRadioLayoutProps) {
  const {
    mode,
    currentDay,
    practiceBookId,
    practiceChapterId,
    errorMode,
    vocabulary,
    currentChapterTitle,
    bookChapters,
    showWordList,
    showPracticeSettings,
    onWordListToggle,
    onSettingsToggle,
    onModeChange,
    onDayChange,
    navigate,
    buildChapterPath,
    onExitHome,
    favoriteSlot,
    speakingSlot,
    wordListActionControls,
    queue,
    radioIndex,
    wordStatuses,
    settings,
    radioQuickSettings,
    onRadioSettingChange,
    onIndexChange,
    markRadioSessionInteraction,
    handleRadioProgressChange,
    isCurrentSessionActive,
  } = props
  return (
    <div className="practice-session-layout">
      <PracticeControlBar
        mode={mode}
        currentDay={currentDay}
        bookId={practiceBookId}
        chapterId={practiceChapterId}
        errorMode={errorMode}
        vocabularyLength={vocabulary.length}
        currentChapterTitle={currentChapterTitle}
        bookChapters={bookChapters}
        showWordList={showWordList}
        showPracticeSettings={showPracticeSettings}
        onWordListToggle={onWordListToggle}
        onSettingsToggle={onSettingsToggle}
        onModeChange={onModeChange}
        onDayChange={onDayChange}
        onNavigate={navigate}
        buildChapterPath={buildChapterPath}
        onExitHome={onExitHome}
        radioQuickSettings={radioQuickSettings}
        onRadioSettingChange={onRadioSettingChange}
      />
      <WordListPanel
        show={showWordList}
        vocabulary={vocabulary}
        queue={queue}
        queueIndex={radioIndex}
        wordStatuses={wordStatuses}
        wordActionControls={wordListActionControls}
        onClose={onWordListToggle}
      />
      {showPracticeSettings && (
        <SettingsPanel showSettings={showPracticeSettings} onClose={onSettingsToggle} />
      )}
      <RadioMode
        vocabulary={vocabulary}
        queue={queue}
        radioIndex={radioIndex}
        showSettings={false}
        settings={settings}
        onRadioSkipPrev={() => {}}
        onRadioSkipNext={() => {}}
        onRadioPause={() => {}}
        onRadioResume={() => {}}
        onRadioRestart={() => {}}
        onRadioStop={() => {}}
        onNavigate={navigate}
        onCloseSettings={onSettingsToggle}
        onModeChange={onModeChange}
        onIndexChange={onIndexChange}
        onSessionInteraction={markRadioSessionInteraction}
        onProgressChange={handleRadioProgressChange}
        isSessionActive={isCurrentSessionActive}
        favoriteSlot={favoriteSlot}
        speakingSlot={speakingSlot}
      />
    </div>
  )
}
interface PracticePageQuickMemoryLayoutProps extends Omit<SharedLayoutProps, 'speakingSlot'> {
  queue: number[]
  queueIndex: number
  wordStatuses: WordStatuses
  settings: AppSettings
  reviewMode: boolean
  reviewOffset: number
  reviewHasMore: boolean
  onContinueReview?: () => void
  onWrongWord: (word: Word) => void
  onQuickMemoryRecordChange: (word: Word, record: {
    status: 'known' | 'unknown'
    firstSeen: number
    lastSeen: number
    knownCount: number
    unknownCount: number
    nextReview: number
    fuzzyCount: number
  }) => void
  initialIndex?: number
  onIndexChange?: (index: number) => void
}
export function PracticePageQuickMemoryLayout(props: PracticePageQuickMemoryLayoutProps) {
  const {
    mode,
    currentDay,
    practiceBookId,
    practiceChapterId,
    errorMode,
    vocabulary,
    currentChapterTitle,
    bookChapters,
    showWordList,
    showPracticeSettings,
    onWordListToggle,
    onSettingsToggle,
    onModeChange,
    onDayChange,
    navigate,
    buildChapterPath,
    onExitHome,
    favoriteSlot,
    wordListActionControls,
    queue,
    queueIndex,
    wordStatuses,
    settings,
    reviewMode,
    reviewOffset,
    reviewHasMore,
    onContinueReview,
    onWrongWord,
    onQuickMemoryRecordChange,
    initialIndex,
    onIndexChange,
  } = props
  return (
    <div className="practice-session-layout">
      <PracticeControlBar
        mode={mode}
        currentDay={currentDay}
        bookId={practiceBookId}
        chapterId={practiceChapterId}
        errorMode={errorMode}
        vocabularyLength={vocabulary.length}
        currentChapterTitle={currentChapterTitle}
        bookChapters={bookChapters}
        showWordList={showWordList}
        showPracticeSettings={showPracticeSettings}
        onWordListToggle={onWordListToggle}
        onSettingsToggle={onSettingsToggle}
        onModeChange={onModeChange}
        onDayChange={onDayChange}
        onNavigate={navigate}
        buildChapterPath={buildChapterPath}
        onExitHome={onExitHome}
      />
      <WordListPanel
        show={showWordList}
        vocabulary={vocabulary}
        queue={queue}
        queueIndex={queueIndex}
        wordStatuses={wordStatuses}
        wordActionControls={wordListActionControls}
        onClose={onWordListToggle}
      />
      {showPracticeSettings && (
        <SettingsPanel showSettings={showPracticeSettings} onClose={onSettingsToggle} />
      )}
      <QuickMemoryMode
        key={`quickmemory-${practiceBookId ?? 'day'}-${practiceChapterId ?? currentDay ?? 'all'}-${errorMode ? 'errors' : 'normal'}-${reviewMode ? `review-${reviewOffset}` : 'default'}`}
        vocabulary={vocabulary}
        queue={queue}
        settings={settings}
        bookId={practiceBookId}
        chapterId={practiceChapterId}
        bookChapters={bookChapters}
        reviewMode={reviewMode}
        errorMode={errorMode}
        reviewHasMore={reviewMode ? reviewHasMore : false}
        onContinueReview={reviewMode ? onContinueReview : undefined}
        buildChapterPath={buildChapterPath}
        onModeChange={onModeChange}
        onNavigate={navigate}
        onWrongWord={onWrongWord}
        onQuickMemoryRecordChange={onQuickMemoryRecordChange}
        initialIndex={initialIndex}
        onIndexChange={onIndexChange}
        favoriteSlot={favoriteSlot}
      />
    </div>
  )
}
