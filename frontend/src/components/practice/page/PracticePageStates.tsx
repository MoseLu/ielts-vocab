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
  quickMemoryReviewQueueResolved: boolean
}

export function PracticePageLoadingState({
  navigate,
  mode,
  noListeningPresets,
  reviewMode,
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

  return (
    <div className="practice-session-layout">
      <PageSkeleton variant="practice" />
    </div>
  )
}

interface PracticePageCompletedStateProps {
  navigate: NavigateFunction
  bookId: string | null
  chapterId: string | null
  currentDay?: number
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
  chapterId,
  currentDay,
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

  return (
    <div className="practice-session-layout">
      <div className="practice-complete">
        <div className="complete-emoji" aria-hidden="true">Completed</div>
        <h2>
          {errorMode ? '错词复习完成'
            : reviewMode ? '本批复习完成'
            : bookId ? '本章完成'
            : `Day ${currentDay} 完成`}
        </h2>
        <div className="complete-stats-row">
          <span className="stat-correct">正确 {correctCount}</span>
          <span className="stat-wrong">错误 {wrongCount}</span>
          {sessionDurationText && <span className="stat-duration">本次用时 {sessionDurationText}</span>}
        </div>
        {errorMode && (
          <p className="practice-complete-copy practice-complete-copy--compact">
            第 {errorReviewRound} 轮已完成，剩余 {nextErrorRoundWords.length} 个单词需要继续巩固。
          </p>
        )}
        {errorMode && nextErrorRoundWords.length > 0 && (
          <button className="complete-btn" onClick={onContinueErrorReview}>
            继续第{errorReviewRound + 1}轮（{nextErrorRoundWords.length}词）
          </button>
        )}
        {reviewMode && reviewSummary?.has_more && (
          <button className="complete-btn" onClick={onContinueReview}>
            继续复习{reviewRemaining > 0 ? `（还有 ${reviewRemaining} 个）` : ''}
          </button>
        )}
        <button className="complete-btn" onClick={() => navigate('/plan')}>返回主页</button>
      </div>
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
  markRadioSessionInteraction: () => void
  handleRadioProgressChange: (wordsStudied: number) => void
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
        favoriteSlot={favoriteSlot}
      />
    </div>
  )
}

interface PracticePageQuickMemoryLayoutProps extends SharedLayoutProps {
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
