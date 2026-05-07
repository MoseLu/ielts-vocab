import React, { useEffect, useMemo, useState } from 'react'
import { BookOpen, CheckCircle2, ChevronRight, Layers3, Library, Plus, Search, Star } from 'lucide-react-native'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import type { MobileBook, MobileChapter, MobileWord } from '@ielts-vocab/app-core'
import {
  addMyBook,
  createCustomBook,
  loadBooks,
  loadChapterWords,
  loadChapters,
  loadMyBookIds,
  saveWordNote,
  setFamiliar,
  setFavorite,
} from '../api/learnerApi'
import { Body, Card, Field, Heading, Meta, Pill, PrimaryButton, Row, ScreenScroll, StatusText } from '../components/primitives'
import type { Navigate } from '../navigation/types'
import { theme } from '../theme'

function wordCount(book: MobileBook): number {
  return book.total_words || book.word_count || 0
}

function shortText(value: string, limit = 72): string {
  return value.length > limit ? `${value.slice(0, limit)}...` : value
}

function makeCustomWord(line: string): MobileWord {
  const [word, definition = ''] = line.split(/[,，\t]/)
  return {
    word: word.trim(),
    definition: definition.trim(),
    phonetic: '',
    pos: '',
    group_key: '',
    book_id: '',
    book_title: '',
    chapter_id: '',
    chapter_title: '',
    examples: [],
    listening_confusables: [],
  }
}

export function BooksScreen({ navigate, options }: { navigate: Navigate; options?: { bookId?: string; chapterId?: string | number | null } }) {
  const [books, setBooks] = useState<MobileBook[]>([])
  const [myBooks, setMyBooks] = useState<string[]>([])
  const [chapters, setChapters] = useState<MobileChapter[]>([])
  const [words, setWords] = useState<MobileWord[]>([])
  const [selectedBook, setSelectedBook] = useState<MobileBook | null>(null)
  const [selectedChapter, setSelectedChapter] = useState<MobileChapter | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [customTitle, setCustomTitle] = useState('')
  const [customWords, setCustomWords] = useState('')
  const [note, setNote] = useState('')

  const totalWords = useMemo(() => books.reduce((sum, book) => sum + wordCount(book), 0), [books])

  function refreshBooks(term = search) {
    let active = true
    setLoading(true)
    Promise.all([loadBooks(term), loadMyBookIds()])
      .then(([nextBooks, ids]) => {
        if (!active) return
        setBooks(nextBooks)
        setMyBooks(ids)
        if (options?.bookId && !selectedBook) {
          const found = nextBooks.find(book => String(book.id) === options.bookId)
          if (found) void openBook(found)
        }
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
  }

  useEffect(() => {
    return refreshBooks('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function openBook(book: MobileBook) {
    setSelectedBook(book)
    setSelectedChapter(null)
    setWords([])
    setError('')
    try {
      setChapters(await loadChapters(String(book.id)))
    } catch (err) {
      setError(err instanceof Error ? err.message : '章节加载失败')
    }
  }

  async function openChapter(chapter: MobileChapter) {
    if (!selectedBook) return
    setSelectedChapter(chapter)
    setError('')
    try {
      setWords(await loadChapterWords(String(selectedBook.id), chapter.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : '词表加载失败')
    }
  }

  async function createBook() {
    const wordsToCreate = customWords.split(/\n+/).map(line => line.trim()).filter(Boolean).map(makeCustomWord)
    if (!customTitle || !wordsToCreate.length) {
      setError('请填写自定义词书标题和词表')
      return
    }
    await createCustomBook(customTitle, wordsToCreate)
    setCustomTitle('')
    setCustomWords('')
    refreshBooks()
  }

  return (
    <ScreenScroll hideHeader title="词书" subtitle="浏览词书、章节、词详情；收藏、熟词和自定义词书都在原生端完成。">
      <StatusText error={error} loading={loading} />
      <Card style={styles.hero}>
        <View style={styles.heroTop}>
          <View style={styles.heroIcon}>
            <Library color={theme.colors.primaryDark} size={26} strokeWidth={2.5} />
          </View>
          <View style={styles.heroCopy}>
            <Meta>词书中心</Meta>
            <Text style={styles.heroTitle}>{selectedBook ? selectedBook.title : `${books.length} 本词书`}</Text>
            <Text style={styles.heroSub}>{selectedBook ? `${chapters.length} 个章节 · ${wordCount(selectedBook)} 词` : `${totalWords} 个词条已接入原生学习流`}</Text>
          </View>
        </View>
        <View style={styles.searchShell}>
          <Search color={theme.colors.muted} size={19} />
          <Field value={search} onChangeText={setSearch} placeholder="搜索词书" />
          <Pressable accessibilityRole="button" style={styles.searchButton} onPress={() => refreshBooks(search)}>
            <Text style={styles.searchButtonText}>搜索</Text>
          </Pressable>
        </View>
      </Card>

      {selectedBook ? (
        <Card>
          <View style={styles.selectedHead}>
            <View>
              <Heading>{selectedBook.title}</Heading>
              <Meta>{selectedBook.level || selectedBook.category || 'IELTS'} · {wordCount(selectedBook)} 词</Meta>
            </View>
            <Pressable accessibilityRole="button" onPress={() => {
              setSelectedBook(null)
              setSelectedChapter(null)
              setWords([])
            }}>
              <Text style={styles.linkText}>列表</Text>
            </Pressable>
          </View>
          {selectedBook.description ? <Body>{shortText(selectedBook.description, 110)}</Body> : null}
          <Row>
            <PrimaryButton label="加入我的词书" onPress={() => void addMyBook(String(selectedBook.id)).then(() => refreshBooks())} />
            <PrimaryButton label="开始练习" tone="accent" onPress={() => navigate('practice', { bookId: String(selectedBook.id), chapterId: selectedChapter?.id })} />
          </Row>
        </Card>
      ) : null}

      {selectedBook && !selectedChapter ? (
        <Card>
          <View style={styles.sectionHead}>
            <Heading>章节</Heading>
            <Layers3 color={theme.colors.muted} size={20} />
          </View>
          <View style={styles.chapterGrid}>
            {chapters.map(chapter => (
              <Pressable key={String(chapter.id)} accessibilityRole="button" style={styles.chapterTile} onPress={() => void openChapter(chapter)}>
                <Text style={styles.chapterTitle}>{chapter.title}</Text>
                <Text style={styles.chapterMeta}>{chapter.word_count || chapter.group_count || 0} 项</Text>
              </Pressable>
            ))}
          </View>
        </Card>
      ) : null}

      {selectedChapter ? (
        <Card>
          <View style={styles.sectionHead}>
            <View>
              <Heading>{selectedChapter.title}</Heading>
              <Meta>{words.length} 个词条</Meta>
            </View>
            <Pressable accessibilityRole="button" onPress={() => {
              setSelectedChapter(null)
              setWords([])
            }}>
              <Text style={styles.linkText}>章节</Text>
            </Pressable>
          </View>
          {words.map(word => (
            <View key={word.word} style={styles.wordRow}>
              <View style={styles.wordBody}>
                <Text style={styles.word}>{word.word}</Text>
                <Text style={styles.wordMeta}>{[word.phonetic, word.pos].filter(Boolean).join(' ') || 'IELTS'}</Text>
                <Text style={styles.definition}>{word.definition}</Text>
              </View>
              <View style={styles.wordActions}>
                <Pressable accessibilityRole="button" style={styles.iconButton} onPress={() => void setFavorite(word.word, true)}>
                  <Star color={theme.colors.accent} size={18} />
                </Pressable>
                <Pressable accessibilityRole="button" style={styles.iconButton} onPress={() => void setFamiliar(word.word, true)}>
                  <CheckCircle2 color={theme.colors.emerald} size={18} />
                </Pressable>
              </View>
            </View>
          ))}
          <Field value={note} onChangeText={setNote} placeholder="给当前章节写复习笔记" multiline />
          <PrimaryButton label="保存笔记到最近查看词" tone="neutral" onPress={() => words[0] ? void saveWordNote(words[0].word, note) : undefined} />
        </Card>
      ) : null}

      {!selectedBook ? (
        <>
          <View style={styles.bookListHead}>
            <Heading>全部词书</Heading>
            <Meta>{myBooks.length} 本已加入</Meta>
          </View>
          {books.map(book => {
            const owned = myBooks.includes(String(book.id))
            return (
              <Pressable key={String(book.id)} accessibilityRole="button" style={styles.bookCard} onPress={() => void openBook(book)}>
                <View style={[styles.bookIcon, owned ? styles.ownedBookIcon : null]}>
                  <BookOpen color={owned ? theme.colors.primaryDark : theme.colors.text} size={22} strokeWidth={2.4} />
                </View>
                <View style={styles.bookInfo}>
                  <Text style={styles.bookTitle}>{book.title}</Text>
                  <Text style={styles.bookMeta}>{book.level || book.category || 'IELTS'} · {wordCount(book)} 词</Text>
                  {book.description ? <Text style={styles.bookDesc}>{shortText(book.description)}</Text> : null}
                  <View style={styles.tagRow}>
                    {owned ? <Pill label="我的词书" /> : null}
                    {book.practice_mode === 'match' ? <Pill label="易混词" /> : null}
                  </View>
                </View>
                <ChevronRight color={theme.colors.textTertiary} size={20} />
              </Pressable>
            )
          })}
        </>
      ) : null}

      {!selectedBook ? (
        <Card>
          <View style={styles.sectionHead}>
            <Heading>自定义词书</Heading>
            <Plus color={theme.colors.muted} size={20} />
          </View>
          <Field value={customTitle} onChangeText={setCustomTitle} placeholder="词书标题" />
          <Field value={customWords} onChangeText={setCustomWords} placeholder="每行：word,中文释义" multiline />
          <PrimaryButton label="创建自定义词书" onPress={() => void createBook().catch(err => setError(err.message))} />
        </Card>
      ) : null}
      {!loading && !books.length ? <Text style={styles.emptyText}>暂无词书。</Text> : null}
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
  bookIcon: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.card,
    height: 46,
    justifyContent: 'center',
    width: 46,
  },
  bookInfo: {
    flex: 1,
  },
  bookListHead: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  bookMeta: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '700',
    marginTop: 2,
  },
  bookTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    fontWeight: '900',
  },
  chapterGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
  },
  chapterMeta: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '700',
    marginTop: theme.spacing.xs,
  },
  chapterTile: {
    backgroundColor: theme.colors.surface,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    flexBasis: '48%',
    flexGrow: 1,
    minHeight: 92,
    padding: theme.spacing.md,
  },
  chapterTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    fontWeight: '900',
    lineHeight: 20,
  },
  definition: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    lineHeight: 21,
    marginTop: theme.spacing.xs,
  },
  emptyText: {
    color: theme.colors.muted,
    textAlign: 'center',
  },
  hero: {
    backgroundColor: theme.colors.surface,
  },
  heroCopy: {
    flex: 1,
  },
  heroIcon: {
    alignItems: 'center',
    backgroundColor: theme.colors.primarySoft,
    borderRadius: theme.radius.card,
    height: 54,
    justifyContent: 'center',
    width: 54,
  },
  heroSub: {
    color: theme.colors.muted,
    fontSize: theme.typography.label,
    lineHeight: 20,
    marginTop: theme.spacing.xs,
  },
  heroTitle: {
    color: theme.colors.text,
    fontSize: 24,
    fontWeight: '900',
    marginTop: theme.spacing.xs,
  },
  heroTop: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.md,
  },
  iconButton: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.pill,
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
  linkText: {
    color: theme.colors.primaryDark,
    fontSize: theme.typography.label,
    fontWeight: '900',
  },
  ownedBookIcon: {
    backgroundColor: theme.colors.primarySoft,
  },
  searchButton: {
    alignItems: 'center',
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.control,
    height: 44,
    justifyContent: 'center',
    paddingHorizontal: theme.spacing.md,
  },
  searchButtonText: {
    color: theme.colors.textInverse,
    fontWeight: '900',
  },
  searchShell: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.control,
    borderWidth: 1,
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginTop: theme.spacing.md,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
  },
  sectionHead: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  selectedHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: theme.spacing.md,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.xs,
    marginTop: theme.spacing.xs,
  },
  word: {
    color: theme.colors.text,
    fontSize: 19,
    fontWeight: '900',
  },
  wordActions: {
    gap: theme.spacing.xs,
  },
  wordBody: {
    flex: 1,
  },
  wordMeta: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '700',
  },
  wordRow: {
    borderBottomColor: theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: theme.spacing.md,
    paddingVertical: theme.spacing.md,
  },
})
