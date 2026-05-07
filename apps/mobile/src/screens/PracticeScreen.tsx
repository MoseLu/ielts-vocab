import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Text } from 'react-native'
import {
  PRACTICE_MODE_LABELS,
  buildPracticeOptions,
  buildProgressSnapshot,
  buildQuickMemorySyncRecord,
  buildWrongWordRecord,
  evaluatePracticeAnswer,
  type MobileBook,
  type MobileChapter,
  type MobileWord,
  type PracticeMode,
} from '@ielts-vocab/app-core'
import { loadBooks, loadChapterWords, loadChapters, loadWrongWords, logPracticeSession, savePracticeProgress, syncQuickMemory, syncWrongWord } from '../api/learnerApi'
import { Card, Field, Heading, Meta, Pill, PrimaryButton, Row, ScreenScroll, StatusText } from '../components/primitives'
import type { NavigateOptions } from '../navigation/types'
import { playRemoteAudio } from '../native/NativeAudioPlayer'
import { useMobileSpeechRecognition } from '../speech/useMobileSpeechRecognition'

const MODES: PracticeMode[] = ['smart', 'quickmemory', 'listening', 'meaning', 'dictation', 'follow', 'radio', 'errors']

export function PracticeScreen({ options }: { options?: NavigateOptions }) {
  const { start, state: speechState, stop } = useMobileSpeechRecognition('en')
  const [mode, setMode] = useState<PracticeMode>(options?.mode ?? 'quickmemory')
  const [books, setBooks] = useState<MobileBook[]>([])
  const [chapters, setChapters] = useState<MobileChapter[]>([])
  const [bookId, setBookId] = useState(options?.bookId ?? '')
  const [chapterId, setChapterId] = useState<string | number | null>(options?.chapterId ?? null)
  const [queue, setQueue] = useState<MobileWord[]>([])
  const [index, setIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [correctCount, setCorrectCount] = useState(0)
  const [wrongCount, setWrongCount] = useState(0)
  const [feedback, setFeedback] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const cleanupRef = useRef<(() => void) | null>(null)
  const startedAtRef = useRef(Date.now())

  const currentWord = queue[index]
  const optionsForWord = useMemo(
    () => currentWord ? buildPracticeOptions(currentWord, queue) : [],
    [currentWord, queue],
  )

  useEffect(() => {
    void loadBooks().then(nextBooks => {
      setBooks(nextBooks)
      const firstBook = options?.bookId || String(nextBooks[0]?.id ?? '')
      if (firstBook) void selectBook(firstBook)
    }).catch(err => setError(err instanceof Error ? err.message : '词书加载失败'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function selectBook(nextBookId: string) {
    setBookId(nextBookId)
    setChapterId(null)
    setChapters(await loadChapters(nextBookId))
  }

  async function startPractice(nextMode = mode, nextChapterId = chapterId) {
    setLoading(true)
    setError('')
    setFeedback('')
    try {
      const words = nextMode === 'errors'
        ? await loadWrongWords()
        : await loadChapterWords(bookId, nextChapterId)
      setQueue(words)
      setIndex(0)
      setCorrectCount(0)
      setWrongCount(0)
      setAnswer('')
      startedAtRef.current = Date.now()
    } catch (err) {
      setError(err instanceof Error ? err.message : '练习加载失败')
    } finally {
      setLoading(false)
    }
  }

  async function toggleRecording() {
    if (speechState.status === 'recording') {
      cleanupRef.current?.()
      cleanupRef.current = null
      await stop()
      return
    }
    setError('')
    try {
      cleanupRef.current = await start()
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法开始录音')
    }
  }

  async function playWord() {
    if (!currentWord) return
    const params = new URLSearchParams({ w: currentWord.word, cache_only: '1' })
    await playRemoteAudio(`/api/tts/word-audio?${params.toString()}`).catch(err => {
      setError(err instanceof Error ? err.message : '播放失败')
    })
  }

  async function submit(value = answer) {
    if (!currentWord) return
    const result = evaluatePracticeAnswer(currentWord, mode, value)
    const nextCorrect = correctCount + (result.correct ? 1 : 0)
    const nextWrong = wrongCount + (result.correct ? 0 : 1)
    const nextIndex = index + 1
    setCorrectCount(nextCorrect)
    setWrongCount(nextWrong)
    setFeedback(result.feedback)
    setAnswer('')
    if (!result.correct || value === 'unknown') {
      await syncWrongWord(buildWrongWordRecord(currentWord, mode)).catch(() => undefined)
    }
    if (mode === 'quickmemory') {
      await syncQuickMemory(buildQuickMemorySyncRecord(currentWord, value === 'known')).catch(() => undefined)
    }
    const snapshot = buildProgressSnapshot({
      correctCount: nextCorrect,
      currentIndex: nextIndex,
      queue,
      wrongCount: nextWrong,
    })
    if (bookId && mode !== 'errors') {
      await savePracticeProgress({
        bookId,
        chapterId,
        mode,
        ...snapshot,
      }).catch(() => undefined)
    }
    if (snapshot.isCompleted) {
      await logPracticeSession({
        bookId,
        chapterId,
        correctCount: nextCorrect,
        durationSeconds: Math.round((Date.now() - startedAtRef.current) / 1000),
        mode,
        wordsStudied: snapshot.wordsLearned || nextIndex,
        wrongCount: nextWrong,
      }).catch(() => undefined)
    }
    setIndex(nextIndex)
  }

  return (
    <ScreenScroll hideHeader title="练习" subtitle="基础模式原生闭环：答题、进度、错词、复习和跟读录音。">
      <StatusText error={error || speechState.error} loading={loading} />
      <Card>
        <Heading>模式</Heading>
        <Row>{MODES.map(item => (
          <PrimaryButton
            key={item}
            label={PRACTICE_MODE_LABELS[item]}
            tone={item === mode ? 'primary' : 'neutral'}
            onPress={() => {
              setMode(item)
              void startPractice(item)
            }}
          />
        ))}</Row>
      </Card>
      <Card>
        <Heading>范围</Heading>
        <Row>{books.slice(0, 6).map(book => (
          <PrimaryButton key={String(book.id)} label={book.title} tone={String(book.id) === bookId ? 'primary' : 'neutral'} onPress={() => void selectBook(String(book.id))} />
        ))}</Row>
        <Row>{chapters.slice(0, 12).map(chapter => (
          <PrimaryButton key={String(chapter.id)} label={chapter.title} tone={String(chapter.id) === String(chapterId) ? 'primary' : 'neutral'} onPress={() => {
            setChapterId(chapter.id)
            void startPractice(mode, chapter.id)
          }} />
        ))}</Row>
        <PrimaryButton label="开始 / 重载练习" onPress={() => void startPractice()} />
      </Card>
      {currentWord ? (
        <Card>
          <Row>
            <Pill label={`${index + 1} / ${queue.length}`} />
            <Pill label={`对 ${correctCount}`} />
            <Pill label={`错 ${wrongCount}`} />
          </Row>
          <Heading>{mode === 'meaning' ? currentWord.definition : currentWord.word}</Heading>
          <Meta>{currentWord.phonetic} {currentWord.pos}</Meta>
          {mode !== 'meaning' ? <Text>{currentWord.definition}</Text> : null}
          {mode === 'listening' || mode === 'dictation' || mode === 'radio' ? (
            <PrimaryButton label="播放发音" onPress={() => void playWord()} />
          ) : null}
          {mode === 'follow' ? (
            <>
              <PrimaryButton label={speechState.status === 'recording' ? '停止录音' : '开始跟读'} onPress={() => void toggleRecording()} />
              <Meta>音量 {Math.round(speechState.level * 100)}% · {speechState.finalText || speechState.partialText || '等待录音'}</Meta>
            </>
          ) : null}
          {mode === 'quickmemory' ? (
            <Row>
              <PrimaryButton label="认识" onPress={() => void submit('known')} />
              <PrimaryButton label="不认识" tone="danger" onPress={() => void submit('unknown')} />
            </Row>
          ) : mode === 'listening' ? (
            optionsForWord.map(option => <PrimaryButton key={option} label={option} tone="neutral" onPress={() => void submit(option)} />)
          ) : mode === 'radio' ? (
            <PrimaryButton label="下一词" onPress={() => void submit('played')} />
          ) : mode !== 'follow' ? (
            <>
              <Field value={answer} onChangeText={setAnswer} placeholder="输入答案" />
              <PrimaryButton label="提交" onPress={() => void submit()} />
            </>
          ) : (
            <PrimaryButton label="跟读完成，下一词" onPress={() => void submit('followed')} />
          )}
          {feedback ? <Meta>{feedback}</Meta> : null}
        </Card>
      ) : (
        <Card>
          <Heading>请选择词书和章节</Heading>
          <Meta>错词强化会直接读取错词队列，其他模式需要先选择章节。</Meta>
        </Card>
      )}
    </ScreenScroll>
  )
}
