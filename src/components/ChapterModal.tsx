import React, { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../contexts'
import { apiFetch, buildApiUrl } from '../lib'
import { Scrollbar } from './ui/Scrollbar'

const MODE_META: Record<string, { label: string; title: string }> = {
  quickmemory: { label: '记', title: '快速记忆' },
  listening: { label: '听', title: '听音选义' },
  meaning: { label: '看', title: '看词选义' },
  dictation: { label: '默', title: '听写模式' },
  smart: { label: '智', title: '智能模式' },
}

interface Book {
  id: string | number
  title: string
  description?: string
  word_count: number
}

export interface Chapter {
  id: string | number
  title: string
  word_count?: number
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

function groupBySection(chapters: Chapter[]): SectionGroup[] {
  const groups: SectionGroup[] = []
  const map = new Map<string, SectionGroup>()

  for (const chapter of chapters) {
    const separatorIndex = chapter.title.indexOf(' 路 Part ')
    const label = separatorIndex !== -1 ? chapter.title.slice(0, separatorIndex) : chapter.title

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

type RenderUnit =
  | { kind: 'flat'; chapters: Chapter[] }
  | { kind: 'section'; label: string; wordCount: number; chapters: Chapter[] }

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
  const separatorIndex = chapter.title.indexOf(' 路 Part ')
  return separatorIndex !== -1 ? chapter.title.slice(separatorIndex + 3) : chapter.title
}

function ChapterModal({ book, progress, onClose, onSelectChapter, onFallback }: ChapterModalProps) {
  const { user } = useAuth()
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [chapterProgress, setChapterProgress] = useState<Record<string | number, ChapterProgress>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const currentIndex = progress?.current_index || 0

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

  const handleSelectChapter = (chapter: Chapter) => {
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
        handleSelectChapter(chapter)
        return
      }
    }

    onClose()
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

    const getAccuracyClass = (accuracy: number) =>
      accuracy >= 80 ? 'mode-badge-high' : accuracy >= 60 ? 'mode-badge-mid' : 'mode-badge-low'

    const chapterProgressPercent = hasModeData
      ? (progressRecord?.accuracy ?? 0)
      : (chapter.word_count
        ? Math.round(((progressRecord?.words_learned ?? 0) / chapter.word_count) * 100)
        : 0)

    return (
      <div
        key={chapter.id}
        className={`chapter-card${isCurrent ? ' current' : ''}${isCompleted ? ' completed' : ''}`}
        onClick={() => handleSelectChapter(chapter)}
      >
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
            <span className="chapter-status-done">已完成 {progressRecord?.accuracy}%</span>
          ) : hasStarted ? (
            <span className="chapter-status-progress">{progressRecord?.accuracy}%</span>
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

        <Scrollbar className="chapter-modal-body">
          {loading ? (
            <div className="chapter-loading loading-state">
              <div className="loading-spinner" />
              <span>加载章节...</span>
            </div>
          ) : error ? (
            <div className="chapter-error"><p>{error}</p></div>
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
  )
}

export default ChapterModal
