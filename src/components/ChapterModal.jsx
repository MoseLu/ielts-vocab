import React, { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

function ChapterModal({ book, progress, onClose, onSelectChapter }) {
  const [chapters, setChapters] = useState([])
  const [chapterProgress, setChapterProgress] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const currentIndex = progress?.current_index || 0

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch chapters
        const chaptersRes = await fetch(`${API_BASE}/books/${book.id}/chapters`)
        if (!chaptersRes.ok) throw new Error('Failed to load chapters')
        const chaptersData = await chaptersRes.json()
        setChapters(chaptersData.chapters || [])

        // Fetch chapter progress (if user is logged in)
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
          } catch (e) {
            // Ignore progress fetch errors
          }
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
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
                const chProgress = chapterProgress[chapter.id]
                const isCompleted = chProgress?.is_completed
                const accuracy = chProgress?.accuracy
                const hasStarted = chProgress && chProgress.words_learned > 0

                return (
                  <div
                    key={chapter.id}
                    className={`chapter-card${isCurrent ? ' current' : ''}${isCompleted ? ' completed' : ''}`}
                    onClick={() => handleSelectChapter(chapter)}
                  >
                    <div className="chapter-card-name">{chapter.title}</div>
                    <div className="chapter-card-count">{chapter.word_count} 词</div>
                    <div className="chapter-card-status">
                      {isCompleted ? (
                        <span className="chapter-status-done">正确率: {accuracy}%</span>
                      ) : hasStarted ? (
                        <span className="chapter-status-progress">学习中 {accuracy}%</span>
                      ) : (
                        <span className="chapter-status-todo">未完成</span>
                      )}
                    </div>
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