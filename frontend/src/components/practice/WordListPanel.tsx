// ── Word List Panel Component ───────────────────────────────────────────────────

import { useCallback, useRef, useEffect, useLayoutEffect, useMemo, useState } from 'react'
import { DEFAULT_SETTINGS } from '../../constants'
import { readAppSettingsFromStorage } from '../../lib/appSettings'
import WordMeaningGroups from '../ui/WordMeaningGroups'
import WordListActionButton from './WordListActionButton'
import type { Word, WordListPanelProps } from './types'
import WordListDetailPanel from './WordListDetailPanel'
import { playWordAudio } from './utils.audio'

function normalizeWordKey(word: string | null | undefined): string {
  return (word ?? '').trim().toLowerCase()
}

function isEditableShortcutTarget(target: EventTarget | null): boolean {
  const element = target instanceof HTMLElement ? target : null
  const tagName = element?.tagName
  return tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT' || element?.isContentEditable === true
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
  const selectedDetailItemRef = useRef<HTMLDivElement>(null)
  const wasOpenRef = useRef(false)
  const focusPlaybackSuppressionRef = useRef<string | null>(null)
  const [selectedDetailState, setSelectedDetailState] = useState<{ word: Word; version: number } | null>(null)
  const wordAudioSettings = useMemo(() => {
    const settings = typeof window === 'undefined' ? DEFAULT_SETTINGS : readAppSettingsFromStorage()
    return {
      playbackSpeed: String(settings.playbackSpeed ?? DEFAULT_SETTINGS.playbackSpeed),
      volume: String(settings.volume ?? DEFAULT_SETTINGS.volume),
    }
  }, [])

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

  const openWordDetails = useCallback((word: Word) => {
    setSelectedDetailState(previous => {
      if (previous && normalizeWordKey(previous.word.word) === normalizeWordKey(word.word)) {
        return { word, version: previous.version + 1 }
      }
      return { word, version: 0 }
    })
  }, [])

  const selectedDetailIndex = useMemo(() => {
    if (!selectedDetailState) return -1
    const selectedKey = normalizeWordKey(selectedDetailState.word.word)
    return visibleWords.findIndex(word => normalizeWordKey(word.word) === selectedKey)
  }, [selectedDetailState, visibleWords])

  const moveSelectedWord = useCallback((direction: -1 | 1) => {
    if (!visibleWords.length) return

    const fallbackIndex = Math.min(Math.max(queueIndex, 0), visibleWords.length - 1)
    const baseIndex = selectedDetailIndex >= 0 ? selectedDetailIndex : fallbackIndex
    const nextIndex = Math.min(Math.max(baseIndex + direction, 0), visibleWords.length - 1)
    const nextWord = visibleWords[nextIndex]
    if (nextWord) openWordDetails(nextWord)
  }, [openWordDetails, queueIndex, selectedDetailIndex, visibleWords])

  const closeWordDetails = () => {
    setSelectedDetailState(null)
  }

  // Position the list before paint on first open so the panel does not visibly jump.
  useLayoutEffect(() => {
    if (!show) {
      wasOpenRef.current = false
      return
    }

    const currentItem = currentWordListItemRef.current
    if (currentItem && typeof currentItem.scrollIntoView === 'function') {
      currentItem.scrollIntoView({
        block: 'nearest',
        behavior: wasOpenRef.current ? 'smooth' : 'auto',
      })
    }

    wasOpenRef.current = true
  }, [queueIndex, show])

  useEffect(() => {
    if (!show) {
      setSelectedDetailState(null)
    }
  }, [show])

  useLayoutEffect(() => {
    if (!show || !selectedDetailState) return
    const selectedItem = selectedDetailItemRef.current
    if (selectedItem && typeof selectedItem.scrollIntoView === 'function') {
      selectedItem.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      })
    }
  }, [selectedDetailState, show])

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

  const playListWord = (word: string) => {
    if (!word.trim()) return
    void playWordAudio(word, wordAudioSettings)
  }

  useEffect(() => {
    if (!show) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return
      if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return
      if (isEditableShortcutTarget(event.target)) return

      event.preventDefault()
      event.stopImmediatePropagation()
      moveSelectedWord(event.key === 'ArrowDown' ? 1 : -1)
    }

    window.addEventListener('keydown', handleKeyDown, true)
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [moveSelectedWord, show])

  return (
    <>
      {show && (
        <div className="wordlist-backdrop" onClick={handleClose} />
      )}
      <div className={`wordlist-panel ${show ? 'open' : ''}`} ref={wordListRef}>
        <div className="wordlist-header">
          <div className="wordlist-header-main">
            <span className="wordlist-title">单词列表</span>
            <span className="wordlist-total">{vocabulary.length}词</span>
          </div>
          <div className="wordlist-header-actions">
            <span className="wordlist-shortcut-hint" aria-label="上下方向键切换选中单词">
              <kbd>↑</kbd>
              <kbd>↓</kbd>
              <span className="wordlist-shortcut-label">切换选中</span>
            </span>
            <button type="button" className="wordlist-close" aria-label="关闭单词列表" onClick={handleClose}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>
        <div className="wordlist-body">
          {queue.map((vocabIdx, qi) => {
            const w = vocabulary[vocabIdx]
            if (!w) return null
            const isCurrent = qi === queueIndex
            const isDetailSelected =
              normalizeWordKey(selectedDetailState?.word.word) === normalizeWordKey(w.word)
            const explicitStatus = wordStatuses[vocabIdx]
            const status = explicitStatus ?? (qi < queueIndex ? 'correct' : undefined)
            const favoriteActive = wordActionControls?.isFavorite(w.word) ?? false
            const favoritePending = wordActionControls?.isFavoritePending(w.word) ?? false
            const familiarActive = wordActionControls?.isFamiliar(w.word) ?? false
            const familiarPending = wordActionControls?.isFamiliarPending(w.word) ?? false
            return (
              <div
                key={qi}
                ref={isDetailSelected ? selectedDetailItemRef : isCurrent ? currentWordListItemRef : null}
                className={`wordlist-item ${isCurrent ? 'current' : ''} ${isDetailSelected ? 'is-detail-selected' : ''} ${status || ''}`}
              >
                <button
                  type="button"
                  className="wordlist-item-main"
                  aria-label={`查看 ${w.word} 详情`}
                  aria-controls="practice-wordlist-detail-panel"
                  aria-pressed={isDetailSelected}
                  onPointerDown={() => {
                    focusPlaybackSuppressionRef.current = normalizeWordKey(w.word)
                  }}
                  onFocus={() => {
                    const normalizedWord = normalizeWordKey(w.word)
                    if (focusPlaybackSuppressionRef.current === normalizedWord) {
                      focusPlaybackSuppressionRef.current = null
                      return
                    }
                    playListWord(w.word)
                  }}
                  onClick={() => {
                    focusPlaybackSuppressionRef.current = null
                    playListWord(w.word)
                    openWordDetails(w)
                  }}
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
                    <WordMeaningGroups
                      className="wordlist-def"
                      definition={w.definition}
                      pos={w.pos}
                    />
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
