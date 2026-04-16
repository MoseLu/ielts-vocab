import { startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import GlobalWordSearchDetailPanel from '../layout/navigation/GlobalWordSearchDetailPanel'
import {
  apiFetch,
  safeParse,
  WordSearchResponseSchema,
  type WordSearchResult,
} from '../../lib'
import type { Word } from './types'

interface WordListDetailPanelProps {
  open: boolean
  selectedWord: Word | null
  selectionVersion?: number
  visibleWords: Word[]
  onClose: () => void
  onPickLocalWord: (word: string) => void
}

const SEARCH_LIMIT = 1

function normalizeWordKey(word: string | null | undefined): string {
  return (word ?? '').trim().toLowerCase()
}

function buildWordSearchResult(word: Word): WordSearchResult {
  return {
    word: word.word,
    phonetic: word.phonetic || '',
    pos: word.pos || '',
    definition: word.definition || '',
    group_key: word.group_key,
    listening_confusables: word.listening_confusables,
    chapter_id: word.chapter_id,
    chapter_title: word.chapter_title,
    examples: word.examples,
    book_id: String(word.book_id ?? word.chapter_id ?? 'practice'),
    book_title: word.book_title ?? '',
    match_type: 'exact',
  }
}

function buildLooseWordResult(word: string): WordSearchResult {
  return {
    word,
    phonetic: '',
    pos: '',
    definition: '',
    book_id: 'practice',
    book_title: '',
    match_type: 'exact',
  }
}

function pickBestSearchResult(query: string, results: WordSearchResult[]): WordSearchResult | null {
  const normalizedQuery = normalizeWordKey(query)
  return results.find(result => normalizeWordKey(result.word) === normalizedQuery) ?? results[0] ?? null
}

export default function WordListDetailPanel({
  open,
  selectedWord,
  selectionVersion = 0,
  visibleWords,
  onClose,
  onPickLocalWord,
}: WordListDetailPanelProps) {
  const [activeResult, setActiveResult] = useState<WordSearchResult | null>(null)
  const [detailQuery, setDetailQuery] = useState('')
  const [isResolving, setIsResolving] = useState(false)
  const [resolutionError, setResolutionError] = useState<string | null>(null)
  const searchAbortRef = useRef<AbortController | null>(null)

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

  const resolveSearchResult = useCallback(async (word: string) => {
    const trimmedWord = word.trim()
    if (!trimmedWord) return

    searchAbortRef.current?.abort()
    const controller = new AbortController()
    searchAbortRef.current = controller
    setIsResolving(true)
    setResolutionError(null)

    try {
      const raw = await apiFetch<unknown>(
        `/api/books/search?q=${encodeURIComponent(trimmedWord)}&limit=${SEARCH_LIMIT}`,
        { signal: controller.signal },
      )
      const parsed = safeParse(WordSearchResponseSchema, raw)
      if (!parsed.success) {
        throw new Error('搜索结果格式错误')
      }

      const resolved = pickBestSearchResult(trimmedWord, parsed.data.results)
      if (resolved) {
        startTransition(() => {
          setActiveResult(resolved)
          setDetailQuery(trimmedWord)
        })
      }
    } catch (error) {
      if (controller.signal.aborted) return
      setResolutionError(error instanceof Error ? error.message : '全局词条同步失败')
    } finally {
      if (searchAbortRef.current === controller) {
        searchAbortRef.current = null
      }
      if (!controller.signal.aborted) {
        setIsResolving(false)
      }
    }
  }, [])

  useEffect(() => {
    if (!open || !selectedWord) {
      searchAbortRef.current?.abort()
      searchAbortRef.current = null
      setActiveResult(null)
      setDetailQuery('')
      setIsResolving(false)
      setResolutionError(null)
      return
    }

    startTransition(() => {
      setActiveResult(buildWordSearchResult(selectedWord))
      setDetailQuery(selectedWord.word)
      setResolutionError(null)
    })

    void resolveSearchResult(selectedWord.word)
  }, [open, resolveSearchResult, selectedWord, selectionVersion])

  useEffect(() => {
    if (!open) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopImmediatePropagation()
      onClose()
    }

    window.addEventListener('keydown', handleKeyDown, true)
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [onClose, open])

  const handlePickWord = useCallback((word: string) => {
    const localWord = visibleWordMap.get(normalizeWordKey(word))
    if (localWord) {
      onPickLocalWord(localWord.word)
      return
    }

    startTransition(() => {
      setActiveResult(buildLooseWordResult(word))
      setDetailQuery(word)
      setResolutionError(null)
    })
    void resolveSearchResult(word)
  }, [onPickLocalWord, resolveSearchResult, visibleWordMap])

  if (!open || !activeResult) return null

  return (
    <aside
      id="practice-wordlist-detail-panel"
      className="wordlist-detail-panel"
      role="dialog"
      aria-label="单词详情"
    >
      <div className="wordlist-detail-header">
        <div className="wordlist-detail-heading">
          <span className="wordlist-detail-eyebrow">已接入全局搜索能力</span>
        </div>
        <div className="wordlist-detail-actions">
          {isResolving ? (
            <span className="wordlist-detail-status">同步中</span>
          ) : resolutionError ? (
            <span className="wordlist-detail-status wordlist-detail-status--fallback">词表兜底</span>
          ) : null}
          <button
            type="button"
            className="wordlist-detail-close"
            aria-label="关闭单词详情"
            onClick={onClose}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>
      <div className="wordlist-detail-body">
        <GlobalWordSearchDetailPanel
          query={detailQuery}
          result={activeResult}
          onPickWord={handlePickWord}
        />
      </div>
    </aside>
  )
}
