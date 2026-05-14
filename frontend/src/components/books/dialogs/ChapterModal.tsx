import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../../contexts'
import {
  CHAPTER_PRACTICE_MODE_META,
  SPECIAL_BOOK_MODE_META,
} from '../../../constants/practiceModes'
import { useResponsiveChapterSkeletonCount } from '../../../hooks/useResponsiveSkeletonCount'
import { apiFetch } from '../../../lib'
import type { BookEntryMode } from '../../../lib'
import { Skeleton } from '../../ui'
import { Scrollbar } from '../../ui/Scrollbar'
import ConfusableCustomGroupsModal from '../../practice/ConfusableCustomGroupsModal'
import type { CustomConfusableChapter } from '../../../features/practice/confusableCustomGroups'
import ChapterModeCharts from './ChapterModeCharts'

const MODE_META: Record<string, { label: string; title: string }> = {
  ...CHAPTER_PRACTICE_MODE_META,
  ...SPECIAL_BOOK_MODE_META,
}

interface Book {
  id: string | number
  title: string
  description?: string
  word_count: number
  chapter_count?: number
  group_count?: number
  is_custom_book?: boolean
  practice_mode?: string
}

export interface Chapter {
  id: string | number
  title: string
  word_count?: number
  group_count?: number
  is_custom?: boolean
}

interface ChapterModeData {
  mode: string
  correct_count: number
  wrong_count: number
  accuracy: number
  is_completed: boolean
}

interface ChapterProgress {
  is_completed: boolean
  words_learned: number
  accuracy?: number
  modes?: Record<string, ChapterModeData>
}

interface Progress {
  current_index?: number
}

interface ChapterModalProps {
  book: Book
  progress: Progress | null
  onClose: () => void
  onSelectChapter: (chapter: Chapter, startIndex: number, entryMode?: BookEntryMode) => void
  onFallback?: () => void
}

interface SectionGroup {
  label: string
  isMultiPart: boolean
  wordCount: number
  groupCount: number
  chapters: Chapter[]
}

interface ChapterModalSkeletonProps {
  itemCount: number
}

type RenderUnit =
  | { kind: 'flat'; chapters: Chapter[] }
  | { kind: 'section'; label: string; wordCount: number; groupCount: number; chapters: Chapter[] }

const ENTRY_MODE_META: Record<BookEntryMode, { title: string; description: string }> = {
  practice: {
    title: '常规练习',
    description: '进入单项训练模式，按你选择的练习方式推进。',
  },
  game: {
    title: '游戏闯关',
    description: '进入独立的五维闯关入口，在同一词上串联认义听说写。',
  },
}

function findPartSeparatorIndex(title: string): number {
  const match = title.match(/\s+[·•]\s+Part\s+/i)
  if (!match || match.index == null) return -1
  return match.index
}

function groupBySection(chapters: Chapter[]): SectionGroup[] {
  const groups: SectionGroup[] = []
  const map = new Map<string, SectionGroup>()

  for (const chapter of chapters) {
    const separatorIndex = findPartSeparatorIndex(chapter.title)
    const label = separatorIndex !== -1 ? chapter.title.slice(0, separatorIndex).trim() : chapter.title

    if (!map.has(label)) {
      const group: SectionGroup = {
        label,
        isMultiPart: false,
        wordCount: 0,
        groupCount: 0,
        chapters: [],
      }
      map.set(label, group)
      groups.push(group)
    }

    const group = map.get(label)!
    group.chapters.push(chapter)
    group.wordCount += chapter.word_count ?? 0
    group.groupCount += chapter.group_count ?? 0
  }

  for (const group of groups) {
    group.isMultiPart = group.chapters.length > 1
  }

  return groups
}

function buildRenderUnits(groups: SectionGroup[]): RenderUnit[] {
  const units: RenderUnit[] = []
  let currentFlat: Chapter[] | null = null

  for (const group of groups) {
    if (!group.isMultiPart) {
      if (!currentFlat) {
        currentFlat = []
        units.push({ kind: 'flat', chapters: currentFlat })
      }
      currentFlat.push(group.chapters[0])
      continue
    }

    currentFlat = null
    units.push({
      kind: 'section',
      label: group.label,
      wordCount: group.wordCount,
      groupCount: group.groupCount,
      chapters: group.chapters,
    })
  }

  return units
}

function getCardLabel(chapter: Chapter, isInSection: boolean): string {
  if (!isInSection) return chapter.title
  const separatorMatch = chapter.title.match(/Part\s+.+$/i)
  return separatorMatch ? separatorMatch[0] : chapter.title
}

function ChapterModalSkeleton({ itemCount }: ChapterModalSkeletonProps) {
  return (
    <div className="chapter-skeleton chapter-loading--centered" aria-hidden="true">
      <div className="chapter-skeleton-grid">
        {Array.from({ length: itemCount }, (_, index) => (
          <div key={index} className="chapter-skeleton-card">
            <Skeleton width="58%" height={18} />
            <div className="chapter-skeleton-tags">
              <Skeleton width="28%" height={12} />
              <Skeleton width="24%" height={12} />
            </div>
            <div className="chapter-skeleton-footer">
              <Skeleton width="32%" height={12} />
              <Skeleton width="18%" height={12} />
            </div>
            <Skeleton variant="rectangular" width="100%" height={8} />
          </div>
        ))}
      </div>
    </div>
  )
}

function ChapterModal({ book, progress, onClose, onSelectChapter, onFallback }: ChapterModalProps) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [chapterProgress, setChapterProgress] = useState<Record<string | number, ChapterProgress>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCustomModal, setShowCustomModal] = useState(false)
  const [entryMode, setEntryMode] = useState<BookEntryMode>('practice')
  const { bodyRef, count: skeletonCount } = useResponsiveChapterSkeletonCount({
    rowMinHeight: 156,
    gap: 10,
    maxRows: 3,
  })

  const currentIndex = progress?.current_index || 0
  const isConfusableBook = String(book.id) === 'ielts_confusable_match'
  const isCustomBook = !!book.is_custom_book && !isConfusableBook
  const supportsGameEntry = !isConfusableBook && book.practice_mode !== 'match'
  const activeEntryMode: BookEntryMode = supportsGameEntry ? entryMode : 'practice'

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await apiFetch<{ chapters?: Chapter[] }>(`/api/books/${book.id}/chapters`)
        setChapters(data.chapters || [])

        if (user) {
          try {
            const progressData = await apiFetch<{ chapter_progress?: Record<string | number, ChapterProgress> }>(
              `/api/books/${book.id}/chapters/progress`,
            )
            setChapterProgress(progressData.chapter_progress || {})
          } catch {
            // Ignore progress fetch failure and keep the chapter list usable.
          }
        }
      } catch (err) {
        setError((err as Error).message)
        onFallback?.()
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [book.id, onFallback, user])

  const currentChapterId = useMemo((): string | number | null => {
    if (!chapters.length || currentIndex === 0) return null

    let accumulated = 0
    for (const chapter of chapters) {
      accumulated += chapter.word_count ?? 0
      if (accumulated > currentIndex) return chapter.id
    }

    return chapters[chapters.length - 1]?.id ?? null
  }, [chapters, currentIndex])

  const chapterStartIndexById = useMemo(() => {
    const startIndexById: Record<string, number> = {}
    let accumulated = 0
    for (const chapter of chapters) {
      startIndexById[String(chapter.id)] = accumulated
      accumulated += chapter.word_count ?? 0
    }
    return startIndexById
  }, [chapters])

  const renderUnits = useMemo(() => buildRenderUnits(groupBySection(chapters)), [chapters])
  const hasAnyChapterProgress = Object.keys(chapterProgress).length > 0

  const handleSelect = (chapter: Chapter) => {
    let startIndex = 0
    for (const currentChapter of chapters) {
      if (currentChapter.id === chapter.id) break
      startIndex += currentChapter.word_count ?? 0
    }

    onSelectChapter(chapter, startIndex, activeEntryMode)
  }

  const handleContinue = () => {
    if (currentChapterId !== null) {
      const chapter = chapters.find(item => item.id === currentChapterId)
      if (chapter) {
        handleSelect(chapter)
        return
      }
    }

    onClose()
  }

  const handleCustomCreated = (createdChapters: CustomConfusableChapter[]) => {
    if (!createdChapters.length) return

    setChapters(previous => {
      const existingIds = new Set(previous.map(chapter => String(chapter.id)))
      const appended = createdChapters.filter(chapter => !existingIds.has(String(chapter.id)))
      return [...previous, ...appended]
    })

    const firstCreated = createdChapters[0]
    const startIndex = chapters.reduce((sum, chapter) => sum + (chapter.word_count ?? 0), 0)
    onSelectChapter(firstCreated, startIndex)
  }

  const renderCard = (chapter: Chapter, isInSection: boolean) => {
    const isCurrent = chapter.id === currentChapterId
    const progressRecord = chapterProgress[chapter.id] ?? chapterProgress[String(chapter.id)]
    const displayCount = isConfusableBook ? chapter.group_count ?? 0 : chapter.word_count ?? 0
    const displayUnit = isConfusableBook ? '组' : '词'
    const progressTotal = isConfusableBook ? chapter.group_count ?? chapter.word_count ?? 0 : chapter.word_count ?? 0
    const bookCoverageLearnedCount = hasAnyChapterProgress
      ? 0
      : Math.max(0, Math.min(progressTotal, currentIndex - (chapterStartIndexById[String(chapter.id)] ?? 0)))
    const learnedCount = Math.max(0, progressRecord?.words_learned ?? 0, bookCoverageLearnedCount)
    const modeRecords = Object.values(progressRecord?.modes ?? {})
    const hasStarted = learnedCount > 0 || modeRecords.some(record => (record.correct_count ?? 0) + (record.wrong_count ?? 0) > 0)
    const hasModeData = modeRecords.length > 0
    const allCompleted = hasModeData && modeRecords.every(record => record.is_completed)
    const isCoverageComplete = progressTotal > 0 && learnedCount >= progressTotal
    const isCompleted = !!progressRecord?.is_completed || allCompleted || isCoverageComplete
    const chapterProgressPercent = isCompleted
      ? 100
      : progressTotal
        ? Math.min(100, Math.round((learnedCount / progressTotal) * 100))
        : 0
    const accuracyText = `正确率 ${progressRecord?.accuracy ?? 0}%`

    return (
      <div
        key={chapter.id}
        className={`chapter-card${isCurrent ? ' current' : ''}${isCompleted ? ' completed' : hasStarted ? ' in-progress' : ' not-started'}`}
        onClick={() => handleSelect(chapter)}
      >
        {chapter.is_custom && (
          <div className="chapter-card-custom-tag">自定义</div>
        )}
        <div className="chapter-card-name">{getCardLabel(chapter, isInSection)}</div>

        <ChapterModeCharts
          modeMeta={MODE_META}
          modes={progressRecord?.modes}
          completionPercent={chapterProgressPercent}
        />

        <div className="chapter-card-footer">
          <span className="chapter-card-count">{displayCount} {displayUnit}</span>
          {isCompleted ? (
            <span className="chapter-status-done">{hasModeData ? '已完成' : `已完成 · ${accuracyText}`}</span>
          ) : hasStarted ? (
            <span className="chapter-status-progress">{hasModeData ? '学习中' : `学习中 · ${accuracyText}`}</span>
          ) : (
            <span className="chapter-status-todo">未开始</span>
          )}
        </div>

        {isCurrent && <div className="chapter-card-current-dot" />}
      </div>
    )
  }

  const totalWords = isCustomBook
    ? Math.max(0, Number(book.word_count) || 0)
    : chapters.reduce((sum, chapter) => sum + (chapter.word_count ?? 0), 0)
  const totalGroups = chapters.reduce((sum, chapter) => sum + (chapter.group_count ?? 0), 0)
  const subtitle = isConfusableBook
    ? `${chapters.length} 章节 · ${totalGroups} 组`
    : `${chapters.length} 章节 · ${totalWords} 词`

  return (
    <div className="chapter-modal-overlay" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <div className="chapter-modal">
        <div className="chapter-modal-header">
          <div className="chapter-modal-info">
            <h2 className="chapter-modal-title">{book.title}</h2>
            <p className="chapter-modal-subtitle">{subtitle}</p>
            {supportsGameEntry && (
              <>
                <div className="chapter-entry-switch" role="tablist" aria-label="学习入口">
                  {(Object.entries(ENTRY_MODE_META) as [BookEntryMode, { title: string; description: string }][]).map(([mode, meta]) => (
                    <button
                      key={mode}
                      type="button"
                      role="tab"
                      aria-selected={activeEntryMode === mode}
                      className={`chapter-entry-switch__option${activeEntryMode === mode ? ' is-active' : ''}`}
                      onClick={() => setEntryMode(mode)}
                    >
                      {meta.title}
                    </button>
                  ))}
                </div>
                <p className="chapter-entry-note">{ENTRY_MODE_META[activeEntryMode].description}</p>
              </>
            )}
          </div>
          <div className="chapter-modal-actions">
            {isCustomBook && (
              <button
                className="chapter-continue-btn"
                onClick={() => navigate(`/books/create?bookId=${encodeURIComponent(String(book.id))}`)}
              >
                编辑词书
              </button>
            )}
            {isConfusableBook && (
              <button
                className="chapter-continue-btn"
                onClick={() => setShowCustomModal(true)}
              >
                自定义组
              </button>
            )}
            {currentIndex > 0 && (
              <button className="chapter-continue-btn" onClick={handleContinue}>
                {activeEntryMode === 'game' ? '继续闯关' : '继续学习'}
              </button>
            )}
            <button className="chapter-modal-close" onClick={onClose}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <div className="chapter-modal-body" ref={bodyRef}>
          <Scrollbar wrapClassName="chapter-modal-scroll-wrap">
            {loading ? (
              <ChapterModalSkeleton itemCount={skeletonCount} />
            ) : error ? (
              <div className="chapter-error chapter-loading--centered"><p>{error}</p></div>
            ) : (
              <div className="chapter-units">
                {renderUnits.map((unit, index) =>
                  unit.kind === 'flat' ? (
                    <div key={`flat-${index}`} className="chapter-grid">
                      {unit.chapters.map(chapter => renderCard(chapter, false))}
                    </div>
                  ) : (
                    <div key={unit.label} className="chapter-section">
                      <div className="chapter-section-label">
                        <span className="chapter-section-name">{unit.label}</span>
                        <span className="chapter-section-meta">
                          {unit.chapters.length} 节 · {isConfusableBook ? `${unit.groupCount} 组` : `${unit.wordCount} 词`}
                        </span>
                      </div>
                      <div className="chapter-grid">
                        {unit.chapters.map(chapter => renderCard(chapter, true))}
                      </div>
                    </div>
                  ),
                )}
              </div>
            )}
          </Scrollbar>
        </div>
      </div>

      {isConfusableBook && (
        <ConfusableCustomGroupsModal
          isOpen={showCustomModal}
          onClose={() => setShowCustomModal(false)}
          onCreated={handleCustomCreated}
        />
      )}
    </div>
  )
}

export default ChapterModal
