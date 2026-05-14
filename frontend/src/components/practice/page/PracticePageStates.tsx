import type { NavigateFunction } from 'react-router-dom'
import type { ReactNode } from 'react'
import type { AppSettings, Chapter, PracticeMode, Word, WordListActionControls, WordStatuses } from '../types'
import PracticeControlBar from '../PracticeControlBar'
import WordListPanel from '../WordListPanel'
import RadioMode from '../RadioMode'
import QuickMemoryMode from '../QuickMemoryMode'
import SettingsPanel from '../../settings/SettingsPanel'
import type { PracticeGroupWindow } from '../../../composables/practice/page/practicePageGrouping'
export { PracticePageCompletedState } from './PracticePageCompletedState'
export { PracticePageLoadingState } from './PracticePageLoadingState'
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
  chapterGroup?: PracticeGroupWindow | null
  chapterQueueWords?: string[]
  onContinueChapterGroup?: () => void
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
    chapterGroup,
    chapterQueueWords,
    onContinueChapterGroup,
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
        key={`quickmemory-${practiceBookId ?? 'day'}-${practiceChapterId ?? currentDay ?? 'all'}-${errorMode ? 'errors' : 'normal'}-${reviewMode ? `review-${reviewOffset}` : `group-${chapterGroup?.start ?? 0}-${chapterGroup?.end ?? queue.length}`}`}
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
        chapterGroup={chapterGroup}
        chapterQueueWords={chapterQueueWords}
        onContinueChapterGroup={onContinueChapterGroup}
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
