import React, { useEffect, useState } from 'react'
import { Text } from 'react-native'
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
    const wordsToCreate = customWords
      .split(/\n+/)
      .map(line => line.trim())
      .filter(Boolean)
      .map(line => {
        const [word, definition = ''] = line.split(/[,，\t]/)
        return { word: word.trim(), definition: definition.trim(), phonetic: '', pos: '', group_key: '', book_id: '', book_title: '', chapter_id: '', chapter_title: '', examples: [], listening_confusables: [] }
      })
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
      <Card>
        <Field value={search} onChangeText={setSearch} placeholder="搜索词书" />
        <PrimaryButton label="搜索" onPress={() => refreshBooks(search)} />
      </Card>
      {selectedBook ? (
        <Card>
          <Heading>{selectedBook.title}</Heading>
          <Meta>{selectedBook.level || selectedBook.category || 'IELTS'} · {selectedBook.total_words || selectedBook.word_count || 0} 词</Meta>
          <Row>
            <PrimaryButton label="加入我的词书" onPress={() => void addMyBook(String(selectedBook.id)).then(() => refreshBooks())} />
            <PrimaryButton label="开始练习" onPress={() => navigate('practice', { bookId: String(selectedBook.id), chapterId: selectedChapter?.id })} />
            <PrimaryButton label="返回列表" tone="neutral" onPress={() => setSelectedBook(null)} />
          </Row>
        </Card>
      ) : null}
      {selectedBook && chapters.map(chapter => (
        <Card key={String(chapter.id)}>
          <Heading>{chapter.title}</Heading>
          <Meta>{chapter.word_count || chapter.group_count || 0} 项</Meta>
          <PrimaryButton label="打开章节" onPress={() => void openChapter(chapter)} />
        </Card>
      ))}
      {selectedChapter && words.map(word => (
        <Card key={word.word}>
          <Heading>{word.word}</Heading>
          <Meta>{word.phonetic} {word.pos}</Meta>
          <Body>{word.definition}</Body>
          <Row>
            <Pill label={String(selectedChapter.title)} />
            <PrimaryButton label="收藏" onPress={() => void setFavorite(word.word, true)} />
            <PrimaryButton label="熟词" onPress={() => void setFamiliar(word.word, true)} />
            <PrimaryButton label="保存笔记" tone="neutral" onPress={() => void saveWordNote(word.word, note)} />
          </Row>
          <Field value={note} onChangeText={setNote} placeholder="给当前词写笔记" multiline />
        </Card>
      ))}
      {!selectedBook && books.map(book => (
        <Card key={String(book.id)}>
          <Heading>{book.title}</Heading>
          <Meta>{book.level || book.category || 'IELTS'} · {book.total_words || book.word_count || 0} 词</Meta>
          {book.description ? <Body>{book.description}</Body> : null}
          <Row>
            {myBooks.includes(String(book.id)) ? <Pill label="我的词书" /> : null}
            {book.practice_mode === 'match' ? <Pill label="易混词" /> : null}
          </Row>
          <PrimaryButton label="打开" onPress={() => void openBook(book)} />
        </Card>
      ))}
      <Card>
        <Heading>自定义词书</Heading>
        <Field value={customTitle} onChangeText={setCustomTitle} placeholder="词书标题" />
        <Field value={customWords} onChangeText={setCustomWords} placeholder="每行：word,中文释义" multiline />
        <PrimaryButton label="创建自定义词书" onPress={() => void createBook().catch(err => setError(err.message))} />
      </Card>
      {!loading && !books.length ? <Text>暂无词书。</Text> : null}
    </ScreenScroll>
  )
}
