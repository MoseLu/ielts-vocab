import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../contexts'
import { useResponsiveChapterSkeletonCount } from '../hooks/useResponsiveSkeletonCount'
import { apiFetch, buildApiUrl } from '../lib'
import { Skeleton } from './ui'
import { Scrollbar } from './ui/Scrollbar'
import ConfusableCustomGroupsModal, {
  type CustomConfusableChapter,
} from './practice/ConfusableCustomGroupsModal'

const MODE_META: Record<string, { label: string; title: string }> = {
  quickmemory: { label: '记', title: '速记模式' },
  listening: { label: '听', title: '听音选义' },
  meaning: { label: '想', title: '汉译英' },
  dictation: { label: '默', title: '听写模式' },
  smart: { label: '智', title: '智能模式' },
  match: { label: '连', title: '易混消消乐' },
}

interface Book {
  id: string | number
  title: string
  description?: string
  word_count: number
  practice_mode?: string
}

export interface Chapter {
  id: string | number
  title: string
  word_count?: number
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
  onSelectChapter: (chapter: Chapter, startIndex: number) => void
  onFallback?: () => void
}

interface SectionGroup {
  label: string
  isMultiPart: boolean
  wordCount: number
  chapters: Chapter[]
}

interface ChapterModalSkeletonProps {
  itemCount: number
}

type RenderUnit =
  | { kind: 'flat'; chapters: Chapter[] }
  | { kind: 'section'; label: string; wordCount: number; chapters: Chapter[] }

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
      const group: SectionGroup = { label, isMultiPart: false, wordCount: 0, chapters: [] }
      map.set(label, group)
      groups.push(group)
    }

    const group = map.get(label)!
    group.chapters.push(chapter)
    group.wordCount += chapter.word_count ?? 0
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
  const { user } = useAuth()
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [chapterProgress, setChapterProgress] = useState<Record<string | number, ChapterProgress>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCustomModal, setShowCustomModal] = useState(false)
  const { bodyRef, count: skeletonCount } = useResponsiveChapterSkeletonCount({
    rowMinHeight: 156,
    gap: 10,
    maxRows: 3,
  })

  const currentIndex = progress?.current_index || 0
  const isConfusableBook = String(book.id) === 'ielts_confusable_match'

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
        const response = await fetch(buildApiUrl(`/api/books/${book.id}/chapters`))
        if (!response.ok) throw new Error('加载章节失败')

        const data = await response.json()
        setChapters(data.chapters || [])

        if (user) {
          try {
            const progressData = await apiFetch<{ chapter_progress?: Record<string | number, ChapterProgress> }>(
              buildApiUrl(`/api/books/${book.id}/chapters/progress`),
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

  const renderUnits = useMemo(() => buildRenderUnits(groupBySection(chapters)), [chapters])

  const handleSelect = (chapter: Chapter) => {
    let startIndex = 0
    for (const currentChapter of chapters) {
      if (currentChapter.id === chapter.id) break
      startIndex += currentChapter.word_count ?? 0
    }

    onSelectChapter(chapter, startIndex)
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
    const hasStarted = !!progressRecord && progressRecord.words_learned > 0

    const modeBadges = Object.entries(MODE_META)
      .map(([modeKey, meta]) => {
        const record = progressRecord?.modes?.[modeKey]
        return record ? { modeKey, meta, record } : null
      })
      .filter(Boolean) as { modeKey: string; meta: typeof MODE_META[string]; record: ChapterModeData }[]

    const hasModeData = modeBadges.length > 0
    const allCompleted = hasModeData && modeBadges.every(item => item.record.is_completed)
    const isCompleted = allCompleted || (!hasModeData && !!progressRecord?.is_completed)
    const chapterProgressPercent = hasModeData
      ? progressRecord?.accuracy ?? 0
      : chapter.word_count
        ? Math.round(((progressRecord?.words_learned ?? 0) / chapter.word_count) * 100)
        : 0

    const getAccuracyClass = (accuracy: number) => (
      accuracy >= 80 ? 'mode-badge-high' : accuracy >= 60 ? 'mode-badge-mid' : 'mode-badge-low'
    )

    return (
      <div
        key={chapter.id}
        className={`chapter-card${isCurrent ? ' current' : ''}${isCompleted ? ' completed' : ''}`}
        onClick={() => handleSelect(chapter)}
      >
        {chapter.is_custom && (
          <div className="chapter-card-custom-tag">自定义</div>
        )}
        <div className="chapter-card-name">{getCardLabel(chapter, isInSection)}</div>

        {hasModeData && (
          <div className="chapter-mode-badges">
            {modeBadges.map(({ modeKey, meta, record }) => (
              <span
                key={modeKey}
                className={`mode-badge mode-badge--${modeKey} ${getAccuracyClass(record.accuracy)}`}
                title={`${meta.title}：${record.accuracy}%${record.is_completed ? ' 已完成' : ''}`}
              >
                {meta.label} {record.accuracy}%{record.is_completed ? ' 已完成' : ''}
              </span>
            ))}
          </div>
        )}

        <div className="chapter-card-footer">
          <span className="chapter-card-count">{chapter.word_count ?? 0} 词</span>
          {isCompleted ? (
            <span className="chapter-status-done">已完成 {progressRecord?.accuracy ?? 0}%</span>
          ) : hasStarted ? (
            <span className="chapter-status-progress">{progressRecord?.accuracy ?? 0}%</span>
          ) : (
            <span className="chapter-status-todo">未开始</span>
          )}
        </div>

        <div className="chapter-card-progress">
          <progress className="chapter-card-progress-bar" value={chapterProgressPercent} max={100} />
          <span className="chapter-card-progress-text">{chapterProgressPercent}%</span>
        </div>

        {isCurrent && <div className="chapter-card-current-dot" />}
      </div>
    )
  }

  const totalWords = chapters.reduce((sum, chapter) => sum + (chapter.word_count ?? 0), 0)

  return (
    <div className="chapter-modal-overlay" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <div className="chapter-modal">
        <div className="chapter-modal-header">
          <div className="chapter-modal-info">
            <h2 className="chapter-modal-title">{book.title}</h2>
            <p className="chapter-modal-subtitle">{chapters.length} 章节 · {totalWords} 词</p>
          </div>
          <div className="chapter-modal-actions">
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
                继续学习
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
                          {unit.chapters.length} 节 · {unit.wordCount} 词
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
