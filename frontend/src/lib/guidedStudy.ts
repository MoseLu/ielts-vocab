import type { LearningAlltime, LearnerProfile, WrongWord } from '../features/vocabulary/hooks'
import { getPracticeModeLabel, normalizeModeText } from '../constants/practiceModes'
import {
  WRONG_WORD_DIMENSIONS,
  WRONG_WORD_DIMENSION_LABELS,
  hasWrongWordPending,
  isWrongWordPendingInDimension,
  type WrongWordDimension,
} from '../features/vocabulary/wrongWordsStore'
import type { Book, BookProgress } from '../types'

export type GuidedPracticeMode = 'smart' | 'quickmemory' | 'listening' | 'meaning' | 'dictation'
export type GuidedActionKind = 'add-book' | 'due-review' | 'error-review' | 'continue-book' | 'focus-mode'
export type GuidedStepStatus = 'current' | 'ready' | 'done' | 'optional'

export interface StudyBookCard {
  book: Book
  currentIndex: number
  progressPercent: number
  remainingWords: number
  isActive: boolean
  isComplete: boolean
}

export interface GuidedStudyActionRef {
  kind: GuidedActionKind
  ctaLabel: string
  mode?: GuidedPracticeMode
  bookId?: string
  dimension?: WrongWordDimension
  disabled?: boolean
}

export interface GuidedStudyPrimaryAction extends GuidedStudyActionRef {
  title: string
  description: string
  badge?: string
  tone: 'accent' | 'error' | 'success' | 'neutral'
}

export interface GuidedStudyStep {
  id: string
  order: number
  title: string
  description: string
  badge?: string
  status: GuidedStepStatus
  action: GuidedStudyActionRef
}

export interface GuidedStudySummary {
  primaryAction: GuidedStudyPrimaryAction
  steps: GuidedStudyStep[]
  bookCards: StudyBookCard[]
  activeBook: StudyBookCard | null
  dueReviewCount: number
  pendingWrongWordCount: number
  recommendedWrongDimension: WrongWordDimension | null
  recommendedWrongDimensionCount: number
  weakestMode: GuidedPracticeMode | null
  weakestModeLabel: string | null
  streakDays: number
  nextActions: string[]
}

function parseTimestamp(value?: string | null): number {
  if (!value) return 0
  const timestamp = Date.parse(value)
  return Number.isNaN(timestamp) ? 0 : timestamp
}

function buildBookCards(
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

function normalizeWeakestMode(value?: string | null): GuidedPracticeMode | null {
  if (!value) return null

  switch (value) {
    case 'recognition':
    case 'quickmemory':
      return 'quickmemory'
    case 'listening':
      return 'listening'
    case 'meaning':
      return 'meaning'
    case 'dictation':
      return 'dictation'
    case 'smart':
      return 'smart'
    default:
      return null
  }
}

function buildFallbackActions({
  dueReviewCount,
  pendingWrongWordCount,
  recommendedWrongDimension,
  recommendedWrongDimensionCount,
  activeBook,
  weakestModeLabel,
}: {
  dueReviewCount: number
  pendingWrongWordCount: number
  recommendedWrongDimension: WrongWordDimension | null
  recommendedWrongDimensionCount: number
  activeBook: StudyBookCard | null
  weakestModeLabel: string | null
}): string[] {
  const actions: string[] = []

  if (dueReviewCount > 0) {
    actions.push(`先复习 ${dueReviewCount} 个到期单词，别把复习拖成积压。`)
  }

  if (pendingWrongWordCount > 0) {
    if (recommendedWrongDimension) {
      actions.push(
        `错词优先清「${WRONG_WORD_DIMENSION_LABELS[recommendedWrongDimension]}」，当前还有 ${recommendedWrongDimensionCount} 个词待清。`,
      )
    } else {
      actions.push(`错词还有 ${pendingWrongWordCount} 个待处理，建议今天清一轮。`)
    }
  }

  if (activeBook && !activeBook.isComplete) {
    actions.push(`《${activeBook.book.title}》还剩 ${activeBook.remainingWords} 词，适合继续推进新词。`)
  }

  if (weakestModeLabel) {
    actions.push(`当前薄弱项是 ${weakestModeLabel}，清完主线后再加练一轮。`)
  }

  if (actions.length === 0) {
    actions.push('主线任务已清空，可以自由安排一轮巩固练习。')
  }

  return actions.slice(0, 3)
}

export function getGuidedPracticeModeLabel(mode?: GuidedPracticeMode | null): string | null {
  return getPracticeModeLabel(mode)
}

export function buildGuidedStudySummary({
  books,
  myBookIds,
  progressMap,
  wrongWords,
  alltime,
  learnerProfile,
}: {
  books: Book[]
  myBookIds: Set<string>
  progressMap: Record<string, BookProgress | undefined>
  wrongWords: WrongWord[]
  alltime?: LearningAlltime | null
  learnerProfile?: LearnerProfile | null
}): GuidedStudySummary {
  const bookCards = buildBookCards(books, myBookIds, progressMap)
  const activeBook =
    bookCards.find(card => card.isActive)
    ?? bookCards.find(card => !card.isComplete)
    ?? bookCards[0]
    ?? null

  const pendingWrongWords = wrongWords.filter(word => hasWrongWordPending(word))
  const pendingWrongWordCount = pendingWrongWords.length

  const recommendedWrongDimension = WRONG_WORD_DIMENSIONS
    .map(dimension => ({
      dimension,
      count: pendingWrongWords.filter(word => isWrongWordPendingInDimension(word, dimension)).length,
    }))
    .sort((left, right) => right.count - left.count)[0]

  const dueReviewCount = Math.max(
    learnerProfile?.summary.due_reviews ?? 0,
    alltime?.ebbinghaus_due_total ?? 0,
  )

  const weakestMode = normalizeWeakestMode(
    learnerProfile?.summary.weakest_mode
    ?? alltime?.weakest_mode
    ?? null,
  )
  const weakestModeLabel =
    getPracticeModeLabel(weakestMode, learnerProfile?.summary.weakest_mode_label)
    ?? getGuidedPracticeModeLabel(weakestMode)
    ?? null
  const streakDays = learnerProfile?.summary.streak_days ?? alltime?.streak_days ?? 0

  const nextActions = learnerProfile?.next_actions?.length
    ? learnerProfile.next_actions.slice(0, 3).map(action => normalizeModeText(action))
    : buildFallbackActions({
        dueReviewCount,
        pendingWrongWordCount,
        recommendedWrongDimension: recommendedWrongDimension?.count ? recommendedWrongDimension.dimension : null,
        recommendedWrongDimensionCount: recommendedWrongDimension?.count ?? 0,
        activeBook,
        weakestModeLabel,
      })

  const hasMyBooks = bookCards.length > 0
  const hasIncompleteBook = Boolean(activeBook && !activeBook.isComplete)

  let primaryAction: GuidedStudyPrimaryAction

  if (!hasMyBooks) {
    primaryAction = {
      kind: 'add-book',
      title: '先选一本词书，后面的学习顺序我来替你安排',
      description: '没有词书时，首页无法生成下一步。先添加一本词书，系统再自动引导你走复习、错词和新词主线。',
      ctaLabel: '去选词书',
      tone: 'accent',
    }
  } else if (dueReviewCount > 0) {
    primaryAction = {
      kind: 'due-review',
      title: '先完成到期复习，再开始今天的新词',
      description: `${dueReviewCount} 个单词已经到复习点。先把艾宾浩斯复习清掉，新词学习才不会越学越乱。`,
      ctaLabel: '开始到期复习',
      badge: `${dueReviewCount} 词到期`,
      mode: 'quickmemory',
      tone: 'accent',
    }
  } else if (pendingWrongWordCount > 0) {
    primaryAction = {
      kind: 'error-review',
      title: '先把错词清一轮，别让问题继续堆积',
      description: recommendedWrongDimension?.count
        ? `${pendingWrongWordCount} 个错词还在待清，建议优先处理「${WRONG_WORD_DIMENSION_LABELS[recommendedWrongDimension.dimension]}」这类问题。`
        : `${pendingWrongWordCount} 个错词还在待清，先清错再推进新词会更稳。`,
      ctaLabel: recommendedWrongDimension?.count
        ? `先清${WRONG_WORD_DIMENSION_LABELS[recommendedWrongDimension.dimension]}`
        : '开始清错词',
      badge: `${pendingWrongWordCount} 个待清理`,
      mode: recommendedWrongDimension?.dimension
        ? normalizeWeakestMode(recommendedWrongDimension.dimension) ?? undefined
        : undefined,
      dimension: recommendedWrongDimension?.count ? recommendedWrongDimension.dimension : undefined,
      tone: 'error',
    }
  } else if (hasIncompleteBook && activeBook) {
    primaryAction = {
      kind: 'continue-book',
      title: `继续推进《${activeBook.book.title}》的新词`,
      description: activeBook.isActive
        ? `当前已学 ${activeBook.currentIndex}/${activeBook.book.word_count} 词，还剩 ${activeBook.remainingWords} 词。沿着这一条主线继续即可。`
        : `这本词书还没完成，建议从这里继续。系统会按词书自身设置进入对应学习流程。`,
      ctaLabel: activeBook.isActive ? '继续当前词书' : '开始这本词书',
      badge: `${activeBook.progressPercent}% 已完成`,
      bookId: activeBook.book.id,
      tone: 'accent',
    }
  } else if (weakestMode && activeBook) {
    primaryAction = {
      kind: 'focus-mode',
      title: `主线已清空，今天做一轮${weakestModeLabel ?? getGuidedPracticeModeLabel(weakestMode)}巩固`,
      description: '当复习、错词、新词都没有积压时，再做专项模式加练，用户会更容易理解自己下一步为什么这样学。',
      ctaLabel: '开始专项巩固',
      badge: weakestModeLabel ?? getGuidedPracticeModeLabel(weakestMode) ?? undefined,
      mode: weakestMode,
      bookId: activeBook.book.id,
      tone: 'success',
    }
  } else {
    primaryAction = {
      kind: 'continue-book',
      title: '当前主线任务已清空，可以自由选择一本词书继续巩固',
      description: '你现在没有到期复习，也没有待清错词。可以回到词书继续巩固，或者查看学习画像决定下一轮重点。',
      ctaLabel: '查看词书',
      bookId: activeBook?.book.id,
      tone: 'neutral',
    }
  }

  const steps: GuidedStudyStep[] = [
    {
      id: 'due-review',
      order: 1,
      title: '先复习到期词',
      description: dueReviewCount > 0
        ? `${dueReviewCount} 个单词已经到复习点，先回顾再学新词。`
        : '当前没有到期复习，可以直接进入下一步。',
      badge: dueReviewCount > 0 ? `${dueReviewCount} 词` : '已清空',
      status: dueReviewCount > 0 ? 'current' : 'done',
      action: {
        kind: 'due-review',
        ctaLabel: '开始复习',
        mode: 'quickmemory',
        disabled: dueReviewCount <= 0,
      },
    },
    {
      id: 'error-review',
      order: 2,
      title: '再清错词',
      description: pendingWrongWordCount > 0
        ? recommendedWrongDimension?.count
          ? `优先攻克「${WRONG_WORD_DIMENSION_LABELS[recommendedWrongDimension.dimension]}」，当前 ${recommendedWrongDimension.count} 个词待清。`
          : `${pendingWrongWordCount} 个错词还没通过，建议清一轮。`
        : '当前没有待清理错词。',
      badge: pendingWrongWordCount > 0 ? `${pendingWrongWordCount} 个待处理` : '已清空',
      status: pendingWrongWordCount <= 0
        ? 'done'
        : dueReviewCount > 0
          ? 'ready'
          : 'current',
      action: {
        kind: 'error-review',
        ctaLabel: recommendedWrongDimension?.count
          ? `清${WRONG_WORD_DIMENSION_LABELS[recommendedWrongDimension.dimension]}`
          : '开始清错',
        mode: recommendedWrongDimension?.count
          ? normalizeWeakestMode(recommendedWrongDimension.dimension) ?? undefined
          : undefined,
        dimension: recommendedWrongDimension?.count ? recommendedWrongDimension.dimension : undefined,
        disabled: pendingWrongWordCount <= 0,
      },
    },
    {
      id: 'new-words',
      order: 3,
      title: hasMyBooks ? '继续新词主线' : '先添加第一本词书',
      description: !hasMyBooks
        ? '没有词书时，系统无法给出新词主线。先加一本，再自动安排后续步骤。'
        : hasIncompleteBook && activeBook
          ? `继续《${activeBook.book.title}》，还剩 ${activeBook.remainingWords} 词。`
          : '你的词书主线已经清空，可以转入专项巩固。',
      badge: !hasMyBooks
        ? '缺少词书'
        : activeBook
          ? `${activeBook.progressPercent}%`
          : '已完成',
      status: !hasMyBooks
        ? 'current'
        : hasIncompleteBook
          ? (dueReviewCount > 0 || pendingWrongWordCount > 0 ? 'ready' : 'current')
          : 'done',
      action: {
        kind: hasMyBooks ? 'continue-book' : 'add-book',
        ctaLabel: !hasMyBooks ? '去选词书' : hasIncompleteBook ? '继续词书' : '查看词书',
        bookId: activeBook?.book.id,
        disabled: hasMyBooks && !activeBook,
      },
    },
    {
      id: 'focus-mode',
      order: 4,
      title: '最后做薄弱项巩固',
      description: weakestMode && weakestModeLabel
        ? `当前薄弱项是 ${weakestModeLabel}，适合在主线任务清空后单独加练。`
        : '继续积累几轮学习数据后，这里会给出更明确的专项建议。',
      badge: weakestModeLabel ?? '等待画像',
      status: weakestMode
        ? (dueReviewCount <= 0 && pendingWrongWordCount <= 0 && !hasIncompleteBook ? 'current' : 'optional')
        : 'done',
      action: {
        kind: 'focus-mode',
        ctaLabel: weakestMode ? '开始专项练习' : '等待画像',
        mode: weakestMode ?? undefined,
        bookId: activeBook?.book.id,
        disabled: !weakestMode || !activeBook,
      },
    },
  ]

  return {
    primaryAction,
    steps,
    bookCards,
    activeBook,
    dueReviewCount,
    pendingWrongWordCount,
    recommendedWrongDimension: recommendedWrongDimension?.count ? recommendedWrongDimension.dimension : null,
    recommendedWrongDimensionCount: recommendedWrongDimension?.count ?? 0,
    weakestMode,
    weakestModeLabel,
    streakDays,
    nextActions,
  }
}

export function getWrongDimensionShortLabel(dimension?: WrongWordDimension | null): string | null {
  return dimension ? WRONG_WORD_DIMENSION_LABELS[dimension] : null
}

export function getWrongDimensionLongLabel(dimension?: WrongWordDimension | null): string | null {
  return dimension ? WRONG_WORD_DIMENSION_LABELS[dimension] : null
}
