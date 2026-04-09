import { PageSkeleton } from '../../ui'
import { PracticeRoundSummary } from '../page/PracticeRoundSummary'

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
  const totalAttempts = correctCount + wrongCount
  const accuracy = totalAttempts > 0 ? `${Math.round((correctCount / totalAttempts) * 100)}%` : '0%'

  return (
    <div className="practice-session-layout confusable-shell">
      <PracticeRoundSummary
        contextLabel={chapterTitle || '本章辨析'}
        stats={[
          { value: correctCount, label: '配对成功', tone: 'accent' },
          { value: wrongCount, label: '误连', tone: 'error' },
          { value: accuracy, label: '正确率', tone: 'warning' },
        ]}
        note="当前章节的辨析配对已经完成。"
        actions={[
          { label: '再来一轮', onClick: onReplay, tone: 'primary' },
          { label: '返回词书', onClick: onBack, tone: 'secondary' },
        ]}
        className="practice-round-summary--confusable"
      />
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
