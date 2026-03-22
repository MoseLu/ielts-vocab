import React, { useState, useEffect, useMemo } from 'react'
import { Scrollbar } from './ui/Scrollbar'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

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

interface ChapterProgress {
  is_completed: boolean
  words_learned: number
  accuracy?: number
}

interface Progress {
  current_index?: number
}

interface ChapterModalProps {
  book: Book
  progress: Progress | null
  onClose: () => void
  onSelectChapter: (chapter: Chapter, startIndex: number) => void
  /** Called when chapters API fails — parent can switch to PlanModal */
  onFallback?: () => void
}

// ── Grouping helpers ────────────────────────────────────────────────────────
// Chapters from the CSV layer are named "AWL学术词汇 Sublist 1 · Part 1".
// We split on " · Part " to find the section label.
// Chapters without " · Part " (like "150次及以上", "口语词汇") are standalone.

interface SectionGroup {
  label: string        // full label (or title for standalone)
  isMultiPart: boolean // true when the group has >1 chapters
  wordCount: number
  chapters: Chapter[]
}

function groupBySection(chapters: Chapter[]): SectionGroup[] {
  const groups: SectionGroup[] = []
  const map = new Map<string, SectionGroup>()

  for (const ch of chapters) {
    const sepIdx = ch.title.indexOf(' · Part ')
    const label = sepIdx !== -1 ? ch.title.slice(0, sepIdx) : ch.title

    if (!map.has(label)) {
      const g: SectionGroup = { label, isMultiPart: false, wordCount: 0, chapters: [] }
      map.set(label, g)
      groups.push(g)
    }
    const g = map.get(label)!
    g.chapters.push(ch)
    g.wordCount += ch.word_count ?? 0
  }

  // Mark multi-part groups
  for (const g of groups) {
    g.isMultiPart = g.chapters.length > 1
  }

  return groups
}

// Render units: merge consecutive standalone chapters into a single flat grid;
// multi-part groups keep their own section header + grid.
type RenderUnit =
  | { kind: 'flat'; chapters: Chapter[] }
  | { kind: 'section'; label: string; wordCount: number; chapters: Chapter[] }

function buildRenderUnits(groups: SectionGroup[]): RenderUnit[] {
  const units: RenderUnit[] = []
  let currentFlat: Chapter[] | null = null

  for (const g of groups) {
    if (!g.isMultiPart) {
      // standalone chapter → merge into current flat unit
      if (!currentFlat) {
        currentFlat = []
        units.push({ kind: 'flat', chapters: currentFlat })
      }
      currentFlat.push(g.chapters[0])
    } else {
      // multi-part section → own block, break any flat run
      currentFlat = null
      units.push({ kind: 'section', label: g.label, wordCount: g.wordCount, chapters: g.chapters })
    }
  }

  return units
}

// Within a multi-part group card, show "Part N" only (section header provides context)
function getCardLabel(chapter: Chapter, isInSection: boolean): string {
  if (!isInSection) return chapter.title
  const sepIdx = chapter.title.indexOf(' · Part ')
  return sepIdx !== -1 ? chapter.title.slice(sepIdx + 3) : chapter.title
}
// ───────────────────────────────────────────────────────────────────────────

function ChapterModal({ book, progress, onClose, onSelectChapter, onFallback }: ChapterModalProps) {
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [chapterProgress, setChapterProgress] = useState<Record<string | number, ChapterProgress>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const currentIndex = progress?.current_index || 0

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE}/books/${book.id}/chapters`)
        if (!res.ok) throw new Error('加载章节失败')
        const data = await res.json()
        setChapters(data.chapters || [])

        const token = localStorage.getItem('auth_token')
        if (token) {
          try {
            const pRes = await fetch(`${API_BASE}/books/${book.id}/chapters/progress`, {
              headers: { 'Authorization': `Bearer ${token}` },
            })
            if (pRes.ok) {
              const pData = await pRes.json()
              setChapterProgress(pData.chapter_progress || {})
            }
          } catch { /* ignore */ }
        }
      } catch (err) {
        setError((err as Error).message)
        // Fallback to PlanModal if chapters fail to load
        onFallback?.()
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [book.id, onFallback])

  // Which chapter the user was last working on
  const currentChapterId = useMemo((): string | number | null => {
    if (!chapters.length || currentIndex === 0) return null
    let accumulated = 0
    for (const ch of chapters) {
      accumulated += ch.word_count ?? 0
      if (accumulated > currentIndex) return ch.id
    }
    return chapters[chapters.length - 1]?.id ?? null
  }, [chapters, currentIndex])

  const renderUnits = useMemo(
    () => buildRenderUnits(groupBySection(chapters)),
    [chapters],
  )

  const handleSelectChapter = (chapter: Chapter) => {
    let startIndex = 0
    for (const ch of chapters) {
      if (ch.id === chapter.id) break
      startIndex += ch.word_count ?? 0
    }
    onSelectChapter(chapter, startIndex)
  }

  const handleContinue = () => {
    if (currentChapterId !== null) {
      const ch = chapters.find(c => c.id === currentChapterId)
      if (ch) { handleSelectChapter(ch); return }
    }
    onClose()
  }

  const renderCard = (chapter: Chapter, isInSection: boolean) => {
    const isCurrent  = chapter.id === currentChapterId
    const prog       = chapterProgress[chapter.id]
    const isCompleted = prog?.is_completed
    const hasStarted  = prog && prog.words_learned > 0
    const accuracy    = prog?.accuracy

    return (
      <div
        key={chapter.id}
        className={`chapter-card${isCurrent ? ' current' : ''}${isCompleted ? ' completed' : ''}`}
        onClick={() => handleSelectChapter(chapter)}
      >
        <div className="chapter-card-name">{getCardLabel(chapter, isInSection)}</div>
        <div className="chapter-card-footer">
          <span className="chapter-card-count">{chapter.word_count ?? 0} 词</span>
          {isCompleted ? (
            <span className="chapter-status-done">✓ {accuracy}%</span>
          ) : hasStarted ? (
            <span className="chapter-status-progress">{accuracy}%</span>
          ) : (
            <span className="chapter-status-todo">未开始</span>
          )}
        </div>
        {isCurrent && <div className="chapter-card-current-dot" />}
      </div>
    )
  }

  const totalWords = chapters.reduce((s, c) => s + (c.word_count ?? 0), 0)

  return (
    <div className="chapter-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="chapter-modal">

        {/* ── Header ── */}
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

        {/* ── Body ── */}
        <Scrollbar className="chapter-modal-body">
          {loading ? (
            <div className="chapter-loading">
              <div className="loading-spinner" />
              <span>加载章节...</span>
            </div>
          ) : error ? (
            <div className="chapter-error"><p>{error}</p></div>
          ) : (
            <div className="chapter-units">
              {renderUnits.map((unit, i) =>
                unit.kind === 'flat' ? (
                  /* Standalone chapters — no header, all in one grid */
                  <div key={`flat-${i}`} className="chapter-grid">
                    {unit.chapters.map(ch => renderCard(ch, false))}
                  </div>
                ) : (
                  /* Multi-part section — header + grid */
                  <div key={unit.label} className="chapter-section">
                    <div className="chapter-section-label">
                      <span className="chapter-section-name">{unit.label}</span>
                      <span className="chapter-section-meta">
                        {unit.chapters.length} 节 · {unit.wordCount} 词
                      </span>
                    </div>
                    <div className="chapter-grid">
                      {unit.chapters.map(ch => renderCard(ch, true))}
                    </div>
                  </div>
                )
              )}
            </div>
          )}
        </Scrollbar>
      </div>
    </div>
  )
}

export default ChapterModal
