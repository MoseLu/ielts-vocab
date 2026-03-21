import React, { useState, useEffect, useMemo } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

interface Book {
  id: string | number
  title: string
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

// ── Section grouping helpers ────────────────────────────────────────────────
// Chapters may be named "AWL学术词汇 Sublist 1 · Part 1" — we group by the
// label before " · Part " so they appear under a shared section header.

function getSectionLabel(title: string): string {
  const idx = title.indexOf(' · Part ')
  return idx !== -1 ? title.slice(0, idx) : title
}

function getCardTitle(title: string): string {
  const idx = title.indexOf(' · Part ')
  return idx !== -1 ? title.slice(idx + 3) : title  // "Part N"
}

interface SectionGroup {
  label: string
  wordCount: number
  chapters: Chapter[]
}

function groupBySection(chapters: Chapter[]): SectionGroup[] {
  const groups: SectionGroup[] = []
  const map = new Map<string, SectionGroup>()

  for (const ch of chapters) {
    const label = getSectionLabel(ch.title)
    if (!map.has(label)) {
      const g: SectionGroup = { label, wordCount: 0, chapters: [] }
      map.set(label, g)
      groups.push(g)
    }
    const g = map.get(label)!
    g.chapters.push(ch)
    g.wordCount += ch.word_count ?? 0
  }
  return groups
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
        const chaptersRes = await fetch(`${API_BASE}/books/${book.id}/chapters`)
        if (!chaptersRes.ok) throw new Error('Failed to load chapters')
        const chaptersData = await chaptersRes.json()
        setChapters(chaptersData.chapters || [])

        const token = localStorage.getItem('auth_token')
        if (token) {
          try {
            const progressRes = await fetch(`${API_BASE}/books/${book.id}/chapters/progress`, {
              headers: { 'Authorization': `Bearer ${token}` }
            })
            if (progressRes.ok) {
              const progressData = await progressRes.json()
              setChapterProgress(progressData.chapter_progress || {})
            }
          } catch {
            // Ignore progress fetch errors
          }
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

  // Calculate which chapter the user is currently on based on total word index
  const currentChapterId = useMemo((): string | number | null => {
    if (!chapters.length || currentIndex === 0) return null
    let accumulated = 0
    for (const ch of chapters) {
      accumulated += ch.word_count ?? 0
      if (accumulated > currentIndex) return ch.id
    }
    return chapters[chapters.length - 1]?.id ?? null
  }, [chapters, currentIndex])

  const groups = useMemo(() => groupBySection(chapters), [chapters])

  const handleSelectChapter = (chapter: Chapter) => {
    let startIndex = 0
    for (const ch of chapters) {
      if (ch.id === chapter.id) break
      startIndex += ch.word_count ?? 0
    }
    onSelectChapter(chapter, startIndex)
  }

  // "继续学习" — navigate to the chapter the user was last on
  const handleContinue = () => {
    if (currentChapterId !== null) {
      const chapter = chapters.find(ch => ch.id === currentChapterId)
      if (chapter) {
        handleSelectChapter(chapter)
        return
      }
    }
    onClose()
  }

  const totalWords = chapters.reduce((s, c) => s + (c.word_count ?? 0), 0)

  return (
    <div className="chapter-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="chapter-modal">
        {/* Header */}
        <div className="chapter-modal-header">
          <div className="chapter-modal-info">
            <h2 className="chapter-modal-title">{book.title}</h2>
            <p className="chapter-modal-subtitle">
              {totalWords} 词 · {chapters.length} 章节
            </p>
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

        {/* Body */}
        <div className="chapter-modal-body">
          {loading ? (
            <div className="chapter-loading">
              <div className="loading-spinner" />
              <span>加载章节...</span>
            </div>
          ) : error ? (
            <div className="chapter-error">
              <p>加载失败: {error}</p>
            </div>
          ) : (
            <div className="chapter-sections">
              {groups.map(group => {
                const isMultiPart = group.chapters.length > 1

                return (
                  <div key={group.label} className="chapter-section">
                    {/* Section header — only when there are multiple groups */}
                    {groups.length > 1 && (
                      <div className="chapter-section-label">
                        <span className="chapter-section-name">{group.label}</span>
                        <span className="chapter-section-meta">
                          {isMultiPart ? `${group.chapters.length} 节 · ` : ''}
                          {group.wordCount} 词
                        </span>
                      </div>
                    )}

                    <div className="chapter-grid">
                      {group.chapters.map(chapter => {
                        const isCurrent = chapter.id === currentChapterId
                        const chProgress = chapterProgress[chapter.id]
                        const isCompleted = chProgress?.is_completed
                        const accuracy = chProgress?.accuracy
                        const hasStarted = chProgress && chProgress.words_learned > 0

                        // In a multi-part group, abbreviate to "Part N" for conciseness
                        const displayTitle = isMultiPart
                          ? getCardTitle(chapter.title)
                          : chapter.title

                        return (
                          <div
                            key={chapter.id}
                            className={`chapter-card${isCurrent ? ' current' : ''}${isCompleted ? ' completed' : ''}`}
                            onClick={() => handleSelectChapter(chapter)}
                          >
                            <div className="chapter-card-name">{displayTitle}</div>
                            <div className="chapter-card-count">{chapter.word_count} 词</div>
                            <div className="chapter-card-status">
                              {isCompleted ? (
                                <span className="chapter-status-done">✓ {accuracy}%</span>
                              ) : hasStarted ? (
                                <span className="chapter-status-progress">学习中 {accuracy}%</span>
                              ) : (
                                <span className="chapter-status-todo">未开始</span>
                              )}
                            </div>
                            {isCurrent && <div className="chapter-card-recent">当前</div>}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ChapterModal
