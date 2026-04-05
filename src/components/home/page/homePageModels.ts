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

export interface DailyPlanStep {
  id: string
  label: string
  status: 'pending' | 'current' | 'completed'
}

export interface DailyPlanTask {
  id: string
  kind: 'add-book' | 'due-review' | 'error-review' | 'continue-book'
  title: string
  description: string
  status: 'pending' | 'completed'
  completion_source?: 'completed_today' | 'already_clear' | null
  badge: string
  steps?: DailyPlanStep[]
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

export function getStepStateLabel(step: DailyPlanStep): string {
  if (step.status === 'completed') return '已完成'
  if (step.status === 'current') return '当前步骤'
  return '待处理'
}

function extractQuotedLabel(text: string): string | null {
  const match = text.match(/「(.+?)」/)
  return match?.[1] ?? null
}

function buildStepItems(task: DailyPlanTask, labels: string[]): DailyPlanStep[] {
  const isCompleted = task.status === 'completed'
  return labels.map((label, index) => ({
    id: `${task.id}-step-${index + 1}`,
    label,
    status: isCompleted ? 'completed' : (index === 0 ? 'current' : 'pending'),
  }))
}

function buildCompletedTaskSteps(
  task: DailyPlanTask,
  options?: {
    focusBookTitle?: string | null
  },
): string[] {
  const focusBookTitle = options?.focusBookTitle?.trim()
  const focusBookLabel = focusBookTitle ? `《${focusBookTitle}》` : '当前词书'

  if (task.kind === 'due-review') {
    if (task.completion_source === 'already_clear') {
      return [
        '今天没有新增到期复习。',
        '到期复习队列当前已清空。',
        '可以直接进入主线学习。',
      ]
    }
    return [
      '到期复习入口已经处理过了。',
      `${task.badge} 已经完成。`,
      '可以继续下一项主线任务。',
    ]
  }

  if (task.kind === 'error-review') {
    if (task.completion_source === 'already_clear') {
      return [
        '今天没有待清理的错词。',
        '错词待清范围当前为空。',
        '可以把时间留给主线或复习。',
      ]
    }
    return [
      '今天的错词清理已经处理过了。',
      `${task.badge} 已经处理完成。`,
      '可以继续主线或弱项加练。',
    ]
  }

  if (task.kind === 'add-book') {
    return [
      '今天的主线词书已经确定。',
      '词书入口和学习计划已经准备好。',
      '首页会继续展示主线推进任务。',
    ]
  }

  return [
    `已进入 ${focusBookLabel} 并完成今日推进。`,
    '今天的词书进度已经更新。',
    '接下来可以继续复习或弱项加练。',
  ]
}

export function buildTaskGuidanceSteps(
  task: DailyPlanTask,
  options?: {
    focusBookTitle?: string | null
  },
): DailyPlanStep[] {
  if (task.status === 'completed') {
    return buildStepItems(task, buildCompletedTaskSteps(task, options))
  }

  if (task.kind === 'due-review') {
    return buildStepItems(task, [
      '打开速记复习队列，只处理到期这一组。',
      `先完成 ${task.badge}，每个词都要做到能立刻回想释义。`,
      '完成标准：到期数量归零，回到首页后这一项才会自动勾选。',
    ])
  }

  if (task.kind === 'error-review') {
    const dimensionLabel = extractQuotedLabel(task.description)
    return buildStepItems(task, [
      '进入错词强化，只看待清范围。',
      dimensionLabel
        ? `先刷 ${dimensionLabel} 这一维，再补其他维度。`
        : '先把当前待清错词连续刷过一轮。',
      '完成标准：待清错词数量下降到 0，首页才会自动勾选。',
    ])
  }

  if (task.kind === 'add-book') {
    return buildStepItems(task, [
      '先选一本今天要推进的词书。',
      '进入词书后选择章节或学习计划。',
      '完成标准：开始第一轮真实学习后，首页才会生成主线推进任务。',
    ])
  }

  const focusBookTitle = options?.focusBookTitle?.trim()
  const focusBookLabel = focusBookTitle ? `《${focusBookTitle}》` : '当前词书'
  return buildStepItems(task, [
    `打开 ${focusBookLabel}，从当前章节继续。`,
    '先完成至少一轮真实答题，让已学词数、正确数或错误数发生变化。',
    '完成标准：只点进去不算，回到首页后这一项自动勾选才算完成。',
  ])
}
