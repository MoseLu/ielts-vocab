import type { LearningAlltime, LearnerProfile } from '../../../features/vocabulary/hooks'
import {
  getWrongWordDimensionLabel,
  WRONG_WORD_DIMENSION_LABELS,
  WRONG_WORD_PENDING_REVIEW_TARGET,
} from '../../../features/vocabulary/wrongWordsStore'
import { QUICK_MEMORY_REVIEW_INTERVALS_DAYS } from '../../../lib/quickMemory'
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
  displayCurrentCount: number
  displayTotalCount: number
  displayRemainingCount: number
  displayUnit: '词' | '组'
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

export interface StudyGuidanceCard {
  id: string
  eyebrow: string
  title: string
  badge: string
  description: string
  facts: string[]
  sections: StudyGuidanceCardSection[]
  tone: 'accent' | 'error' | 'success' | 'neutral'
}

export interface StudyGuidanceSection {
  cards: StudyGuidanceCard[]
}

export interface StudyGuidanceCardSection {
  label: string
  items: string[]
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
      const progressRatio = Math.min(1, currentIndex / safeWordCount)
      const progressPercent = Math.min(100, Math.round(progressRatio * 100))
      const remainingWords = Math.max(0, safeWordCount - currentIndex)
      const isConfusable = String(book.id) === 'ielts_confusable_match' && Number(book.group_count) > 0
      const displayTotalCount = isConfusable ? Number(book.group_count) || 0 : safeWordCount
      const displayCurrentCount = isConfusable
        ? Math.min(displayTotalCount, Math.max(currentIndex > 0 ? 1 : 0, Math.round(progressRatio * displayTotalCount)))
        : currentIndex
      const displayRemainingCount = Math.max(0, displayTotalCount - displayCurrentCount)

      return {
        book,
        currentIndex,
        progressPercent,
        remainingWords,
        displayCurrentCount,
        displayTotalCount,
        displayRemainingCount,
        displayUnit: isConfusable ? '组' : '词',
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

function formatPercentLabel(value: number | null | undefined, fallback: string): string {
  return typeof value === 'number' && Number.isFinite(value)
    ? `${Math.round(value)}%`
    : fallback
}

function getTrendLabel(
  value: LearnerProfile['summary']['trend_direction'] | LearningAlltime['trend_direction'] | undefined,
): string {
  if (value === 'improving') return '趋势上升'
  if (value === 'declining') return '趋势回落'
  if (value === 'new') return '画像建立中'
  return '趋势稳定'
}

function getWeakestDimension(learnerProfile?: LearnerProfile | null) {
  return [...(learnerProfile?.dimensions ?? [])].sort((left, right) => {
    const weaknessDiff = right.weakness - left.weakness
    if (weaknessDiff !== 0) return weaknessDiff

    const leftAccuracy = left.accuracy ?? 100
    const rightAccuracy = right.accuracy ?? 100
    if (leftAccuracy !== rightAccuracy) return leftAccuracy - rightAccuracy

    return right.wrong - left.wrong
  })[0] ?? null
}

function getReviewCadenceLabel(alltime?: LearningAlltime | null): string {
  const intervals = alltime?.ebbinghaus_stages?.length
    ? alltime.ebbinghaus_stages.map(stage => stage.interval_days)
    : QUICK_MEMORY_REVIEW_INTERVALS_DAYS

  return intervals.map(interval => `${interval} 天`).join(' / ')
}

export function buildStudyGuidanceSection({
  learnerProfile,
  alltime,
  reviewTask,
  errorTask,
  focusBookTitle,
  focusBookRemainingWords,
}: {
  learnerProfile?: LearnerProfile | null
  alltime?: LearningAlltime | null
  reviewTask?: DailyPlanTask | null
  errorTask?: DailyPlanTask | null
  focusBookTitle?: string | null
  focusBookRemainingWords?: number | null
}): StudyGuidanceSection {
  const weakestDimension = getWeakestDimension(learnerProfile)
  const weakestModeLabel = learnerProfile?.summary.weakest_mode_label?.trim() || '当前最弱模式'
  const weakestModeAccuracy = learnerProfile?.summary.weakest_mode_accuracy ?? alltime?.weakest_mode_accuracy
  const streakDays = learnerProfile?.summary.streak_days ?? alltime?.streak_days ?? 0
  const dueReviewCount = Math.max(
    learnerProfile?.summary.due_reviews ?? 0,
    alltime?.ebbinghaus_due_total ?? 0,
  )
  const reviewBadge = reviewTask?.badge ?? (dueReviewCount > 0 ? `${dueReviewCount} 词到期` : '当前无到期')
  const reviewCadence = getReviewCadenceLabel(alltime)
  const reviewTarget = QUICK_MEMORY_REVIEW_INTERVALS_DAYS.length
  const focusBookLabel = focusBookTitle?.trim() ? `《${focusBookTitle.trim()}》` : '先选今天的词书'
  const focusBookProgress = typeof focusBookRemainingWords === 'number'
    ? (focusBookRemainingWords > 0 ? `还剩 ${focusBookRemainingWords} 词` : '主线已清空')
    : '主线进度看词书卡片'
  const weakestDimensionLabel = getWrongWordDimensionLabel(weakestDimension?.dimension, weakestDimension?.label) ?? '当前最薄弱的一项'
  const allWrongDimensionLabels = Object.values(WRONG_WORD_DIMENSION_LABELS).join('、')
  return {
    cards: [
      {
        id: 'wrong-words',
        eyebrow: '错词本',
        title: '错词怎么减少',
        badge: errorTask?.status === 'completed'
          ? '今日待清已空'
          : (weakestDimension ? `${weakestDimensionLabel} 优先处理` : `连续 ${WRONG_WORD_PENDING_REVIEW_TARGET} 次才会消掉`),
        description: `错词不会直接删除。哪一项能力答错了，就要把这一项连续答对 ${WRONG_WORD_PENDING_REVIEW_TARGET} 次，它才会从待清里消掉。`,
        facts: [
          `当前：${errorTask?.badge ?? '看待清范围'}`,
          `优先：${weakestDimensionLabel}`,
          `门槛：连续答对 ${WRONG_WORD_PENDING_REVIEW_TARGET} 次`,
        ],
        sections: [
          {
            label: '怎么记入',
            items: [
              `${allWrongDimensionLabels} 这四类问题会分开记录，不会互相抵消。`,
              `只要某一项还没连续答对 ${WRONG_WORD_PENDING_REVIEW_TARGET} 次，这一项就还算“没清掉”。`,
            ],
          },
          {
            label: '怎么变少',
            items: [
              weakestDimension
                ? `你现在应该先处理 ${weakestDimensionLabel}，因为这是你最近最容易丢分的一项。`
                : '同一个词如果同时卡在几项能力上，就要一项一项地清。',
              `同一项连续答对 ${WRONG_WORD_PENDING_REVIEW_TARGET} 次后，只会消掉这一项错误，不会顺带把其他项一起清掉。`,
            ],
          },
          {
            label: '还要注意',
            items: [
              '错词数量变少，只说明这一个能力项暂时过关，不代表这个词已经彻底掌握。',
              '如果后面在这一项上又答错了，它会重新回到待清里，需要再从头累计。',
            ],
          },
        ],
        tone: errorTask?.status === 'completed' ? 'success' : 'error',
      },
      {
        id: 'ebbinghaus',
        eyebrow: '艾宾浩斯',
        title: '复习怎样算完成',
        badge: dueReviewCount > 0
          ? `${alltime?.ebbinghaus_met ?? 0}/${dueReviewCount} 已按时`
          : '当前无到期',
        description: '艾宾浩斯完成看的是今天到点的词有没有按时复习，不是把整个复习库一次做完。',
        facts: [
          `当前：${reviewBadge}`,
          `频次：${reviewCadence}`,
          `复习库：${alltime?.qm_word_total ? `${alltime.qm_word_total} 词` : '从速记开始累计'}`,
        ],
        sections: [
          {
            label: '今天算完成',
            items: [
              dueReviewCount > 0
                ? '今天的完成标准是到期待复习数量归零，不是一次清空整个复习库。'
                : '当前没有到期词，所以今天这一项已经满足“到期清零”的条件。',
              '按时复习率只统计到期词是否及时完成，不按总答题量结算。',
            ],
          },
          {
            label: '长期怎么过关',
            items: [
              `同一个词要按 ${reviewCadence} 这 ${reviewTarget} 轮节奏反复通过，才算把“认识它”这一步走完整。`,
              '只要中间有一轮想不起来或答错，就会重新回到前面，再从头巩固。',
            ],
          },
          {
            label: '还要注意',
            items: [
              '艾宾浩斯主要检查你还能不能认出这个词、回想出意思，不会替你检查中文想英文、听音辨义和听音拼写。',
              '所以“今日复习完成”只代表今天这一步做完了，不代表这个词已经没有漏洞。',
            ],
          },
        ],
        tone: dueReviewCount > 0 ? 'accent' : 'success',
      },
      {
        id: 'mode-metrics',
        eyebrow: '多模式',
        title: '每个模式看什么',
        badge: weakestModeAccuracy == null
          ? weakestModeLabel
          : `${formatPercentLabel(weakestModeAccuracy, weakestModeLabel)} 当前弱项`,
        description: '多模式不需要平均刷。先补准确率最低的模式，再让词书主线继续推进，效率更高。',
        facts: [
          `弱项：${weakestModeLabel}`,
          `准确率：${formatPercentLabel(weakestModeAccuracy, '画像同步中')}`,
          `趋势：${getTrendLabel(learnerProfile?.summary.trend_direction ?? alltime?.trend_direction)}`,
        ],
        sections: [
          {
            label: '模式完成是什么意思',
            items: [
              '某一章显示这个模式已完成，意思是你已经把这一章在这个模式下完整练过一轮。',
              '系统会记住你这一轮的正确率和错题情况，但不会直接把它当成“已经彻底掌握”。',
            ],
          },
          {
            label: '章节完成怎么显示',
            items: [
              '如果这一章已经有分模式记录，章节卡会按这些模式的完成情况来显示。',
              '如果还没有分模式记录，就先按整章进度来显示完成状态。',
            ],
          },
          {
            label: '还要注意',
            items: [
              '所以模式完成目前只代表这轮练习做完了，不代表这些词以后都不会再错。',
              '你还要结合错词本、到期复习和后面几次表现，才能看出它是不是真的稳定。',
            ],
          },
        ],
        tone: 'neutral',
      },
      {
        id: 'closure',
        eyebrow: '归档闭环',
        title: '系统还缺哪一关',
        badge: '阶段完成不等于彻底掌握',
        description: '你说的“在彻底放心前再做一次总检查”目前还没有单独做成一关，所以首页只能老实告诉用户：哪些已经做到，哪些还没有。',
        facts: [
          `主线：${focusBookLabel}`,
          `主线进度：${focusBookProgress}`,
          `连续学习：${streakDays} 天`,
        ],
        sections: [
          {
            label: '现在已经做到',
            items: [
              '新词学习、错词记录、错词回刷、到期复习、章节练习，这条学习链路现在已经有了。',
              dueReviewCount > 0
                ? `按今天的顺序，先处理 ${reviewBadge}，再清错词，最后推进 ${focusBookLabel}。`
                : `今天没有到期积压，可以先清错词，再推进 ${focusBookLabel}。`,
            ],
          },
          {
            label: '现在还缺什么',
            items: [
              `现在还没有一场专门的“总检查”，去把${allWrongDimensionLabels}这四类问题一起复核一遍。`,
              '所以你现在看到的“今日完成”“章节完成”“模式完成”，都只能理解为阶段过关。',
            ],
          },
          {
            label: '首页怎么提示',
            items: [
              '在这道总检查补齐前，首页只会展示现在真实存在的规则，不会把阶段过关说成彻底掌握。',
              '如果后面要把闭环补完整，下一步就应该增加独立总验收，再决定这些词能不能真正放行。',
            ],
          },
        ],
        tone: 'accent',
      },
    ],
  }
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
