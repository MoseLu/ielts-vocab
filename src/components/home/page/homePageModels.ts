import type { Book, BookProgress } from '../../../types'

export interface StudyPlan {
  bookId: string
  dailyCount: number
  totalDays: number
  startIndex: number
}

export interface StudyBookCard {
  book: Book
  currentIndex: number
  progressPercent: number
  remainingWords: number
  isActive: boolean
  isComplete: boolean
}

export interface DailyPlanAction {
  kind: 'add-book' | 'due-review' | 'error-review' | 'continue-book'
  cta_label: string
  mode?: string | null
  book_id?: string | null
  dimension?: string | null
}

export interface DailyPlanTask {
  id: string
  kind: 'add-book' | 'due-review' | 'error-review' | 'continue-book'
  title: string
  description: string
  status: 'pending' | 'completed'
  completion_source?: 'completed_today' | 'already_clear' | null
  badge: string
  action: DailyPlanAction
}

function parseTimestamp(value?: string | null): number {
  if (!value) return 0
  const timestamp = Date.parse(value)
  return Number.isNaN(timestamp) ? 0 : timestamp
}

export function buildStudyBookCards(
  books: Book[],
  myBookIds: Set<string>,
  progressMap: Record<string, BookProgress | undefined>,
): StudyBookCard[] {
  return books
    .filter(book => myBookIds.has(book.id))
    .map(book => {
      const progress = progressMap[book.id]
      const currentIndex = Math.max(0, Number(progress?.current_index) || 0)
      const safeWordCount = Math.max(1, Number(book.word_count) || 1)
      const progressPercent = Math.min(100, Math.round((currentIndex / safeWordCount) * 100))
      const remainingWords = Math.max(0, safeWordCount - currentIndex)

      return {
        book,
        currentIndex,
        progressPercent,
        remainingWords,
        isActive: currentIndex > 0 && progressPercent < 100,
        isComplete: progressPercent >= 100,
      }
    })
    .sort((left, right) => {
      if (left.isComplete !== right.isComplete) return left.isComplete ? 1 : -1
      if (left.isActive !== right.isActive) return left.isActive ? -1 : 1

      const updatedDiff = parseTimestamp(progressMap[right.book.id]?.updatedAt)
        - parseTimestamp(progressMap[left.book.id]?.updatedAt)
      if (updatedDiff !== 0) return updatedDiff

      const progressDiff = right.currentIndex - left.currentIndex
      if (progressDiff !== 0) return progressDiff

      return left.book.title.localeCompare(right.book.title, 'zh-CN')
    })
}

export function formatDurationSeconds(totalSeconds: number): string {
  if (totalSeconds <= 0) return '0 分钟'
  const minutes = Math.max(1, Math.round(totalSeconds / 60))
  if (minutes < 60) return `${minutes} 分钟`

  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return remainingMinutes > 0 ? `${hours} 小时 ${remainingMinutes} 分钟` : `${hours} 小时`
}

export function getTaskStateLabel(task: DailyPlanTask): string {
  if (task.status === 'pending') return '待完成'
  if (task.completion_source === 'completed_today') return '今日完成'
  return '已清空'
}
