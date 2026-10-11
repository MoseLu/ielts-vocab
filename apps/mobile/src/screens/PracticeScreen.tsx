import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Pressable, Text, View } from 'react-native'
import { CheckCircle2, Mic, XCircle } from 'lucide-react-native'
import {
  PRACTICE_MODE_LABELS,
  SMART_PRACTICE_DIMENSION_LABELS,
  buildNextErrorReviewRoundWords,
  buildPracticeOptions,
  resolveSmartPracticeMode,
  type MobileBook,
  type MobileChapter,
  type PracticeMode,
} from '@ielts-vocab/app-core'
import { Card, Field, Heading, Meta, Pill, PrimaryButton, ScreenScroll, StatusText } from '../components/primitives'
import type { Navigate, NavigateOptions } from '../navigation/types'
import { useMobileSpeechRecognition } from '../speech/useMobileSpeechRecognition'
import { theme } from '../theme'
import {
  hydrateErrorReviewProgress,
  hydratePracticeSession,
  loadBookChapters,
  loadPracticeBootstrap,
  loadPracticeQueue,
  persistErrorReviewProgress,
  practiceSessionDependencies,
  useMobileSmartPractice,
  usePracticeAnswerSubmission,
  usePracticeAudioModes,
  usePracticeSessionState,
} from '../features/practice/runtime'
import { PracticeControlSurface } from './PracticeControlSurface'
import { PracticeCompletionCard, PracticeEntryPanel, type PracticeEntry, type PracticeEntryKey } from './PracticeEntryPanel'
import { entryForMode, initialDueReviewRequested, initialEntry, isRecognitionReviewMode, searchableText } from './PracticeScreen.helpers'
import { PracticeScopeSheet } from './PracticeScopeSheet'
import { PracticeStatusHeader } from './PracticeStatusHeader'
import { styles } from './PracticeScreen.styles'

type SheetState = 'mode' | 'scope' | null

export function PracticeScreen({ navigate, options }: { navigate: Navigate; options?: NavigateOptions }) {
  const { start, state: speechState, stop } = useMobileSpeechRecognition('en')
  const { chooseSmartDimension, recordSmartAnswer, refreshSmartPracticeContext } = useMobileSmartPractice()
  const [entry, setEntry] = useState<PracticeEntryKey | null>(initialEntry(options))
  const [mode, setMode] = useState<PracticeMode>(options?.mode ?? 'quickmemory')
  const [dueReviewRequested, setDueReviewRequested] = useState(initialDueReviewRequested(options))
  const [sheet, setSheet] = useState<SheetState>(null)
  const [books, setBooks] = useState<MobileBook[]>([])
  const [chapters, setChapters] = useState<MobileChapter[]>([])
  const [bookId, setBookId] = useState(options?.bookId ?? '')
  const [chapterId, setChapterId] = useState<string | number | null>(options?.chapterId ?? null)
  const [scopeQuery, setScopeQuery] = useState('')
  const {
    answer,
    applyHydratedSession,
    chapterBaselineRef,
    correctCount,
    error,
    errorReviewRound,
    errorRoundResults,
    feedback,
    index,
    loading,
    queue,
    queueSource,
    setAnswer,
    setCorrectCount,
    setError,
    setErrorRoundResults,
    setFeedback,
    setIndex,
    setLoading,
    setWrongCount,
    startedAtRef,
    startErrorReviewRound,
    wrongCount,
  } = usePracticeSessionState()
  const cleanupRef = useRef<(() => void) | null>(null)

  const selectedBook = useMemo(() => books.find(book => String(book.id) === bookId) ?? null, [bookId, books])
  const selectedChapter = useMemo(
    () => chapters.find(chapter => String(chapter.id) === String(chapterId)) ?? null,
    [chapterId, chapters],
  )
  const currentWord = queue[index]
  const smartDimension = useMemo(() => currentWord ? chooseSmartDimension(currentWord) : 'meaning', [chooseSmartDimension, currentWord])
  const activeMode = mode === 'smart' ? resolveSmartPracticeMode(smartDimension) : mode
  const completed = queue.length > 0 && index >= queue.length
  const errorReviewRetryWords = mode === 'errors' && completed
    ? buildNextErrorReviewRoundWords(queue, errorRoundResults)
    : []
  const optionsForWord = useMemo(() => currentWord ? buildPracticeOptions(currentWord, queue) : [], [currentWord, queue])
  const scopeTerm = scopeQuery.trim().toLowerCase()
  const filteredBooks = useMemo(
    () => books.filter(book => !scopeTerm || searchableText(`${book.title} ${book.description}`).includes(scopeTerm)),
    [books, scopeTerm],
  )
  const filteredChapters = useMemo(
    () => chapters.filter((chapter, idx) => !scopeTerm || searchableText(`${idx + 1} ${chapter.title}`).includes(scopeTerm)),
    [chapters, scopeTerm],
  )

  useEffect(() => {
    let active = true
    setLoading(true)
    loadPracticeBootstrap(options)
      .then(async ({ books: nextBooks, chapters: nextChapters, initialBookId }) => {
        if (!active) return
        setBooks(nextBooks)
        const shouldLoadDueReview = initialDueReviewRequested(options)
        if (!initialBookId) {
          if (options?.mode) setEntry(initialEntry(options))
          setDueReviewRequested(shouldLoadDueReview)
          if (options?.mode === 'errors') await startPractice('errors', '', null, false)
          if (shouldLoadDueReview) await startPractice(options?.mode ?? 'quickmemory', '', null, true)
          return
        }
        setBookId(initialBookId)
        setChapters(nextChapters)
        if (options?.bookId || options?.mode) setEntry(initialEntry(options))
        setDueReviewRequested(shouldLoadDueReview)
        if (options?.chapterId) {
          setChapterId(options.chapterId)
          await startPractice(options.mode ?? 'quickmemory', initialBookId, options.chapterId, shouldLoadDueReview)
        } else if (options?.mode === 'errors') {
          await startPractice('errors', initialBookId, null, false)
        } else if (shouldLoadDueReview) {
          await startPractice(options?.mode ?? 'quickmemory', options?.bookId ? initialBookId : '', null, true)
        }
      })
      .catch(err => setError(err instanceof Error ? err.message : '词书加载失败'))
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options?.bookId, options?.chapterId, options?.mode])

  async function selectBook(nextBookId: string) {
    setBookId(nextBookId)
    setChapterId(null)
    setChapters(await loadBookChapters(nextBookId))
  }

  async function startPractice(nextMode = mode, nextBookId = bookId, nextChapterId = chapterId, nextDueReviewRequested = dueReviewRequested) {
    setLoading(true)
    setError('')
    setFeedback('')
    try {
      const { queueSource: nextQueueSource, words } = await loadPracticeQueue({
        bookId: nextBookId,
        chapterId: nextChapterId,
        dueReviewRequested: nextDueReviewRequested,
        mode: nextMode,
        options,
        refreshSmartPracticeContext,
      })
      const savedErrorProgress = nextQueueSource === 'errors'
        ? await hydrateErrorReviewProgress(words, nextMode)
        : null
      const session = savedErrorProgress
        ? {
          chapterBaseline: { correctCount: 0, wrongCount: 0 },
          correctCount: savedErrorProgress.correctCount,
          index: savedErrorProgress.currentIndex,
          queue: words,
          resumed: true,
          wrongCount: savedErrorProgress.wrongCount,
        }
        : await hydratePracticeSession({
          bookId: nextBookId,
          chapterId: nextChapterId,
          dependencies: practiceSessionDependencies,
          mode: nextMode,
          queueSource: nextQueueSource,
          words,
        })
      applyHydratedSession({ queueSource: nextQueueSource, savedErrorProgress, session })
      if (!words.length && nextQueueSource === 'due-review') setFeedback('暂无到期复习词，可以切换范围或稍后再来。')
      else if (!words.length && nextQueueSource === 'errors') setFeedback('当前筛选没有待恢复错词，可以换一个维度或模式。')
      else if (session.resumed) setFeedback('已恢复未完成练习')
    } catch (err) {
      setError(err instanceof Error ? err.message : '练习加载失败')
    } finally {
      setLoading(false)
    }
  }

  async function openEntry(item: PracticeEntry) {
    if (item.key === 'speaking') {
      navigate('exams')
      return
    }
    const nextMode = item.mode ?? 'quickmemory'
    const nextDueReviewRequested = item.key === 'ebbinghaus' && isRecognitionReviewMode(nextMode)
    setEntry(item.key)
    setMode(nextMode)
    setDueReviewRequested(nextDueReviewRequested)
    if (nextMode === 'errors' || bookId || nextDueReviewRequested) await startPractice(nextMode, bookId, chapterId, nextDueReviewRequested)
    else setSheet('scope')
  }

  async function chooseMode(nextMode: PracticeMode) {
    const nextEntry = entryForMode(nextMode)
    const nextDueReviewRequested = nextEntry === 'ebbinghaus' && isRecognitionReviewMode(nextMode)
    setMode(nextMode)
    setEntry(nextEntry)
    setDueReviewRequested(nextDueReviewRequested)
    setSheet(null)
    if (nextMode === 'errors' || chapterId || queue.length || bookId || nextDueReviewRequested) {
      await startPractice(nextMode, bookId, chapterId, nextDueReviewRequested)
    }
  }

  async function chooseChapter(chapter: MobileChapter | null) {
    const nextChapterId = chapter?.id ?? null
    setChapterId(nextChapterId)
    setSheet(null)
    await startPractice(mode, bookId, nextChapterId, dueReviewRequested)
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

  const {
    audioStatus,
    pauseRadio,
    playWord,
    radioInteractionCount,
    radioPaused,
    resumeRadio,
    skipRadioNext,
  } = usePracticeAudioModes({
    currentWord,
    index,
    mode: activeMode,
    onRadioAdvance: async () => submit('played'),
    setError,
    setFeedback,
  })

  const submitAnswer = usePracticeAnswerSubmission({
    activeMode,
    bookId,
    chapterBaselineRef,
    chapterId,
    correctCount,
    currentWord,
    errorReviewRound,
    errorRoundResults,
    index,
    mode,
    options,
    playWord,
    queue,
    queueSource,
    recordSmartAnswer,
    setAnswer,
    setCorrectCount,
    setErrorRoundResults,
    setFeedback,
    setIndex,
    setWrongCount,
    smartDimension,
    startedAtRef,
    wrongCount,
  })

  async function submit(value = answer) {
    await submitAnswer(value)
  }

  async function startNextErrorReviewRound() {
    const nextRound = errorReviewRound + 1
    startErrorReviewRound({ round: nextRound, words: errorReviewRetryWords })
    await persistErrorReviewProgress({
      correct: 0,
      current: 0,
      mode,
      options,
      results: {},
      round: nextRound,
      wrong: 0,
      words: errorReviewRetryWords,
    })
  }

  const progress = queue.length ? Math.min(100, (index / queue.length) * 100) : 0
  const chapterLabel = queueSource === 'errors'
    ? '错词队列'
    : queueSource === 'due-review'
      ? selectedChapter?.title || selectedBook?.title || '到期复习'
      : selectedChapter?.title || '全书'
  const emptyTitle = queueSource === 'due-review' ? '暂无到期复习' : mode === 'errors' ? '错词练习' : '选择章节开始练习'
  const emptyHint = queueSource === 'due-review'
    ? '当前范围没有到期词，可以切换词书/章节过滤条件后重试。'
    : mode === 'errors'
      ? '当前会读取错词队列。'
      : '可以从顶部状态栏搜索词书或章节。'
  const followTranscript = (speechState.finalText || speechState.partialText || '').trim()
  const followTranscriptLabel = speechState.finalText ? '最终识别' : speechState.partialText ? '实时识别' : '等待录音'

  return (
    <View style={styles.practiceRoot}>
      {error || speechState.error || loading ? (
        <View pointerEvents="none" style={styles.practiceStatusOverlay}>
          <StatusText error={error || speechState.error} loading={loading} />
        </View>
      ) : null}
      <ScreenScroll hideHeader title="练习">
        {!entry ? (
          <PracticeEntryPanel onOpen={item => void openEntry(item)} />
        ) : (
          <>
            <PracticeStatusHeader
              chapterLabel={chapterLabel}
              correctCount={correctCount}
              entry={entry}
              mode={mode}
              onOpenMode={() => setSheet('mode')}
              onOpenScope={() => setSheet('scope')}
              progress={progress}
              queueIndex={index}
              queueLength={queue.length}
              selectedBookTitle={selectedBook?.title}
              wrongCount={wrongCount}
            />
            <PracticeControlSurface
              activeMode={activeMode}
              chapterLabel={chapterLabel}
              currentWord={currentWord}
              mode={mode}
              onOpenMode={() => setSheet('mode')}
              onOpenScope={() => setSheet('scope')}
              onPlayWord={() => void playWord()}
              onRestart={() => void startPractice(mode, bookId, chapterId)}
              onSelectWord={setIndex}
              onSetFeedback={setFeedback}
              queue={queue}
              queueIndex={index}
            />
            {currentWord ? (
              <Card style={styles.workbench}>
                <View style={styles.workbenchTop}>
                  <Pill label={`${index + 1}/${queue.length || 1}`} />
                  <Pill label={speechState.status === 'recording' ? '录音中' : mode === 'smart' ? `${PRACTICE_MODE_LABELS.smart} · ${SMART_PRACTICE_DIMENSION_LABELS[smartDimension]}` : PRACTICE_MODE_LABELS[mode]} />
                </View>
                <Text style={styles.word}>{activeMode === 'meaning' ? currentWord.definition : currentWord.word}</Text>
                <Text style={styles.wordMeta}>{[currentWord.phonetic, currentWord.pos].filter(Boolean).join(' ') || 'IELTS 词条'}</Text>
                {activeMode !== 'meaning' ? <Text style={styles.definition}>{currentWord.definition}</Text> : null}
                {activeMode === 'listening' || activeMode === 'dictation' ? <PrimaryButton label="播放发音" onPress={() => void playWord()} testID="practice.audio.replay" /> : null}
                {audioStatus && mode !== 'follow' ? <Meta>{audioStatus}</Meta> : null}
                {mode === 'follow' ? <PrimaryButton label={speechState.status === 'recording' ? '停止录音' : '开始跟读'} onPress={() => void toggleRecording()} /> : null}
                {mode === 'follow' ? (
                  <View style={styles.micStrip}>
                    <Mic color={theme.colors.primaryDark} size={18} />
                    <Text style={styles.micText}>音量 {Math.round(speechState.level * 100)}% · {followTranscriptLabel}：{followTranscript || '暂无语音结果'}</Text>
                  </View>
                ) : null}
                {mode === 'quickmemory' || mode === 'test' ? (
                  <View style={styles.answerRow}>
                    <Pressable accessibilityLabel="认识" accessibilityRole="button" style={[styles.answerButton, styles.confirmButton]} onPress={() => void submit('known')} testID="practice.quickmemory.known">
                      <CheckCircle2 color={theme.colors.success} size={18} />
                      <Text style={styles.answerButtonText}>认识</Text>
                    </Pressable>
                    <Pressable accessibilityLabel="不认识" accessibilityRole="button" style={[styles.answerButton, styles.rejectButton]} onPress={() => void submit('unknown')} testID="practice.quickmemory.unknown">
                      <XCircle color={theme.colors.danger} size={18} />
                      <Text style={styles.answerButtonText}>不认识</Text>
                    </Pressable>
                  </View>
                ) : activeMode === 'listening' ? (
                  <View style={styles.choiceWrap}>
                    {optionsForWord.map(option => (
                      <Pressable key={option} accessibilityLabel={`选择答案-${option}`} accessibilityRole="button" style={styles.choiceButton} onPress={() => void submit(option)} testID="practice.choice">
                        <Text style={styles.choiceText}>{option}</Text>
                      </Pressable>
                    ))}
                  </View>
                ) : mode === 'radio' ? (
                  <View style={styles.radioControls}>
                    <PrimaryButton label={radioPaused ? '继续播放' : '暂停播放'} onPress={() => void (radioPaused ? resumeRadio() : pauseRadio())} testID="practice.radio.toggle" tone="neutral" />
                    <PrimaryButton label="下一词" onPress={() => void skipRadioNext()} testID="practice.radio.next" />
                  </View>
                ) : mode !== 'follow' ? (
                  <>
                    <Field value={answer} onChangeText={setAnswer} placeholder="输入答案" testID="practice.answer" />
                    <PrimaryButton label="提交" onPress={() => void submit()} testID="practice.submit" />
                  </>
                ) : (
                  <PrimaryButton disabled={!followTranscript} label="跟读完成，下一词" onPress={() => void submit(followTranscript)} testID="practice.follow.submit" />
                )}
                {mode === 'radio' ? <Meta>{`随身听${radioPaused ? '已暂停' : '播放中'} · 已记录 ${radioInteractionCount} 次操作`}</Meta> : null}
                {feedback ? <Meta>{feedback}</Meta> : null}
                {activeMode !== 'follow' && currentWord.examples?.length ? (
                  <View style={styles.exampleBox}>
                    <Text style={styles.exampleTitle}>例句</Text>
                    <Text style={styles.exampleText}>{currentWord.examples[0]?.en || ''}</Text>
                    <Text style={styles.exampleHint}>{currentWord.examples[0]?.zh || ''}</Text>
                  </View>
                ) : null}
              </Card>
            ) : completed ? (
              <>
                <PracticeCompletionCard
                  onChangeScope={() => setSheet('scope')}
                  onRestart={() => void startPractice(mode, bookId, chapterId)}
                  wordCount={queue.length} />
                {errorReviewRetryWords.length > 0 ? (
                  <Card>
                    <Heading>下一轮错词</Heading>
                    <Meta>还有 {errorReviewRetryWords.length} 个词本轮仍答错，可以只复习这些词。</Meta>
                    <PrimaryButton label="复习仍错词" onPress={() => void startNextErrorReviewRound()} testID="practice.errors.nextRound" />
                  </Card>
                ) : null}
              </>
            ) : (
              <Card>
                <Heading>{emptyTitle}</Heading>
                <Meta>{feedback || emptyHint}</Meta>
                <PrimaryButton label="选择范围" onPress={() => setSheet('scope')} />
              </Card>
            )}
          </>
        )}
      </ScreenScroll>
      <PracticeScopeSheet
        bookId={bookId}
        chapterId={chapterId}
        filteredBooks={filteredBooks}
        filteredChapters={filteredChapters}
        mode={mode}
        onChooseChapter={chapter => void chooseChapter(chapter)}
        onChooseMode={nextMode => void chooseMode(nextMode)}
        onClose={() => setSheet(null)}
        onSelectBook={nextBookId => void selectBook(nextBookId)}
        scopeQuery={scopeQuery}
        setScopeQuery={setScopeQuery}
        sheet={sheet}
      />
    </View>
  )
}
