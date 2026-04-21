import { createPortal } from 'react-dom'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { DEFAULT_SETTINGS } from '../../../constants'
import { useAuth, useToast } from '../../../contexts'
import type { WordDetailResponse, WordSearchResult } from '../../../lib'
import { readAppSettingsFromStorage } from '../../../lib/appSettings'
import type { Word } from '../../practice/types'
import FavoriteToggleButton from '../../practice/FavoriteToggleButton'
import { playWordAudio, stopAudio } from '../../practice/utils.audio'
import WordMeaningGroups from '../../ui/WordMeaningGroups'
import { useFavoriteWords } from '../../../features/vocabulary/hooks'
import { openGlobalWordSearch } from './globalWordSearchEvents'
import {
  buildSelectionLookupMeta,
  resolveSelectionLookupExample,
  resolveSelectionLookupPosition,
  type SelectionLookupAnchorRect,
  SELECTION_LOOKUP_FALLBACK_HEIGHT,
  SELECTION_LOOKUP_FALLBACK_WIDTH,
  SELECTION_LOOKUP_PANEL_CLASS,
} from './selectionWordLookup.shared'

type SelectionWordLookupCardProps = {
  anchorRect: SelectionLookupAnchorRect
  detailData: WordDetailResponse | null
  error: string | null
  isGlobalSearchContext: boolean
  isLoadingDetails: boolean
  onDismiss: () => void
  result: WordSearchResult
}

export default function SelectionWordLookupCard({
  anchorRect,
  detailData,
  error,
  isGlobalSearchContext,
  isLoadingDetails,
  onDismiss,
  result,
}: SelectionWordLookupCardProps) {
  const panelRef = useRef<HTMLDivElement | null>(null)
  const { user } = useAuth()
  const { showToast } = useToast()
  const [panelPosition, setPanelPosition] = useState(() => {
    if (typeof window === 'undefined') {
      return { left: anchorRect.right, top: anchorRect.bottom }
    }
    return resolveSelectionLookupPosition(anchorRect, {
      width: SELECTION_LOOKUP_FALLBACK_WIDTH,
      height: SELECTION_LOOKUP_FALLBACK_HEIGHT,
    }, {
      width: window.innerWidth,
      height: window.innerHeight,
    })
  })

  const resolvedPhonetic = detailData?.phonetic || result.phonetic || '/暂无音标/'
  const resolvedPos = detailData?.pos || result.pos || '词性'
  const resolvedDefinition = detailData?.definition || result.definition || '暂无释义'
  const metaLine = buildSelectionLookupMeta(result)
  const example = resolveSelectionLookupExample(detailData, result)
  const vocabulary = useMemo<Word[]>(() => [{
    word: result.word,
    phonetic: resolvedPhonetic,
    pos: resolvedPos,
    definition: resolvedDefinition,
    book_id: result.book_id,
    book_title: result.book_title,
    chapter_id: result.chapter_id,
    chapter_title: result.chapter_title,
  }], [
    resolvedDefinition,
    resolvedPhonetic,
    resolvedPos,
    result.book_id,
    result.book_title,
    result.chapter_id,
    result.chapter_title,
    result.word,
  ])
  const audioSettings = useMemo(() => {
    if (typeof window === 'undefined') return DEFAULT_SETTINGS
    const settings = readAppSettingsFromStorage()
    return {
      playbackSpeed: String(settings.playbackSpeed ?? DEFAULT_SETTINGS.playbackSpeed),
      volume: String(settings.volume ?? DEFAULT_SETTINGS.volume),
    }
  }, [])
  const { isFavorite, isPending, toggleFavorite } = useFavoriteWords({
    userId: user?.id ?? null,
    vocabulary,
    showToast,
  })

  useLayoutEffect(() => {
    if (typeof window === 'undefined') return undefined
    const frameId = window.requestAnimationFrame(() => {
      const panelRect = panelRef.current?.getBoundingClientRect()
      setPanelPosition(resolveSelectionLookupPosition(anchorRect, {
        width: panelRect?.width || SELECTION_LOOKUP_FALLBACK_WIDTH,
        height: panelRect?.height || SELECTION_LOOKUP_FALLBACK_HEIGHT,
      }, {
        width: window.innerWidth,
        height: window.innerHeight,
      }))
    })
    return () => window.cancelAnimationFrame(frameId)
  }, [anchorRect, detailData, isLoadingDetails])

  useEffect(() => () => {
    stopAudio()
  }, [result.word])

  if (typeof document === 'undefined') return null

  const handleFavoriteToggle = () => {
    void toggleFavorite(vocabulary[0], {
      bookId: result.book_id,
      chapterId: result.chapter_id != null ? String(result.chapter_id) : null,
      chapterTitle: result.chapter_title ?? null,
    })
  }

  const handleOpenFullDetails = () => {
    openGlobalWordSearch({ query: result.word, autoSubmit: true })
    onDismiss()
  }

  return createPortal(
    <div
      ref={panelRef}
      className={`${SELECTION_LOOKUP_PANEL_CLASS}${isGlobalSearchContext ? ' selection-word-lookup--global-search' : ''}`}
      role="dialog"
      aria-label={`划词词典卡片：${result.word}`}
      aria-busy={isLoadingDetails}
      data-context={isGlobalSearchContext ? 'global-search' : 'page'}
      data-detail-status={error ? 'fallback' : isLoadingDetails ? 'loading' : 'ready'}
      style={{
        '--selection-lookup-left': `${panelPosition.left}px`,
        '--selection-lookup-top': `${panelPosition.top}px`,
      }}
    >
      <div className="selection-word-lookup-header">
        <div className="selection-word-lookup-heading">
          <button
            type="button"
            className="selection-word-lookup-word"
            aria-label={`朗读 ${result.word}`}
            onClick={() => { void playWordAudio(result.word, audioSettings) }}
          >
            {result.word}
          </button>
          <span className="selection-word-lookup-phonetic">{resolvedPhonetic}</span>
        </div>
        <button
          type="button"
          className="selection-word-lookup-close"
          aria-label="关闭划词词典卡片"
          onClick={onDismiss}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <WordMeaningGroups
        className="selection-word-lookup-summary"
        definition={resolvedDefinition}
        pos={resolvedPos}
        size="sm"
      />
      {metaLine ? <p className="selection-word-lookup-meta">{metaLine}</p> : null}

      {example?.en || example?.zh ? (
        <div className="selection-word-lookup-example">
          {example?.en ? <p className="selection-word-lookup-example-en">{example.en}</p> : null}
          {example?.zh ? <p className="selection-word-lookup-example-zh">{example.zh}</p> : null}
        </div>
      ) : null}

      <div className="selection-word-lookup-actions">
        <FavoriteToggleButton
          active={isFavorite(result.word)}
          pending={isPending(result.word)}
          onClick={handleFavoriteToggle}
        />
        <button
          type="button"
          className="selection-word-lookup-action-btn"
          aria-label={`朗读单词 ${result.word}`}
          onClick={() => { void playWordAudio(result.word, audioSettings) }}
        >
          朗读
        </button>
        <button
          type="button"
          className="selection-word-lookup-action-btn selection-word-lookup-action-btn--accent"
          aria-label={`打开 ${result.word} 的完整详情`}
          onClick={handleOpenFullDetails}
        >
          完整详情
        </button>
      </div>
    </div>,
    document.body,
  )
}
