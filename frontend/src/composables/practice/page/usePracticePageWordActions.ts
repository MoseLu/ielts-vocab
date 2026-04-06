import { useCallback, useMemo } from 'react'
import type { PracticeMode, Word, WordListActionControls } from '../../../components/practice/types'
import { useFavoriteWords, useFamiliarWords } from '../../../features/vocabulary/hooks'

type ToastType = 'success' | 'error' | 'info'

interface UsePracticePageWordActionsParams {
  userId: string | number | null
  mode?: PracticeMode
  vocabulary: Word[]
  queue: number[]
  queueIndex: number
  favoriteQueueIndex: number
  currentWord: Word | undefined
  practiceBookId: string | null
  practiceChapterId: string | null
  currentChapterTitle: string
  showToast?: (message: string, type?: ToastType) => void
}

export function usePracticePageWordActions({
  userId,
  mode,
  vocabulary,
  queue,
  queueIndex,
  favoriteQueueIndex,
  currentWord,
  practiceBookId,
  practiceChapterId,
  currentChapterTitle,
  showToast,
}: UsePracticePageWordActionsParams) {
  const activeQueueIndex = mode === 'quickmemory' || mode === 'radio' ? favoriteQueueIndex : queueIndex
  const actionWord = vocabulary[queue[activeQueueIndex]] ?? currentWord
  const favoriteState = useFavoriteWords({ userId, vocabulary, showToast })
  const familiarState = useFamiliarWords({ userId, vocabulary, showToast })

  const buildWordContext = useCallback((word: Word) => ({
    bookId: word.book_id != null ? String(word.book_id) : practiceBookId,
    chapterId: word.chapter_id != null ? String(word.chapter_id) : practiceChapterId,
    chapterTitle: word.chapter_title ?? currentChapterTitle ?? null,
  }), [currentChapterTitle, practiceBookId, practiceChapterId])

  const handleFavoriteWordToggle = useCallback((word: Word) => {
    void favoriteState.toggleFavorite(word, buildWordContext(word))
  }, [buildWordContext, favoriteState])

  const handleFamiliarWordToggle = useCallback((word: Word) => {
    void familiarState.toggleFamiliar(word, buildWordContext(word))
  }, [buildWordContext, familiarState])

  const handleFavoriteToggle = useCallback(() => {
    if (!actionWord) return
    handleFavoriteWordToggle(actionWord)
  }, [actionWord, handleFavoriteWordToggle])

  const wordListActionControls = useMemo<WordListActionControls>(() => ({
    isFavorite: favoriteState.isFavorite,
    isFavoritePending: favoriteState.isPending,
    onFavoriteToggle: handleFavoriteWordToggle,
    isFamiliar: familiarState.isFamiliar,
    isFamiliarPending: familiarState.isPending,
    onFamiliarToggle: handleFamiliarWordToggle,
  }), [favoriteState, familiarState, handleFavoriteWordToggle, handleFamiliarWordToggle])

  return {
    favoriteActive: favoriteState.isFavorite(actionWord?.word),
    favoriteBusy: favoriteState.isPending(actionWord?.word),
    handleFavoriteToggle,
    wordListActionControls,
  }
}
