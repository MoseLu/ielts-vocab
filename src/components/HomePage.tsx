import { useMemo, useRef, useState, type MouseEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useAllBookProgress,
  useLearningStats,
  useMyBooks,
  useVocabBooks,
  useWrongWords,
} from '../features/vocabulary/hooks'
import { buildWrongWordsPracticeQuery } from '../features/vocabulary/wrongWordsFilters'
import { useResponsivePageSkeletonCount } from '../hooks/useResponsiveSkeletonCount'
import { buildBookPracticePath } from '../lib'
import {
  buildGuidedStudySummary,
  getGuidedPracticeModeLabel,
  getWrongDimensionLongLabel,
  type GuidedPracticeMode,
  type GuidedStudyActionRef,
  type GuidedStudyPrimaryAction,
  type GuidedStudyStep,
  type StudyBookCard,
} from '../lib/guidedStudy'
import type { Book, BookProgress } from '../types'
import type { Chapter } from './ChapterModal'
import ChapterModal from './ChapterModal'
import PlanModal from './PlanModal'
import { PageReady, PageSkeleton } from './ui'

interface StudyPlan {
  bookId: string
  dailyCount: number
  totalDays: number
  startIndex: number
}

const STEP_STATUS_LABELS: Record<GuidedStudyStep['status'], string> = {
  current: '推荐先做',
  ready: '也能先做',
  done: '已清空',
  optional: '自由选',
}

function requestPracticeMode(mode?: GuidedPracticeMode) {
  if (!mode) return

  window.dispatchEvent(new CustomEvent('practice-mode-request', {
    detail: { mode },
  }))
}

function requestModeFromDimension(dimension?: GuidedStudyActionRef['dimension']): GuidedPracticeMode | undefined {
  if (!dimension) return undefined
  if (dimension === 'recognition') return 'quickmemory'
  if (dimension === 'listening') return 'listening'
  if (dimension === 'meaning') return 'meaning'
  if (dimension === 'dictation') return 'dictation'
  return undefined
}

function GuidedHeroMetric({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="study-guide-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function FreeChoiceCard({
  title,
  description,
  badge,
  onClick,
}: {
  title: string
  description: string
  badge?: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      className="study-choice-card"
      onClick={onClick}
    >
      <div className="study-choice-card__top">
        <h3 className="study-choice-card__title">{title}</h3>
        {badge && <span className="study-choice-card__badge">{badge}</span>}
      </div>
      <p className="study-choice-card__description">{description}</p>
      <span className="study-choice-card__cta">直接去做</span>
    </button>
  )
}

function GuideStepCard({
  step,
  onSelect,
}: {
  step: GuidedStudyStep
  onSelect: (action: GuidedStudyActionRef) => void
}) {
  const modeLabel = getGuidedPracticeModeLabel(step.action.mode)
  const dimLabel = getWrongDimensionLongLabel(step.action.dimension)

  return (
    <button
      type="button"
      className={`study-step-card is-${step.status}${step.action.disabled ? ' is-disabled' : ''}`}
      disabled={step.action.disabled}
      onClick={() => onSelect(step.action)}
    >
      <div className="study-step-order">{step.order}</div>
      <div className="study-step-body">
        <div className="study-step-row">
          <h3 className="study-step-title">{step.title}</h3>
          <span className={`study-step-status study-step-status--${step.status}`}>
            {STEP_STATUS_LABELS[step.status]}
          </span>
        </div>
        <p className="study-step-description">{step.description}</p>
        <div className="study-step-meta">
          {step.badge && <span className="study-step-badge">{step.badge}</span>}
          {modeLabel && <span className="study-step-tag">{modeLabel}</span>}
          {dimLabel && <span className="study-step-tag">{dimLabel}</span>}
        </div>
      </div>
      <div className="study-step-cta">{step.action.ctaLabel}</div>
    </button>
  )
}

function MyBookCard({
  card,
  onSelect,
  onRemove,
}: {
  card: StudyBookCard
  onSelect: (book: Book) => void
  onRemove: (bookId: string, event: MouseEvent<HTMLButtonElement>) => void
}) {
  return (
    <div
      key={card.book.id}
      className="study-book-card study-book-card-main"
      onClick={() => onSelect(card.book)}
    >
      <button
        className="study-book-remove"
        onClick={(event) => onRemove(card.book.id, event)}
        title="移除"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>

      <div className="study-book-icon-row">
        <div className="study-book-icon study-book-icon--accent">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
        </div>

        <div className="study-book-header">
          <h3 className="study-book-title">{card.book.title}</h3>
          <div className="study-book-badges">
            {card.book.is_paid && <span className="study-book-badge">付费</span>}
            {card.isActive && <span className="study-book-state study-book-state--active">进行中</span>}
            {card.isComplete && <span className="study-book-state study-book-state--complete">已完成</span>}
          </div>
        </div>
      </div>

      <div className="study-book-progress-text">
        {card.currentIndex} / {card.book.word_count} 词
      </div>
      <div
        className="study-book-progress-bar"
        role="progressbar"
        aria-label={`${card.book.title} 学习进度`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={card.progressPercent}
      >
        <div
          className="study-book-progress-fill"
          style={{ width: `${card.progressPercent}%` }}
        />
      </div>
      <div className="study-book-stats">
        <span>{card.progressPercent}% 完成</span>
        {card.isComplete ? (
          <span className="study-book-status-complete">主线已完成</span>
        ) : (
          <span>剩余 {card.remainingWords} 词</span>
        )}
      </div>
    </div>
  )
}

function HeroBadge({ action }: { action: GuidedStudyPrimaryAction }) {
  if (!action.badge) return null

  return (
    <span className={`study-guide-pill study-guide-pill--${action.tone}`}>
      {action.badge}
    </span>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const [selectedBook, setSelectedBook] = useState<Book | null>(null)
  const [showChapterModal, setShowChapterModal] = useState(false)
  const selfServeRef = useRef<HTMLElement | null>(null)

  const { books, loading: booksLoading } = useVocabBooks()
  const { progressMap, loading: progressLoading } = useAllBookProgress()
  const { myBookIds, loading: myBooksLoading, addBook, removeBook } = useMyBooks()
  const { words: wrongWords } = useWrongWords()
  const { alltime, learnerProfile } = useLearningStats(7, 'all', 'all')
  const { containerRef, count: skeletonCount } = useResponsivePageSkeletonCount({
    minColumnWidth: 260,
    gap: 10,
  })

  const isInitialLoading = booksLoading || progressLoading || myBooksLoading

  const guided = useMemo(() => {
    return buildGuidedStudySummary({
      books: books as Book[],
      myBookIds,
      progressMap: progressMap as Record<string, BookProgress | undefined>,
      wrongWords,
      alltime,
      learnerProfile,
    })
  }, [alltime, books, learnerProfile, myBookIds, progressMap, wrongWords])

  const handleSelectBook = (book: Book) => {
    if (!myBookIds.has(book.id)) {
      addBook(book.id)
    }
    setSelectedBook(book)
    setShowChapterModal(Boolean(book.is_paid || book.practice_mode === 'match'))
  }

  const handleStartStudy = (plan: StudyPlan | null) => {
    if (plan) {
      localStorage.setItem('study_plan', JSON.stringify(plan))
    }
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    if (!selectedBook) return
    navigate(buildBookPracticePath(selectedBook))
  }

  const handleSelectChapter = (chapter: Chapter, startIndex: number) => {
    localStorage.setItem('selected_book', JSON.stringify(selectedBook))
    localStorage.setItem('selected_chapter', JSON.stringify({ id: chapter.id, title: chapter.title }))
    localStorage.setItem('chapter_start_index', String(startIndex))
    if (!selectedBook) return
    navigate(buildBookPracticePath(selectedBook, chapter.id))
  }

  const handleRemoveBook = (bookId: string, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    removeBook(bookId)
  }

  const openBookFromAction = (bookId?: string) => {
    const targetBook = guided.bookCards.find(card => card.book.id === bookId)?.book
      ?? guided.activeBook?.book
      ?? null

    if (!targetBook) {
      navigate('/books')
      return
    }

    handleSelectBook(targetBook)
  }

  const runGuidedAction = (action: GuidedStudyActionRef) => {
    switch (action.kind) {
      case 'add-book':
        navigate('/books')
        return
      case 'due-review':
        requestPracticeMode('quickmemory')
        navigate('/practice?review=due')
        return
      case 'error-review': {
        requestPracticeMode(action.mode)
        const query = buildWrongWordsPracticeQuery({
          scope: 'pending',
          dimFilter: action.dimension ?? 'all',
        })
        navigate(query ? `/practice?mode=errors&${query}` : '/practice?mode=errors')
        return
      }
      case 'continue-book':
        openBookFromAction(action.bookId)
        return
      case 'focus-mode':
        requestPracticeMode(action.mode)
        openBookFromAction(action.bookId)
        return
      default:
        return
    }
  }

  const streakText = guided.streakDays > 0 ? `${guided.streakDays} 天` : '刚开始'
  const weakestText = guided.weakestModeLabel ?? '继续积累'
  const quickReviewText = guided.dueReviewCount > 0 ? `${guided.dueReviewCount} 词` : '已清空'
  const wrongWordsText = guided.pendingWrongWordCount > 0 ? `${guided.pendingWrongWordCount} 个` : '已清空'
  const supportErrorText = guided.pendingWrongWordCount > 0
    ? `${guided.pendingWrongWordCount} 个待清理`
    : '当前没有待清理错词'
  const selfServeErrorText = guided.pendingWrongWordCount > 0
    ? guided.recommendedWrongDimensionCount > 0
      ? `优先清 ${getWrongDimensionLongLabel(guided.recommendedWrongDimension) ?? '错词'}。`
      : `还有 ${guided.pendingWrongWordCount} 个错词待清。`
    : '没积压错词，也可以去错词本看历史问题。'
  const selfServeReviewText = guided.dueReviewCount > 0
    ? `${guided.dueReviewCount} 个词已到复习点。`
    : '现在没有到期词，也可以先看看复习池。'
  const selfServeWeakModeText = guided.weakestModeLabel
    ? `不想走主线时，可以直接练 ${guided.weakestModeLabel}。`
    : '画像还不够明显，先去统计页看看趋势。'

  const scrollToSelfServe = () => {
    selfServeRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
  }

  const startDueReview = () => {
    requestPracticeMode('quickmemory')
    navigate('/practice?review=due')
  }

  const startErrorReview = () => {
    if (guided.pendingWrongWordCount <= 0) {
      navigate('/errors')
      return
    }

    runGuidedAction({
      kind: 'error-review',
      ctaLabel: '开始清错',
      mode: guided.recommendedWrongDimension
        ? requestModeFromDimension(guided.recommendedWrongDimension)
        : undefined,
      dimension: guided.recommendedWrongDimension ?? undefined,
    })
  }

  const startWeakModePractice = () => {
    if (!guided.weakestMode) {
      navigate('/stats')
      return
    }

    runGuidedAction({
      kind: 'focus-mode',
      ctaLabel: '开始专项练习',
      mode: guided.weakestMode,
      bookId: guided.activeBook?.book.id,
    })
  }

  return (
    <div className="study-center-page">
      <div className="page-content" ref={containerRef}>
        <PageReady
          ready={!isInitialLoading}
          fallback={<PageSkeleton variant="books" itemCount={skeletonCount} bookMinWidth={260} />}
        >
          <div className="study-center-shell">
            <section className="study-guide-hero">
              <div className="study-guide-eyebrow">今天推荐这样学</div>
              <HeroBadge action={guided.primaryAction} />
              <h1 className="study-guide-title">{guided.primaryAction.title}</h1>
              <p className="study-guide-description">{guided.primaryAction.description}</p>
              <p className="study-guide-caption">
                这是系统推荐，不是锁流程。你随时可以改走别的学习路径。
              </p>

              <div className="study-guide-metrics">
                <GuidedHeroMetric label="连续学习" value={streakText} />
                <GuidedHeroMetric label="到期复习" value={quickReviewText} />
                <GuidedHeroMetric label="待清错词" value={wrongWordsText} />
                <GuidedHeroMetric label="当前薄弱项" value={weakestText} />
              </div>

              <div className="study-guide-actions">
                <button
                  type="button"
                  className="study-guide-primary-btn"
                  onClick={() => runGuidedAction(guided.primaryAction)}
                >
                  {guided.primaryAction.ctaLabel}
                </button>
                <button
                  type="button"
                  className="study-guide-secondary-btn"
                  onClick={scrollToSelfServe}
                >
                  我想自己选
                </button>
              </div>
            </section>

            <div className="study-guide-content">
              <section className="study-guide-panel">
                <div className="study-section-head">
                  <div>
                    <h2>系统推荐顺序</h2>
                    <p>这是建议，不是强制。每一步都还能直接点进去。</p>
                  </div>
                </div>
                <div className="study-guide-steps">
                  {guided.steps.map(step => (
                    <GuideStepCard
                      key={step.id}
                      step={step}
                      onSelect={runGuidedAction}
                    />
                  ))}
                </div>
              </section>

              <aside className="study-guide-side">
                <section className="study-guide-side-card" ref={selfServeRef}>
                  <div className="study-section-head study-section-head--compact">
                    <div>
                      <h2>我现在想...</h2>
                      <p>不按推荐也可以，直接走你当下更想做的路径。</p>
                    </div>
                  </div>
                  <div className="study-self-serve-grid">
                    <FreeChoiceCard
                      title="先背新词"
                      description={guided.activeBook
                        ? `继续《${guided.activeBook.book.title}》，按你自己的节奏推进。`
                        : '先选一本词书，再决定今天的新词主线。'}
                      badge={guided.activeBook
                        ? (guided.activeBook.isComplete ? '换一本词书' : `剩余 ${guided.activeBook.remainingWords} 词`)
                        : '先选词书'}
                      onClick={() => openBookFromAction(guided.activeBook?.book.id)}
                    />
                    <FreeChoiceCard
                      title="先复习"
                      description={selfServeReviewText}
                      badge={guided.dueReviewCount > 0 ? `${guided.dueReviewCount} 词到期` : '复习池可查看'}
                      onClick={startDueReview}
                    />
                    <FreeChoiceCard
                      title="先清错词"
                      description={selfServeErrorText}
                      badge={guided.pendingWrongWordCount > 0 ? `${guided.pendingWrongWordCount} 个待清` : '先看错词本'}
                      onClick={startErrorReview}
                    />
                    <FreeChoiceCard
                      title="直接练弱项"
                      description={selfServeWeakModeText}
                      badge={guided.weakestModeLabel ?? '先看画像'}
                      onClick={startWeakModePractice}
                    />
                  </div>
                </section>

                <section className="study-guide-side-card">
                  <div className="study-section-head study-section-head--compact">
                    <div>
                      <h2>系统提醒</h2>
                      <p>优先级已经替你压缩成几条最该做的事。</p>
                    </div>
                  </div>
                  <ul className="study-guide-notes">
                    {guided.nextActions.map(note => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </section>

                <section className="study-guide-side-card">
                  <div className="study-section-head study-section-head--compact">
                    <div>
                      <h2>其他页面</h2>
                      <p>想看全量信息时，再去这些页面深挖。</p>
                    </div>
                  </div>
                  <div className="study-quick-links">
                    <button
                      type="button"
                      className="study-quick-link"
                      onClick={() => navigate('/errors')}
                    >
                      <span className="study-quick-link__label">错词本</span>
                      <span className="study-quick-link__value">{supportErrorText}</span>
                    </button>
                    <button
                      type="button"
                      className="study-quick-link"
                      onClick={() => navigate('/books')}
                    >
                      <span className="study-quick-link__label">词书库</span>
                      <span className="study-quick-link__value">
                        {guided.bookCards.length > 0 ? `${guided.bookCards.length} 本已加入` : '去添加词书'}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="study-quick-link"
                      onClick={() => navigate('/stats')}
                    >
                      <span className="study-quick-link__label">学习统计</span>
                      <span className="study-quick-link__value">查看趋势与薄弱项</span>
                    </button>
                  </div>
                </section>
              </aside>
            </div>

            <section className="study-guide-panel">
              <div className="study-section-head">
                <div>
                  <h2>你的词书</h2>
                  <p>词书仍然可以自由切换，但不再需要你自己决定主线顺序。</p>
                </div>
                <button
                  type="button"
                  className="study-section-link"
                  onClick={() => navigate('/books')}
                >
                  管理词书
                </button>
              </div>

              <div className="study-center-grid">
                {guided.bookCards.map(card => (
                  <MyBookCard
                    key={card.book.id}
                    card={card}
                    onSelect={handleSelectBook}
                    onRemove={handleRemoveBook}
                  />
                ))}

                <button
                  type="button"
                  className="study-add-card"
                  onClick={() => navigate('/books')}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  <span>{guided.bookCards.length > 0 ? '添加或切换词书' : '添加第一本词书'}</span>
                </button>
              </div>
            </section>
          </div>
        </PageReady>
      </div>

      {selectedBook && showChapterModal && (
        <ChapterModal
          key={`chapter-${selectedBook.id}-${showChapterModal}`}
          book={selectedBook}
          progress={progressMap[selectedBook.id]}
          onClose={() => {
            setSelectedBook(null)
            setShowChapterModal(false)
          }}
          onSelectChapter={handleSelectChapter}
        />
      )}

      {selectedBook && !showChapterModal && (
        <PlanModal
          book={selectedBook}
          progress={progressMap[selectedBook.id]}
          onClose={() => setSelectedBook(null)}
          onStart={handleStartStudy}
        />
      )}
    </div>
  )
}
