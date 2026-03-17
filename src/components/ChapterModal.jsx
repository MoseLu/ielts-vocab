import React, { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

function ChapterModal({ book, progress, onClose, onSelectChapter }) {
  const [chapters, setChapters] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const currentIndex = progress?.current_index || 0

  useEffect(() => {
    const fetchChapters = async () => {
      try {
        const res = await fetch(`${API_BASE}/books/${book.id}/chapters`)
        if (!res.ok) throw new Error('Failed to load chapters')
        const data = await res.json()
        setChapters(data.chapters || [])
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchChapters()
  }, [book.id])

  // Calculate which chapter the user is currently on
  const getCurrentChapterId = () => {
    if (!chapters.length || currentIndex === 0) return null
    let wordCount = 0
    for (const ch of chapters) {
      wordCount += ch.word_count
      if (wordCount > currentIndex) {
        return ch.id
      }
    }
    return chapters[chapters.length - 1]?.id
  }

  const currentChapterId = getCurrentChapterId()

  const handleSelectChapter = (chapter) => {
    // Calculate start index for this chapter
    let startIndex = 0
    for (const ch of chapters) {
      if (ch.id === chapter.id) break
      startIndex += ch.word_count
    }
    onSelectChapter(chapter, startIndex)
  }

  const handleContinue = () => {
    onClose()
  }

  return (
    <div className="chapter-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="chapter-modal">
        <div className="chapter-modal-header">
          <div className="chapter-modal-info">
            <h2 className="chapter-modal-title">{book.title}</h2>
            <p className="chapter-modal-subtitle">
              {book.word_count} 词 · {chapters.length} 章节
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
            <div className="chapter-grid">
              {chapters.map(chapter => {
                const isCurrent = chapter.id === currentChapterId
                return (
                  <div
                    key={chapter.id}
                    className={`chapter-card${isCurrent ? ' current' : ''}`}
                    onClick={() => handleSelectChapter(chapter)}
                  >
                    <div className="chapter-card-name">{chapter.title}</div>
                    <div className="chapter-card-count">{chapter.word_count} 词</div>
                    {isCurrent && <div className="chapter-card-recent">当前</div>}
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