import type { NavigateFunction } from 'react-router-dom'
import type { PracticeMode, Word } from '../types'
import { buildNextErrorReviewWords, type ErrorReviewRoundResults } from '../../../features/practice/errorReviewSession'
import type { ReviewQueueSummary } from '../../../features/practice/practiceSessionHelpers'
import type { PracticeGroupWindow } from '../../../composables/practice/page/practicePageGrouping'
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
  practiceGroup: PracticeGroupWindow | null
  onContinueReview: () => void
  onContinueErrorReview: () => void
  onContinueChapterGroup: () => void
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
  practiceGroup,
  onContinueReview,
  onContinueErrorReview,
  onContinueChapterGroup,
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
  const chapterGroupRemaining = !errorMode && !reviewMode && !isFollowMode && practiceGroup?.groupSize && practiceGroup.end < practiceGroup.total
    ? practiceGroup.total - practiceGroup.end
    : 0
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
      : chapterGroupRemaining > 0
        ? `当前分组已完成，还可以继续练习 ${chapterGroupRemaining} 个本章单词。`
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
  } else if (chapterGroupRemaining > 0) {
    actions.push({
      label: `继续下一组（还有 ${chapterGroupRemaining} 个）`,
      onClick: onContinueChapterGroup,
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
