import type { CSSProperties } from 'react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { ExamPaperSummary } from '../../../lib'
import type {
  ExamLibraryQuestionFilter,
  ExamPaperQuestionIndex,
} from '../../../composables/exams/page/useExamsLibraryPage'
import { useExamsLibraryPage } from '../../../composables/exams/page/useExamsLibraryPage'
import { Page, PageContent, PageHeader, PageScroll } from '../../layout'
import { EmptyState, PageSkeleton } from '../../ui'


type ExamModeFilter = 'all' | 'listening' | 'reading' | 'writing' | 'speaking'
type ExamQuestionFilter = 'all' | ExamLibraryQuestionFilter

interface ExamCollectionView {
  key: string
  seriesNumberLabel: string
  papers: ExamPaperSummary[]
  tone: {
    accent: string
    surface: string
  }
}

interface ExamTestCardProps {
  activeMode: ExamModeFilter
  activeQuestionFilter: ExamQuestionFilter
  onOpenSection: (paperId: number, sectionType: string) => void
  paper: ExamPaperSummary
  questionIndex?: ExamPaperQuestionIndex
}

const MODE_FILTERS: Array<{ key: ExamModeFilter; label: string }> = [
  { key: 'all', label: '套题模考' },
  { key: 'listening', label: '听力' },
  { key: 'reading', label: '阅读' },
  { key: 'writing', label: '写作' },
  { key: 'speaking', label: '口语' },
]

const QUESTION_FILTERS: Array<{ key: ExamQuestionFilter; label: string }> = [
  { key: 'all', label: '全部' },
  { key: 'fill_blank', label: '填空题' },
  { key: 'single_choice', label: '单选题' },
  { key: 'multiple_choice', label: '多选题' },
  { key: 'matching', label: '匹配题' },
  { key: 'judgement', label: '判断题' },
]

const SERIES_TONES = [
  {
    accent: 'color-mix(in srgb, var(--accent) var(--mix-82), var(--surface-code))',
    surface: 'color-mix(in srgb, var(--accent) var(--mix-58), var(--surface-code))',
  },
  {
    accent: 'var(--surface-code)',
    surface: 'color-mix(in srgb, var(--surface-code) var(--mix-78), var(--accent))',
  },
  {
    accent: 'color-mix(in srgb, var(--warning) var(--mix-78), var(--surface-code))',
    surface: 'color-mix(in srgb, var(--warning) var(--mix-54), var(--surface-code))',
  },
  {
    accent: 'color-mix(in srgb, var(--success) var(--mix-78), var(--surface-code))',
    surface: 'color-mix(in srgb, var(--success) var(--mix-54), var(--surface-code))',
  },
  {
    accent: 'color-mix(in srgb, var(--info) var(--mix-78), var(--surface-code))',
    surface: 'color-mix(in srgb, var(--info) var(--mix-54), var(--surface-code))',
  },
]

function buildSeriesNumber(title: string, seriesNumber?: number | null) {
  if (seriesNumber) return String(seriesNumber)
  const digitMatch = title.match(/(\d+)/)
  return digitMatch?.[1] || title
}

function buildModeBanner(activeMode: ExamModeFilter) {
  if (activeMode === 'listening') return 'LISTENING'
  if (activeMode === 'reading') return 'READING'
  if (activeMode === 'writing') return 'WRITING'
  if (activeMode === 'speaking') return 'SPEAKING'
  return 'IELTS'
}

function buildSectionLabel(sectionType: string) {
  if (sectionType === 'listening') return 'Listening'
  if (sectionType === 'reading') return 'Reading'
  if (sectionType === 'writing') return 'Writing'
  if (sectionType === 'speaking') return 'Speaking'
  return sectionType
}

function isPracticeSection(sectionType: string) {
  return sectionType === 'listening' || sectionType === 'reading' || sectionType === 'writing'
}

function getVisibleSections(
  paper: ExamPaperSummary,
  questionIndex: ExamPaperQuestionIndex | undefined,
  activeMode: ExamModeFilter,
  activeQuestionFilter: ExamQuestionFilter,
) {
  return paper.sections.filter(section => {
    if (!isPracticeSection(section.sectionType)) return false
    const matchesMode = activeMode === 'all' || section.sectionType === activeMode
    if (!matchesMode) return false
    if (activeQuestionFilter === 'all') return true

    const sectionFilters = questionIndex?.sectionQuestionFilters[section.id] || []
    return sectionFilters.includes(activeQuestionFilter)
  })
}

function hasResponseContent(response: NonNullable<ExamPaperSummary['latestAttempt']>['responses'][number]) {
  const hasText = Boolean(response.responseText?.trim())
  const hasChoice = (response.selectedChoices?.length || 0) > 0
  const hasAttachment = Boolean(response.attachmentUrl)
  return hasText || hasChoice || hasAttachment
}

function buildSectionMetrics(
  paper: ExamPaperSummary,
  sectionId: number,
  fallbackQuestionCount: number,
  questionIndex: ExamPaperQuestionIndex | undefined,
) {
  const attempt = paper.latestAttempt
  if (!attempt) {
    return {
      isComplete: false,
      scoreLabel: null as string | null,
    }
  }

  const sectionQuestionIds = questionIndex?.sectionQuestionIds?.[sectionId] || []
  const responseByQuestionId = new Map(
    attempt.responses.map(response => [response.questionId, response]),
  )
  const answeredCount = sectionQuestionIds.filter(questionId => {
    const response = responseByQuestionId.get(questionId)
    return response ? hasResponseContent(response) : false
  }).length
  const totalQuestions = sectionQuestionIds.length || fallbackQuestionCount
  const isComplete = totalQuestions > 0 && answeredCount >= totalQuestions

  const scoredResponses = sectionQuestionIds
    .map(questionId => responseByQuestionId.get(questionId))
    .filter(
      (
        response,
      ): response is NonNullable<ExamPaperSummary['latestAttempt']>['responses'][number] =>
        response != null && typeof response.score === 'number',
    )
  const scoreValue = scoredResponses.reduce((sum, response) => sum + Number(response.score || 0), 0)
  const scoreLabel = scoredResponses.length > 0 ? `${formatScore(scoreValue)}分` : null

  return {
    isComplete,
    scoreLabel,
  }
}

function formatScore(score: number) {
  if (Number.isInteger(score)) return String(score)
  return score.toFixed(1)
}

function ExamTestCard({
  activeMode,
  activeQuestionFilter,
  onOpenSection,
  paper,
  questionIndex,
}: ExamTestCardProps) {
  const visibleSections = getVisibleSections(
    paper,
    questionIndex,
    activeMode,
    activeQuestionFilter,
  )

  if (visibleSections.length === 0) {
    return null
  }

  return (
    <article className="exam-series-paper">
      <div className="exam-series-paper__top">
        <strong>{paper.title}</strong>
      </div>

      <div className="exam-series-paper__body">
        {visibleSections.map(section => {
          const metrics = buildSectionMetrics(
            paper,
            section.id,
            section.questionCount,
            questionIndex,
          )

          return (
            <button
              key={section.id}
              type="button"
              aria-label={buildSectionLabel(section.sectionType)}
              className="exam-series-paper__row"
              onClick={() => onOpenSection(paper.id, section.sectionType)}
            >
              <span className="exam-series-paper__row-label">
                {buildSectionLabel(section.sectionType)}
              </span>
              {(metrics.isComplete || metrics.scoreLabel) ? (
                <span className="exam-series-paper__row-meta">
                  {metrics.isComplete ? (
                    <span className="exam-series-paper__check" aria-hidden="true" />
                  ) : null}
                  {metrics.scoreLabel ? (
                    <span className="exam-series-paper__score">{metrics.scoreLabel}</span>
                  ) : null}
                </span>
              ) : null}
            </button>
          )
        })}
      </div>
    </article>
  )
}

export default function ExamsLibraryPage() {
  const navigate = useNavigate()
  const { collections, questionIndexMap, loading, error } = useExamsLibraryPage()
  const [activeMode, setActiveMode] = useState<ExamModeFilter>('all')
  const [activeQuestionFilter, setActiveQuestionFilter] = useState<ExamQuestionFilter>('all')

  const visibleCollections = useMemo<ExamCollectionView[]>(
    () =>
      collections
        .map((collection, index) => {
          const papers = collection.papers.filter(
            paper =>
              getVisibleSections(
                paper,
                questionIndexMap[paper.id],
                activeMode,
                activeQuestionFilter,
              ).length > 0,
          )

          return {
            key: collection.key,
            seriesNumberLabel: buildSeriesNumber(collection.title, collection.papers[0]?.seriesNumber),
            papers,
            tone: SERIES_TONES[index % SERIES_TONES.length],
          }
        })
        .filter(collection => collection.papers.length > 0),
    [activeMode, activeQuestionFilter, collections, questionIndexMap],
  )

  function openSection(paperId: number, sectionType: string) {
    navigate(`/exams/${paperId}?section=${sectionType}`)
  }

  if (loading) {
    return (
      <Page className="vocab-book-page exams-library-page">
        <PageContent className="vb-page-body">
          <PageSkeleton variant="books" itemCount={4} />
        </PageContent>
      </Page>
    )
  }

  if (error) {
    return (
      <Page className="vocab-book-page exams-library-page">
        <PageContent className="vb-page-body">
          <EmptyState page title="真题题库加载失败" description={error} />
        </PageContent>
      </Page>
    )
  }

  if (collections.length === 0) {
    return (
      <Page className="vocab-book-page exams-library-page">
        <PageContent className="vb-page-body">
          <EmptyState page title="暂无可用真题" description="当前暂无预置真题可展示。" />
        </PageContent>
      </Page>
    )
  }

  return (
    <Page className="vocab-book-page exams-library-page">
      <PageHeader className="vb-page-header">
        <div className="vb-filters">
          <div className="vb-filter-left">
            <div className="vb-filter-row vb-filter-row--compact">
              {MODE_FILTERS.map(filter => (
                <button
                  key={filter.key}
                  type="button"
                  className={`vb-filter-btn vb-filter-btn--compact${activeMode === filter.key ? ' active' : ''}`}
                  onClick={() => setActiveMode(filter.key)}
                >
                  {filter.label}
                </button>
              ))}
            </div>

            <div className="vb-filter-row vb-filter-row--compact">
              <button type="button" className="vb-filter-btn vb-filter-btn--compact active">
                剑雅
              </button>
            </div>

            <div className="vb-filter-row vb-filter-row--compact">
              {QUESTION_FILTERS.map(filter => (
                <button
                  key={filter.key}
                  type="button"
                  className={`vb-filter-btn vb-filter-btn--compact${activeQuestionFilter === filter.key ? ' active' : ''}`}
                  onClick={() => setActiveQuestionFilter(filter.key)}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </PageHeader>

      <PageContent className="vb-page-body exams-library-page__body">
        <PageScroll className="vb-main">
          {visibleCollections.length === 0 ? (
            <div className="vocab-book-empty">
              <p>当前筛选下没有可展示的真题</p>
            </div>
          ) : (
            <div className="exam-series-list">
              {visibleCollections.map(collection => (
                <section
                  key={collection.key}
                  className="exam-series-group"
                  style={
                    {
                      '--exam-series-accent': collection.tone.accent,
                      '--exam-series-surface': collection.tone.surface,
                    } as CSSProperties
                  }
                >
                  <div className="exam-series-group__header">
                    <span className="exam-series-group__mode">{buildModeBanner(activeMode)}</span>
                    <span className="exam-series-group__kind">Academic</span>
                    <strong>{collection.seriesNumberLabel}</strong>
                  </div>

                  <div className="exam-series-group__grid">
                    {collection.papers.map(paper => (
                      <ExamTestCard
                        key={paper.id}
                        activeMode={activeMode}
                        activeQuestionFilter={activeQuestionFilter}
                        onOpenSection={openSection}
                        paper={paper}
                        questionIndex={questionIndexMap[paper.id]}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </PageScroll>
      </PageContent>
    </Page>
  )
}
