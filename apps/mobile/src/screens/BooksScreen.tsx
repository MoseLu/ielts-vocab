import React, { useEffect, useMemo, useState } from 'react'
import { ChevronRight } from 'lucide-react-native'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import type { MobileBook, MobileChapter } from '@ielts-vocab/app-core'
import {
  addMyBook,
  loadBookProgressMap,
  loadBooks,
  loadChapterProgressMap,
  loadChapters,
  loadMyBookIds,
  type ProgressSnapshot,
} from '../api/learnerApi'
import { Card, Heading, Meta, Pill, PrimaryButton, Row, ScreenScroll, StatusText } from '../components/primitives'
import { DecoratedEmptyState } from '../components/stickers'
import type { Navigate } from '../navigation/types'
import { theme } from '../theme'

type ProgressMap = Record<string, ProgressSnapshot>

function toNumber(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim()) return Number(value) || 0
  return 0
}

function shortText(value: string, limit = 72): string {
  return value.length > limit ? `${value.slice(0, limit)}...` : value
}

function pct(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)))
}

function bookTotal(book: MobileBook, progress?: ProgressSnapshot): number {
  return toNumber(progress?.total_words) || book.total_words || book.word_count || 0
}

function bookPercent(book: MobileBook, progress?: ProgressSnapshot): number {
  const total = bookTotal(book, progress)
  const explicit = toNumber(progress?.progress_percent)
  if (explicit) return pct(explicit)
  return total ? pct((toNumber(progress?.current_index) / total) * 100) : 0
}

function chapterTotal(chapter: MobileChapter): number {
  return chapter.word_count || chapter.group_count || 0
}

function chapterPercent(chapter: MobileChapter, progress?: ProgressSnapshot): number {
  const total = chapterTotal(chapter)
  const explicit = toNumber(progress?.progress_percent)
  if (explicit) return pct(explicit)
  return total ? pct((toNumber(progress?.words_learned ?? progress?.current_index) / total) * 100) : 0
}

function ProgressBar({ value }: { value: number }) {
  return (
    <View style={styles.progressTrack}>
      <View style={[styles.progressFill, { width: `${pct(value)}%` }]} />
    </View>
  )
}

export function BooksScreen({
  navigate,
  options,
}: {
  navigate: Navigate
  options?: { bookId?: string; chapterId?: string | number | null }
}) {
  const [books, setBooks] = useState<MobileBook[]>([])
  const [myBooks, setMyBooks] = useState<string[]>([])
  const [bookProgress, setBookProgress] = useState<ProgressMap>({})
  const [chapterProgress, setChapterProgress] = useState<ProgressMap>({})
  const [chapters, setChapters] = useState<MobileChapter[]>([])
  const [selectedBook, setSelectedBook] = useState<MobileBook | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const selectedBookProgress = selectedBook ? bookProgress[String(selectedBook.id)] : undefined
  const totalWords = useMemo(() => books.reduce((sum, book) => sum + bookTotal(book, bookProgress[String(book.id)]), 0), [bookProgress, books])

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all([loadBooks(), loadMyBookIds(), loadBookProgressMap()])
      .then(async ([nextBooks, ids, nextProgress]) => {
        if (!active) return
        setBooks(nextBooks)
        setMyBooks(ids)
        setBookProgress(nextProgress)
        const initial = options?.bookId ? nextBooks.find(book => String(book.id) === options.bookId) : null
        if (initial) await openBook(initial, active)
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : '词书加载失败')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options?.bookId])

  async function openBook(book: MobileBook, active = true) {
    setSelectedBook(book)
    setChapters([])
    setChapterProgress({})
    setError('')
    try {
      const [nextChapters, nextProgress] = await Promise.all([
        loadChapters(String(book.id)),
        loadChapterProgressMap(String(book.id)),
      ])
      if (!active) return
      setChapters(nextChapters)
      setChapterProgress(nextProgress)
    } catch (err) {
      if (active) setError(err instanceof Error ? err.message : '章节加载失败')
    }
  }

  async function addBook(book: MobileBook) {
    try {
      await addMyBook(String(book.id))
      setMyBooks(await loadMyBookIds())
    } catch (err) {
      setError(err instanceof Error ? err.message : '加入词书失败')
    }
  }

  function startChapter(chapter?: MobileChapter) {
    if (!selectedBook) return
    navigate('practice', {
      bookId: String(selectedBook.id),
      chapterId: chapter?.id ?? options?.chapterId ?? chapters[0]?.id,
      mode: 'quickmemory',
    })
  }

  return (
    <ScreenScroll hideHeader title="词书">
      <StatusText error={error} loading={loading} />
      {!selectedBook ? (
        <>
          <View style={styles.listHead}>
            <Heading>全部词书</Heading>
            <Meta>{books.length} 本 · {totalWords} 词</Meta>
          </View>
          {books.map(book => {
            const progress = bookProgress[String(book.id)]
            const percent = bookPercent(book, progress)
            const learned = toNumber(progress?.current_index)
            const total = bookTotal(book, progress)
            const owned = myBooks.includes(String(book.id))
            return (
              <Pressable key={String(book.id)} accessibilityRole="button" onPress={() => void openBook(book)} style={styles.bookCard}>
                <View style={styles.bookMain}>
                  <View style={styles.titleRow}>
                    <Text numberOfLines={1} style={styles.bookTitle}>{book.title}</Text>
                    {owned ? <Pill label="已加入" /> : null}
                  </View>
                  <Text numberOfLines={2} style={styles.bookDesc}>
                    {book.description ? shortText(book.description) : `${book.level || book.category || 'IELTS'} 词书`}
                  </Text>
                  <ProgressBar value={percent} />
                  <View style={styles.progressRow}>
                    <Text style={styles.progressText}>{learned}/{total} 词</Text>
                    <Text style={styles.progressText}>{percent}%</Text>
                  </View>
                </View>
                <ChevronRight color={theme.colors.textTertiary} size={20} />
              </Pressable>
            )
          })}
        </>
      ) : (
        <>
          <Card style={styles.selectedCard}>
            <View style={styles.selectedHead}>
              <View style={styles.bookMain}>
                <Meta>当前词书</Meta>
                <Heading>{selectedBook.title}</Heading>
                <ProgressBar value={bookPercent(selectedBook, selectedBookProgress)} />
                <View style={styles.progressRow}>
                  <Text style={styles.progressText}>
                    {toNumber(selectedBookProgress?.current_index)}/{bookTotal(selectedBook, selectedBookProgress)} 词
                  </Text>
                  <Text style={styles.progressText}>
                    {toNumber(selectedBookProgress?.completed_chapters)}/{toNumber(selectedBookProgress?.total_chapters) || chapters.length} 章
                  </Text>
                </View>
              </View>
              <Pressable accessibilityRole="button" onPress={() => setSelectedBook(null)}>
                <Text style={styles.linkText}>词书列表</Text>
              </Pressable>
            </View>
            <Row>
              <PrimaryButton label={myBooks.includes(String(selectedBook.id)) ? '已加入我的词书' : '加入我的词书'} onPress={() => void addBook(selectedBook)} />
              <PrimaryButton label="继续学习" tone="accent" onPress={() => startChapter()} />
            </Row>
          </Card>
          <View style={styles.listHead}>
            <Heading>章节进度</Heading>
            <Meta>{chapters.length} 章</Meta>
          </View>
          {chapters.map((chapter, index) => {
            const progress = chapterProgress[String(chapter.id)]
            const percent = chapterPercent(chapter, progress)
            const learned = toNumber(progress?.words_learned ?? progress?.current_index)
            const total = chapterTotal(chapter)
            return (
              <Pressable key={String(chapter.id)} accessibilityRole="button" onPress={() => startChapter(chapter)} style={styles.chapterRow}>
                <View style={styles.chapterIndex}>
                  <Text style={styles.chapterIndexText}>{String(index + 1).padStart(2, '0')}</Text>
                </View>
                <View style={styles.bookMain}>
                  <Text numberOfLines={1} style={styles.chapterTitle}>{chapter.title}</Text>
                  <ProgressBar value={percent} />
                  <View style={styles.progressRow}>
                    <Text style={styles.progressText}>{learned}/{total} 项 · {percent}%</Text>
                    <Text style={styles.progressText}>正确 {toNumber(progress?.correct_count)} · 错误 {toNumber(progress?.wrong_count)}</Text>
                  </View>
                </View>
                <ChevronRight color={theme.colors.textTertiary} size={20} />
              </Pressable>
            )
          })}
          {!chapters.length && !loading ? (
            <DecoratedEmptyState
              description="稍后重新同步词书，章节准备好后就能继续学习。"
              sticker="vocabCardStack"
              title="暂无章节"
            />
          ) : null}
        </>
      )}
    </ScreenScroll>
  )
}

const styles = StyleSheet.create({
  bookCard: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    flexDirection: 'row',
    gap: theme.spacing.md,
    marginBottom: theme.spacing.sm,
    padding: theme.spacing.md,
  },
  bookDesc: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    lineHeight: 19,
    marginTop: theme.spacing.xs,
  },
  bookMain: {
    flex: 1,
  },
  bookTitle: {
    color: theme.colors.text,
    flex: 1,
    fontSize: theme.typography.body,
    fontWeight: '900',
  },
  chapterIndex: {
    alignItems: 'center',
    backgroundColor: theme.colors.primarySoft,
    borderRadius: theme.radius.card,
    height: 42,
    justifyContent: 'center',
    width: 42,
  },
  chapterIndexText: {
    color: theme.colors.primaryDark,
    fontSize: theme.typography.caption,
    fontWeight: '900',
  },
  chapterRow: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    flexDirection: 'row',
    gap: theme.spacing.md,
    marginBottom: theme.spacing.sm,
    padding: theme.spacing.md,
  },
  chapterTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    fontWeight: '900',
  },
  linkText: {
    color: theme.colors.primaryDark,
    fontSize: theme.typography.caption,
    fontWeight: '900',
  },
  listHead: {
    marginBottom: theme.spacing.sm,
  },
  progressFill: {
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.pill,
    height: '100%',
  },
  progressRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: theme.spacing.xs,
  },
  progressText: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '800',
  },
  progressTrack: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.pill,
    height: 7,
    marginTop: theme.spacing.sm,
    overflow: 'hidden',
  },
  selectedCard: {
    backgroundColor: theme.colors.surfaceElevated,
  },
  selectedHead: {
    flexDirection: 'row',
    gap: theme.spacing.md,
    justifyContent: 'space-between',
    marginBottom: theme.spacing.md,
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.xs,
  },
})
