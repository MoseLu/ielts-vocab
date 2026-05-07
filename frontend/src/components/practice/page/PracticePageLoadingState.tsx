import type { NavigateFunction } from 'react-router-dom'
import type { ReactNode } from 'react'
import PracticeControlBar from '../PracticeControlBar'
import type { Chapter, PracticeMode } from '../types'
import { PageSkeleton } from '../../ui'

interface PracticePageLoadingStateProps {
  navigate: NavigateFunction
  currentDay?: number
  mode?: PracticeMode
  bookId?: string | null
  chapterId?: string | null
  errorMode?: boolean
  currentChapterTitle?: string
  bookChapters?: Chapter[]
  onModeChange?: (mode: PracticeMode) => void
  onDayChange?: (day: number) => void
  buildChapterPath?: (chapterId: string | number) => string
  noListeningPresets: boolean
  reviewMode: boolean
  reviewQueueError: string | null
  quickMemoryReviewQueueResolved: boolean
}

function PracticeLoadingShell({
  navigate,
  currentDay,
  mode,
  bookId,
  chapterId,
  errorMode,
  currentChapterTitle,
  bookChapters,
  onModeChange,
  onDayChange,
  buildChapterPath,
  children,
}: PracticePageLoadingStateProps & { children: ReactNode }) {
  const safeMode = mode ?? 'smart'
  return (
    <div className="practice-session-layout">
      <PracticeControlBar
        mode={safeMode}
        currentDay={currentDay}
        bookId={bookId ?? null}
        chapterId={chapterId ?? null}
        errorMode={Boolean(errorMode)}
        vocabularyLength={0}
        currentChapterTitle={currentChapterTitle ?? ''}
        bookChapters={bookChapters ?? []}
        showWordList={false}
        showPracticeSettings={false}
        onWordListToggle={() => {}}
        onSettingsToggle={() => {}}
        onModeChange={onModeChange ?? (() => {})}
        onDayChange={onDayChange}
        onNavigate={navigate}
        buildChapterPath={buildChapterPath}
        onExitHome={() => navigate('/plan')}
        showWordListAction={false}
        showSettingsAction={false}
      />
      {children}
    </div>
  )
}

export function PracticePageLoadingState(props: PracticePageLoadingStateProps) {
  const {
    navigate,
    mode,
    noListeningPresets,
    reviewMode,
    reviewQueueError,
    quickMemoryReviewQueueResolved,
  } = props
  if (mode === 'listening' && noListeningPresets) {
    return (
      <PracticeLoadingShell {...props}>
        <div className="practice-complete">
          <div className="complete-emoji" aria-hidden="true">!</div>
          <h2>当前词表暂无可用听音辨析</h2>
          <p className="practice-complete-copy">
            这个范围内的单词还没有准备好完整的听音干扰组，请切换到其他词书、章节或练习模式。
          </p>
          <button className="complete-btn" onClick={() => navigate('/plan')}>返回主页</button>
        </div>
      </PracticeLoadingShell>
    )
  }
  if (reviewMode && reviewQueueError) {
    return (
      <PracticeLoadingShell {...props}>
        <div className="practice-complete">
          <div className="complete-emoji" aria-hidden="true">!</div>
          <h2>到期复习暂时打不开</h2>
          <p className="practice-complete-copy">{reviewQueueError}</p>
          <button className="complete-btn" onClick={() => window.location.reload()}>重新加载</button>
        </div>
      </PracticeLoadingShell>
    )
  }
  if (reviewMode && quickMemoryReviewQueueResolved) {
    return (
      <PracticeLoadingShell {...props}>
        <div className="practice-complete">
          <div className="complete-emoji" aria-hidden="true">✓</div>
          <h2>暂无待复习的单词</h2>
          <p className="practice-complete-copy">
            目前没有到期需要复习的单词，继续学习新词后再来！
          </p>
          <button className="complete-btn" onClick={() => navigate('/plan')}>返回主页</button>
        </div>
      </PracticeLoadingShell>
    )
  }
  return <PracticeLoadingShell {...props}><PageSkeleton variant="practice" /></PracticeLoadingShell>
}
