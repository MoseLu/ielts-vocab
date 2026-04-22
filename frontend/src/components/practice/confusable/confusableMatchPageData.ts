import { apiFetch, buildApiUrl, buildBookPracticePath } from '../../../lib'
import {
  buildMatchGroups,
  buildRoundCards,
  buildWordKeySet,
  getRoundGroups,
  resolveRoundGroupKeys,
  type MatchCard,
  type MatchProgressSnapshot,
} from '../confusableMatch'
import { persistChapterSnapshot, readStoredChapterSnapshot } from './confusableMatchPageHelpers'
import type { Chapter, ProgressData, Word } from '../types'

type NavigateFn = (path: string, options?: { replace?: boolean }) => void

export type ChapterProgressResponse = { chapter_progress?: Record<string, ProgressData | MatchProgressSnapshot> }
type ChapterWordsResponse = { chapter?: Chapter; words?: Word[] }
type ChaptersResponse = { chapters?: Chapter[] }

export type LoadedConfusableMatchData = {
  chapters: Chapter[]
  redirectPath?: string
  title: string
  words: Word[]
  answeredWordKeys: Set<string>
  correctCount: number
  wrongCount: number
  roundGroupKeys: string[]
  cards: MatchCard[]
}

export async function loadConfusableMatchPageData({
  bookId,
  chapterId,
  groupsPerRound,
  navigate,
}: {
  bookId: string
  chapterId: string | null
  groupsPerRound: number
  navigate: NavigateFn
}): Promise<LoadedConfusableMatchData> {
  const chaptersResponse = await fetch(buildApiUrl(`/api/books/${bookId}/chapters`))
  if (!chaptersResponse.ok) {
    throw new Error('加载章节失败')
  }

  const chaptersData = await chaptersResponse.json() as ChaptersResponse
  const chapters = chaptersData.chapters ?? []

  if (!chapterId) {
    const firstChapter = chapters[0]
    if (!firstChapter) {
      throw new Error('未找到可练习章节')
    }
    const redirectPath = buildBookPracticePath({ id: bookId, practice_mode: 'match' }, firstChapter.id)
    navigate(redirectPath, { replace: true })
    return {
      chapters,
      redirectPath,
      title: '',
      words: [],
      answeredWordKeys: new Set<string>(),
      correctCount: 0,
      wrongCount: 0,
      roundGroupKeys: [],
      cards: [],
    }
  }

  const [chapterWordsData, progressData] = await Promise.all([
    fetch(buildApiUrl(`/api/books/${bookId}/chapters/${chapterId}`)).then(async response => {
      if (!response.ok) throw new Error('加载辨析词汇失败')
      return response.json() as Promise<ChapterWordsResponse>
    }),
    apiFetch<ChapterProgressResponse>(`/api/books/${bookId}/chapters/progress`).catch((): ChapterProgressResponse => ({})),
  ])

  const words = chapterWordsData.words ?? []
  if (words.length < 2) {
    throw new Error('当前章节词量不足，无法生成配对')
  }

  const storedSnapshot = readStoredChapterSnapshot(bookId, chapterId)
  const serverSnapshot = progressData.chapter_progress?.[String(chapterId)] as MatchProgressSnapshot | undefined
  const rawSnapshot = storedSnapshot ?? (
    Array.isArray(serverSnapshot?.answered_words) && serverSnapshot.answered_words.length > 0
      ? serverSnapshot
      : null
  )
  const baseSnapshot = rawSnapshot && rawSnapshot.is_completed ? null : rawSnapshot
  const groups = buildMatchGroups(words)
  const answeredWordKeys = buildWordKeySet(baseSnapshot?.answered_words)
  const roundGroupKeys = resolveRoundGroupKeys(
    groups,
    answeredWordKeys,
    groupsPerRound,
    baseSnapshot?.round_group_keys,
  )

  return {
    chapters,
    title: chapterWordsData.chapter?.title ?? '',
    words,
    answeredWordKeys,
    correctCount: baseSnapshot?.correct_count ?? answeredWordKeys.size,
    wrongCount: baseSnapshot?.wrong_count ?? 0,
    roundGroupKeys,
    cards: buildRoundCards(getRoundGroups(groups, roundGroupKeys), answeredWordKeys),
  }
}

export function buildConfusableMatchSnapshot({
  answeredCount,
  correctCount,
  wrongCount,
  isCompleted,
  answeredWordKeys,
  roundGroupKeys,
}: {
  answeredCount: number
  correctCount: number
  wrongCount: number
  isCompleted: boolean
  answeredWordKeys: Set<string>
  roundGroupKeys: string[]
}) {
  return {
    current_index: answeredCount,
    correct_count: correctCount,
    wrong_count: wrongCount,
    is_completed: isCompleted,
    words_learned: answeredCount,
    answered_words: Array.from(answeredWordKeys).sort(),
    round_group_keys: roundGroupKeys,
    updatedAt: new Date().toISOString(),
  }
}

export function persistConfusableMatchProgress({
  bookId,
  chapterId,
  snapshot,
}: {
  bookId: string
  chapterId: string
  snapshot: MatchProgressSnapshot
}) {
  persistChapterSnapshot(bookId, chapterId, snapshot)
  void apiFetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
    method: 'POST',
    body: JSON.stringify({
      mode: 'match',
      current_index: snapshot.current_index,
      correct_count: snapshot.correct_count,
      wrong_count: snapshot.wrong_count,
      is_completed: snapshot.is_completed,
      words_learned: snapshot.words_learned,
    }),
  }).catch(() => {})
  void apiFetch(`/api/books/${bookId}/chapters/${chapterId}/mode-progress`, {
    method: 'POST',
    body: JSON.stringify({
      mode: 'match',
      correct_count: snapshot.correct_count,
      wrong_count: snapshot.wrong_count,
      is_completed: snapshot.is_completed,
    }),
  }).catch(() => {})

  return snapshot
}
