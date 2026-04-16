import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { ExamPaperSummary } from '../../../lib'
import { useExamsLibraryPage } from '../../../composables/exams/page/useExamsLibraryPage'
import { Page, PageContent, PageHeader, PageScroll } from '../../layout'
import { EmptyState, PageSkeleton } from '../../ui'


type ExamModeFilter = 'all' | 'listening' | 'reading' | 'writing' | 'speaking'

interface ExamLibraryPaperItem {
  collectionKey: string
  collectionLabel: string
  paper: ExamPaperSummary
}

const MODE_FILTERS: Array<{ key: ExamModeFilter; label: string }> = [
  { key: 'all', label: '套题模考' },
  { key: 'listening', label: '听力' },
  { key: 'reading', label: '阅读' },
  { key: 'writing', label: '写作' },
  { key: 'speaking', label: '口语' },
]

function buildAttemptLabel(status: string | undefined) {
  if (status === 'in_progress') return '继续模考'
  if (status === 'submitted') return '重新模考'
  return '进入模块'
}

function buildStatusCopy(status: string | undefined, objectiveCorrect?: number, objectiveTotal?: number) {
  if (status === 'in_progress') return '进行中'
  if (status === 'submitted' && objectiveTotal && objectiveTotal > 0) {
    return `${objectiveCorrect || 0}/${objectiveTotal}`
  }
  if (status === 'submitted') return '已提交'
  return '未开始'
}

function buildSectionMeta(sectionType: string, questionCount: number, audioCount: number) {
  if (sectionType === 'listening') return `含 ${audioCount || 0} 段音频 · ${questionCount} 题`
  if (sectionType === 'speaking') return `独立口语 · ${questionCount} 题`
  if (sectionType === 'writing') return `写作任务 · ${questionCount} 题`
  return `${questionCount} 题`
}

function buildCollectionLabel(title: string, seriesNumber?: number | null) {
  if (seriesNumber) return `剑雅${seriesNumber}`

  const normalized = title.replace(/\s+/g, ' ').trim()
  const digitMatch = normalized.match(/(\d+)/)
  if (digitMatch) return `剑雅${digitMatch[1]}`
  return normalized.replace(/IELTS\s*Academic/i, '剑雅')
}

function resolveLandingSectionType(paper: ExamPaperSummary, activeMode: ExamModeFilter) {
  if (activeMode !== 'all') {
    const matched = paper.sections.find(section => section.sectionType === activeMode)
    if (matched) return matched.sectionType
  }

  return paper.sections[0]?.sectionType ?? 'reading'
}

interface ExamLibraryCardProps {
  activeMode: ExamModeFilter
  collectionLabel: string
  onOpenSection: (paperId: number, sectionType: string) => void
  paper: ExamPaperSummary
}

function ExamLibraryCard({
  activeMode,
  collectionLabel,
  onOpenSection,
  paper,
}: ExamLibraryCardProps) {
  const visibleSections = paper.sections.filter(
    section => activeMode === 'all' || section.sectionType === activeMode,
  )
  const summaryText = paper.hasListeningAudio ? '听力音频已预置' : '听力音频待补齐'
  const statusText = buildStatusCopy(
    paper.latestAttempt?.status,
    paper.latestAttempt?.objectiveCorrect,
    paper.latestAttempt?.objectiveTotal,
  )
  const statusTone = paper.latestAttempt?.status ?? 'idle'
  const landingSection = resolveLandingSectionType(paper, activeMode)

  return (
    <article className="vb-card exam-vb-card">
      <div className="exam-vb-card__header">
        <div className="exam-vb-card__heading">
          <span className="exam-vb-card__collection">{collectionLabel}</span>
          <h3 className="vb-card-title">{paper.title}</h3>
        </div>
        <span className={`exam-vb-card__status is-${statusTone}`}>{statusText}</span>
      </div>

      <div className="vb-card-meta exam-vb-card__meta">
        <span className="vb-card-count">{paper.sections.length} 个模块</span>
        <span className="vb-card-desc">{summaryText}</span>
      </div>

      <div className="exam-vb-card__sections">
        {visibleSections.map(section => (
          <button
            key={section.id}
            type="button"
            className="exam-vb-card__section"
            onClick={() => onOpenSection(paper.id, section.sectionType)}
          >
            <span className="exam-vb-card__section-copy">
              <strong>{section.title}</strong>
              <span>{buildSectionMeta(section.sectionType, section.questionCount, section.audioTracks.length)}</span>
            </span>
            <span className="exam-vb-card__section-action">{buildAttemptLabel(paper.latestAttempt?.status)}</span>
          </button>
        ))}
      </div>

      {activeMode === 'all' && visibleSections.length > 1 && (
        <button
          type="button"
          className="exam-vb-card__paper-entry"
          onClick={() => onOpenSection(paper.id, landingSection)}
        >
          按默认顺序进入
        </button>
      )}
    </article>
  )
}

export default function ExamsLibraryPage() {
  const navigate = useNavigate()
  const { collections, loading, error } = useExamsLibraryPage()
  const [activeMode, setActiveMode] = useState<ExamModeFilter>('all')
  const [activeCollectionKey, setActiveCollectionKey] = useState<string>('all')

  const libraryPapers = useMemo<ExamLibraryPaperItem[]>(
    () =>
      collections.flatMap(collection =>
        collection.papers.map(paper => ({
          collectionKey: collection.key,
          collectionLabel: buildCollectionLabel(collection.title, paper.seriesNumber),
          paper,
        })),
      ),
    [collections],
  )

  const collectionFilters = useMemo(
    () => [
      { key: 'all', label: '全部' },
      ...collections.map(collection => ({
        key: collection.key,
        label: buildCollectionLabel(collection.title, collection.papers[0]?.seriesNumber),
      })),
    ],
    [collections],
  )

  const visiblePapers = useMemo(
    () =>
      libraryPapers.filter(({ collectionKey, paper }) => {
        const matchesCollection = activeCollectionKey === 'all' || collectionKey === activeCollectionKey
        const matchesMode = activeMode === 'all' || paper.sections.some(section => section.sectionType === activeMode)
        return matchesCollection && matchesMode
      }),
    [activeCollectionKey, activeMode, libraryPapers],
  )

  const totalPaperCount = libraryPapers.length

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
              <span className="exam-library-source-note">当前仅展示学术类剑雅真题</span>
            </div>

            <div className="vb-filter-row vb-filter-row--compact">
              {collectionFilters.map(filter => (
                <button
                  key={filter.key}
                  type="button"
                  className={`vb-filter-btn vb-filter-btn--compact${activeCollectionKey === filter.key ? ' active' : ''}`}
                  onClick={() => setActiveCollectionKey(filter.key)}
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
          <div className="exams-library-meta">
            <span>{visiblePapers.length} / {totalPaperCount} 套真题</span>
            <span>Academic Only</span>
          </div>

          {visiblePapers.length === 0 ? (
            <div className="vocab-book-empty">
              <p>当前筛选下没有可展示的真题</p>
            </div>
          ) : (
            <div className="vb-grid exams-vb-grid">
              {visiblePapers.map(({ collectionLabel, paper }) => (
                <ExamLibraryCard
                  key={paper.id}
                  activeMode={activeMode}
                  collectionLabel={collectionLabel}
                  onOpenSection={openSection}
                  paper={paper}
                />
              ))}
            </div>
          )}
        </PageScroll>
      </PageContent>
    </Page>
  )
}
