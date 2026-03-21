// ── Word List Panel Component ───────────────────────────────────────────────────

import React, { useRef, useEffect } from 'react'
import type { WordListPanelProps } from './types'

export default function WordListPanel({
  show,
  vocabulary,
  queue,
  queueIndex,
  wordStatuses,
  onClose,
}: WordListPanelProps) {
  const wordListRef = useRef<HTMLDivElement>(null)
  const currentWordListItemRef = useRef<HTMLDivElement>(null)

  // Scroll current word into view
  useEffect(() => {
    if (show && currentWordListItemRef.current) {
      currentWordListItemRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [queueIndex, show])

  return (
    <>
      {show && (
        <div className="wordlist-backdrop" onClick={onClose} />
      )}
      <div className={`wordlist-panel ${show ? 'open' : ''}`} ref={wordListRef}>
        <div className="wordlist-header">
          <span className="wordlist-title">单词列表</span>
          <span className="wordlist-total">{vocabulary.length}词</span>
          <button className="wordlist-close" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="wordlist-body">
          {queue.map((vocabIdx, qi) => {
            const w = vocabulary[vocabIdx]
            if (!w) return null
            const isCurrent = qi === queueIndex
            const status = wordStatuses[vocabIdx]
            return (
              <div
                key={qi}
                ref={isCurrent ? currentWordListItemRef : null}
                className={`wordlist-item ${isCurrent ? 'current' : ''} ${status || ''}`}
              >
                <div className="wordlist-item-status">
                  {isCurrent ? (
                    <span className="wl-dot wl-dot-current" />
                  ) : status === 'correct' ? (
                    <svg className="wl-icon correct" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : status === 'wrong' ? (
                    <svg className="wl-icon wrong" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  ) : (
                    <span className="wl-dot wl-dot-pending" />
                  )}
                </div>
                <div className="wordlist-item-info">
                  <div className="wordlist-word">{w.word}</div>
                  <div className="wordlist-phonetic">{w.phonetic}</div>
                  <div className="wordlist-def">
                    <span className="word-pos-tag">{w.pos}</span>
                    {w.definition}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </>
  )
}
