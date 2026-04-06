// ── Word List Panel Component ───────────────────────────────────────────────────

import { useRef, useEffect, useMemo, useState } from 'react'
import WordListActionButton from './WordListActionButton'
import type { Word, WordListPanelProps } from './types'
import WordListDetailPanel from './WordListDetailPanel'

function normalizeWordKey(word: string | null | undefined): string {
  return (word ?? '').trim().toLowerCase()
}

export default function WordListPanel({
  show,
  vocabulary,
  queue,
  queueIndex,
  wordStatuses,
  wordActionControls,
  onClose,
}: WordListPanelProps) {
  const wordListRef = useRef<HTMLDivElement>(null)
  const currentWordListItemRef = useRef<HTMLDivElement>(null)
  const [selectedDetailState, setSelectedDetailState] = useState<{ word: Word; version: number } | null>(null)

  const visibleWords = useMemo(
    () => queue
      .map(vocabIdx => vocabulary[vocabIdx])
      .filter((word): word is Word => Boolean(word)),
    [queue, vocabulary],
  )
  const visibleWordMap = useMemo(() => {
    const entries = new Map<string, Word>()
    visibleWords.forEach(word => {
      const key = normalizeWordKey(word.word)
      if (key && !entries.has(key)) {
        entries.set(key, word)
      }
    })
    return entries
  }, [visibleWords])

  const openWordDetails = (word: Word) => {
    setSelectedDetailState(previous => {
      if (previous && normalizeWordKey(previous.word.word) === normalizeWordKey(word.word)) {
        return { word, version: previous.version + 1 }
      }
      return { word, version: 0 }
    })
  }

  const closeWordDetails = () => {
    setSelectedDetailState(null)
  }

  // Scroll current word into view
  useEffect(() => {
    if (show && currentWordListItemRef.current && typeof currentWordListItemRef.current.scrollIntoView === 'function') {
      currentWordListItemRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [queueIndex, show])

  useEffect(() => {
    if (!show) {
      setSelectedDetailState(null)
    }
  }, [show])

  useEffect(() => {
    if (!selectedDetailState) return
    const normalizedWord = normalizeWordKey(selectedDetailState.word.word)
    if (!visibleWordMap.has(normalizedWord)) {
      setSelectedDetailState(null)
    }
  }, [selectedDetailState, visibleWordMap])

  const handleClose = () => {
    closeWordDetails()
    onClose()
  }

  const handlePickLocalWord = (word: string) => {
    const localWord = visibleWordMap.get(normalizeWordKey(word))
    if (localWord) {
      openWordDetails(localWord)
    }
  }

  return (
    <>
      {show && (
        <div className="wordlist-backdrop" onClick={handleClose} />
      )}
      <div className={`wordlist-panel ${show ? 'open' : ''}`} ref={wordListRef}>
        <div className="wordlist-header">
          <span className="wordlist-title">单词列表</span>
          <span className="wordlist-total">{vocabulary.length}词</span>
          <button className="wordlist-close" onClick={handleClose}>
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
            const isDetailSelected =
              normalizeWordKey(selectedDetailState?.word.word) === normalizeWordKey(w.word)
            const status = wordStatuses[vocabIdx]
            const favoriteActive = wordActionControls?.isFavorite(w.word) ?? false
            const favoritePending = wordActionControls?.isFavoritePending(w.word) ?? false
            const familiarActive = wordActionControls?.isFamiliar(w.word) ?? false
            const familiarPending = wordActionControls?.isFamiliarPending(w.word) ?? false
            return (
              <div
                key={qi}
                ref={isCurrent ? currentWordListItemRef : null}
                className={`wordlist-item ${isCurrent ? 'current' : ''} ${isDetailSelected ? 'is-detail-selected' : ''} ${status || ''}`}
              >
                <button
                  type="button"
                  className="wordlist-item-main"
                  aria-label={`查看 ${w.word} 详情`}
                  aria-controls="practice-wordlist-detail-panel"
                  aria-pressed={isDetailSelected}
                  onClick={() => openWordDetails(w)}
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
                </button>
                {wordActionControls && (
                  <div className="wordlist-item-actions">
                    <WordListActionButton
                      kind="familiar"
                      active={familiarActive}
                      pending={familiarPending}
                      onClick={() => wordActionControls.onFamiliarToggle(w)}
                    />
                    <WordListActionButton
                      kind="favorite"
                      active={favoriteActive}
                      pending={favoritePending}
                      onClick={() => wordActionControls.onFavoriteToggle(w)}
                    />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
      <WordListDetailPanel
        open={show && Boolean(selectedDetailState)}
        selectedWord={selectedDetailState?.word ?? null}
        selectionVersion={selectedDetailState?.version ?? 0}
        visibleWords={visibleWords}
        onClose={closeWordDetails}
        onPickLocalWord={handlePickLocalWord}
      />
    </>
  )
}
