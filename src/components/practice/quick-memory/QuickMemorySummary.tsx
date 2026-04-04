import type { Word } from '../types'

export interface QuickMemorySessionResult {
  wordIdx: number
  choice: 'known' | 'unknown'
  wasFuzzy: boolean
}

interface QuickMemorySummaryProps {
  results: QuickMemorySessionResult[]
  vocabulary: Word[]
  queue: number[]
  bookId: string | null
  chapterId: string | null
  bookChapters: { id: number | string; title: string }[]
  reviewMode?: boolean
  reviewHasMore?: boolean
  onContinueReview?: () => void
  buildChapterPath?: (chapterId: string | number) => string
  onRestart: () => void
  onModeChange: (mode: string) => void
  onNavigate: (path: string) => void
}

export function QuickMemorySummary({
  results,
  vocabulary,
  queue,
  bookId,
  chapterId,
  bookChapters,
  reviewMode,
  reviewHasMore,
  onContinueReview,
  buildChapterPath,
  onRestart,
  onModeChange,
  onNavigate,
}: QuickMemorySummaryProps) {
  const known = results.filter(result => result.choice === 'known')
  const unknown = results.filter(result => result.choice === 'unknown')
  const fuzzy = results.filter(result => result.wasFuzzy)
  const currentChapterIndex = bookChapters.findIndex(chapter => String(chapter.id) === String(chapterId))
  const nextChapter = currentChapterIndex >= 0 && currentChapterIndex < bookChapters.length - 1
    ? bookChapters[currentChapterIndex + 1]
    : null
  const accuracy = results.length > 0 ? Math.round((known.length / results.length) * 100) : 0

  return (
    <div className="qm-summary">
      <div className="qm-summary-title">本轮完成</div>
      <div className="qm-summary-stats">
        <div className="qm-stat qm-stat-known">
          <span className="qm-stat-num">{known.length}</span>
          <span className="qm-stat-label">认识</span>
        </div>
        <div className="qm-stat qm-stat-unknown">
          <span className="qm-stat-num">{unknown.length}</span>
          <span className="qm-stat-label">不认识</span>
        </div>
        {fuzzy.length > 0 && (
          <div className="qm-stat qm-stat-fuzzy">
            <span className="qm-stat-num">{fuzzy.length}</span>
            <span className="qm-stat-label">模糊</span>
          </div>
        )}
        <div className="qm-stat">
          <span className="qm-stat-num">{accuracy}%</span>
          <span className="qm-stat-label">正确率</span>
        </div>
      </div>

      {fuzzy.length > 0 && (
        <div className="qm-summary-section">
          <div className="qm-summary-section-title">模糊单词（回退重答）</div>
          <div className="qm-summary-word-list">
            {fuzzy.map(result => {
              const word = vocabulary[queue[result.wordIdx]]
              return word ? (
                <span key={result.wordIdx} className="qm-summary-word-tag qm-summary-word-fuzzy">
                  {word.word}
                </span>
              ) : null
            })}
          </div>
        </div>
      )}

      {unknown.length > 0 && (
        <div className="qm-summary-section">
          <div className="qm-summary-section-title">需要复习</div>
          <div className="qm-summary-word-list">
            {unknown.map(result => {
              const word = vocabulary[queue[result.wordIdx]]
              return word ? (
                <span
                  key={result.wordIdx}
                  className={`qm-summary-word-tag${result.wasFuzzy ? ' qm-summary-word-fuzzy' : ''}`}
                >
                  {word.word}
                </span>
              ) : null
            })}
          </div>
        </div>
      )}

      <div className="qm-summary-actions">
        <button className="qm-btn-restart" onClick={onRestart}>再来一轮</button>
        {reviewHasMore && onContinueReview ? (
          <button className="qm-btn-next-chapter" onClick={onContinueReview}>
            下一组复习
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        ) : nextChapter && bookId ? (
          <button
            className="qm-btn-next-chapter"
            onClick={() => onNavigate(
              buildChapterPath?.(nextChapter.id) ?? `/practice?book=${bookId}&chapter=${nextChapter.id}&mode=quickmemory`,
            )}
          >
            {reviewMode ? '下一章节复习' : '下一章节'}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        ) : (
          <button className="qm-btn-mode" onClick={() => onModeChange('smart')}>换个模式</button>
        )}
      </div>
    </div>
  )
}
