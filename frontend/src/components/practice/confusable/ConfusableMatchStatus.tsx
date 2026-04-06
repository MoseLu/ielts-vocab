import { PageSkeleton } from '../../ui'

export function ConfusableMatchLoadingState() {
  return (
    <div className="practice-session-layout">
      <PageSkeleton variant="practice" />
    </div>
  )
}

export function ConfusableMatchErrorState({
  error,
  onBack,
}: {
  error: string
  onBack: () => void
}) {
  return (
    <div className="practice-session-layout confusable-shell">
      <div className="practice-complete confusable-empty">
        <div className="complete-emoji" aria-hidden="true">!</div>
        <h2>无法进入辨析模式</h2>
        <p>{error}</p>
        <button className="complete-btn" onClick={onBack}>返回词书</button>
      </div>
    </div>
  )
}

export function ConfusableMatchCompletedState({
  chapterTitle,
  correctCount,
  wrongCount,
  onReplay,
  onBack,
}: {
  chapterTitle: string
  correctCount: number
  wrongCount: number
  onReplay: () => void
  onBack: () => void
}) {
  return (
    <div className="practice-session-layout confusable-shell">
      <div className="practice-complete confusable-empty">
        <div className="complete-emoji" aria-hidden="true">✓</div>
        <h2>{chapterTitle || '本章'}已完成</h2>
        <div className="complete-stats-row">
          <span className="stat-correct">配对成功 {correctCount}</span>
          <span className="stat-wrong">误连 {wrongCount}</span>
        </div>
        <button className="complete-btn" onClick={onReplay}>再来一轮</button>
        <button className="complete-btn" onClick={onBack}>返回词书</button>
      </div>
    </div>
  )
}

export function ConfusableMatchWarningOverlay({ warningText }: { warningText: string }) {
  return (
    <div className="confusable-warning-overlay" role="alert" aria-live="assertive">
      <div className="confusable-warning-card">
        <span className="confusable-warning-label">配对错误</span>
        <strong>{warningText}</strong>
        <span>当前小棋盘里的两组词很接近，再看一眼再连。</span>
      </div>
    </div>
  )
}
