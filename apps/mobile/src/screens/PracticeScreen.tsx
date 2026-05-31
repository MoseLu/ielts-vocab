import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Modal, Pressable, ScrollView, Text, View } from 'react-native'
import { CheckCircle2, ChevronRight, Mic, XCircle } from 'lucide-react-native'
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
import { StickerLayer, practiceSheetStickerSlots } from '../components/stickers'
import type { Navigate, NavigateOptions } from '../navigation/types'
import { playRemoteAudio } from '../native/NativeAudioPlayer'
import { useMobileSpeechRecognition } from '../speech/useMobileSpeechRecognition'
import { theme } from '../theme'
import { PracticeCompletionCard, PracticeEntryPanel, type PracticeEntry, type PracticeEntryKey } from './PracticeEntryPanel'
import { styles } from './PracticeScreen.styles'

const MODES: PracticeMode[] = ['smart', 'quickmemory', 'listening', 'meaning', 'dictation', 'follow', 'radio', 'errors']

type SheetState = 'mode' | 'scope' | null

const MODE_HINTS: Record<PracticeMode, string> = {
  smart: '按当前词书和复习状态智能出题',
  quickmemory: '快速认词，写入复习队列',
  test: '听音判断熟悉度，写入复习队列',
  listening: '听音辨义，训练反应速度',
  meaning: '看中文，主动拼出英文',
  dictation: '听音写词，抓住拼写细节',
  follow: '跟读发音，记录语音表现',
  radio: '连续播放，适合碎片复习',
  errors: '读取错词队列，直接开始清理',
}

function scoreLabel(label: string, value: number) {
  return `${label} ${value}`
}

function entryForMode(mode?: PracticeMode): PracticeEntryKey {
  if (mode === 'errors') return 'errors'
  if (mode === 'follow') return 'follow'
  if (mode === 'quickmemory') return 'ebbinghaus'
  return 'regular'
}

function entryLabel(entry: PracticeEntryKey | null, mode: PracticeMode) {
  if (entry === 'errors') return '错词练习'
  if (entry === 'ebbinghaus') return '艾宾浩斯'
  if (entry === 'follow') return '跟读练习'
  return PRACTICE_MODE_LABELS[mode]
}

function searchableText(value: unknown) {
  return String(value ?? '').toLowerCase()
}

export function PracticeScreen({ navigate, options }: { navigate: Navigate; options?: NavigateOptions }) {
  const { start, state: speechState, stop } = useMobileSpeechRecognition('en')
  const [entry, setEntry] = useState<PracticeEntryKey | null>(options?.bookId || options?.mode ? entryForMode(options?.mode) : null)
  const [mode, setMode] = useState<PracticeMode>(options?.mode ?? 'quickmemory')
  const [sheet, setSheet] = useState<SheetState>(null)
  const [books, setBooks] = useState<MobileBook[]>([])
  const [chapters, setChapters] = useState<MobileChapter[]>([])
  const [bookId, setBookId] = useState(options?.bookId ?? '')
  const [chapterId, setChapterId] = useState<string | number | null>(options?.chapterId ?? null)
  const [scopeQuery, setScopeQuery] = useState('')
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

  const selectedBook = useMemo(() => books.find(book => String(book.id) === bookId) ?? null, [bookId, books])
  const selectedChapter = useMemo(
    () => chapters.find(chapter => String(chapter.id) === String(chapterId)) ?? null,
    [chapterId, chapters],
  )
  const currentWord = queue[index]
  const completed = queue.length > 0 && index >= queue.length
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
    loadBooks()
      .then(async nextBooks => {
        if (!active) return
        setBooks(nextBooks)
        const initialBookId = options?.bookId || String(nextBooks[0]?.id ?? '')
        if (!initialBookId) return
        setBookId(initialBookId)
        const nextChapters = await loadChapters(initialBookId)
        if (!active) return
        setChapters(nextChapters)
        if (options?.bookId || options?.mode) setEntry(entryForMode(options?.mode))
        if (options?.chapterId) {
          setChapterId(options.chapterId)
          await startPractice(options.mode ?? 'quickmemory', initialBookId, options.chapterId)
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
    setChapters(await loadChapters(nextBookId))
  }

  async function startPractice(nextMode = mode, nextBookId = bookId, nextChapterId = chapterId) {
    setLoading(true)
    setError('')
    setFeedback('')
    try {
      if (nextMode !== 'errors' && !nextBookId) throw new Error('请先选择练习范围')
      const words = nextMode === 'errors' ? await loadWrongWords() : await loadChapterWords(nextBookId, nextChapterId)
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

  async function openEntry(item: PracticeEntry) {
    if (item.key === 'speaking') {
      navigate('exams')
      return
    }
    const nextMode = item.mode ?? 'quickmemory'
    setEntry(item.key)
    setMode(nextMode)
    if (nextMode === 'errors' || bookId) await startPractice(nextMode)
    else setSheet('scope')
  }

  async function chooseMode(nextMode: PracticeMode) {
    setMode(nextMode)
    setEntry(entryForMode(nextMode))
    setSheet(null)
    if (nextMode === 'errors' || chapterId || queue.length || bookId) await startPractice(nextMode)
  }

  async function chooseChapter(chapter: MobileChapter | null) {
    const nextChapterId = chapter?.id ?? null
    setChapterId(nextChapterId)
    setSheet(null)
    await startPractice(mode, bookId, nextChapterId)
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
    if (!result.correct || value === 'unknown') await syncWrongWord(buildWrongWordRecord(currentWord, mode)).catch(() => undefined)
    if (mode === 'quickmemory') await syncQuickMemory(buildQuickMemorySyncRecord(currentWord, value === 'known')).catch(() => undefined)
    const snapshot = buildProgressSnapshot({ correctCount: nextCorrect, currentIndex: nextIndex, queue, wrongCount: nextWrong })
    if (bookId && mode !== 'errors') await savePracticeProgress({ bookId, chapterId, mode, ...snapshot }).catch(() => undefined)
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

  const progress = queue.length ? Math.min(100, (index / queue.length) * 100) : 0
  const chapterLabel = mode === 'errors' ? '错词队列' : selectedChapter?.title || '全书'

  return (
    <>
      <ScreenScroll hideHeader title="练习">
        <StatusText error={error || speechState.error} loading={loading} />
        {!entry ? (
          <PracticeEntryPanel onOpen={item => void openEntry(item)} />
        ) : (
          <>
            <View style={styles.practiceStatusBar}>
              <Pressable accessibilityRole="button" onPress={() => setSheet('scope')} style={styles.statusSegment}>
                <Text style={styles.statusLabel}>词书</Text>
                <Text numberOfLines={1} style={styles.statusValue}>{selectedBook?.title || '选择词书'}</Text>
              </Pressable>
              <Pressable accessibilityRole="button" onPress={() => setSheet('scope')} style={styles.statusSegment}>
                <Text style={styles.statusLabel}>章节</Text>
                <Text numberOfLines={1} style={styles.statusValue}>{chapterLabel}</Text>
              </Pressable>
              <Pressable accessibilityRole="button" onPress={() => setSheet('mode')} style={styles.statusSegment}>
                <Text style={styles.statusLabel}>模式</Text>
                <Text numberOfLines={1} style={styles.statusValue}>{entryLabel(entry, mode)}</Text>
              </Pressable>
            </View>
            <View style={styles.progressMini}>
              <View style={styles.progressTrack}>
                <View style={[styles.progressFill, { width: `${progress}%` }]} />
              </View>
              <View style={styles.statRow}>
                <Pill label={`${index}/${queue.length || 0}`} />
                <Pill label={scoreLabel('对', correctCount)} />
                <Pill label={scoreLabel('错', wrongCount)} />
              </View>
            </View>
            {currentWord ? (
              <Card style={styles.workbench}>
                <View style={styles.workbenchTop}>
                  <Pill label={`${index + 1}/${queue.length || 1}`} />
                  <Pill label={speechState.status === 'recording' ? '录音中' : PRACTICE_MODE_LABELS[mode]} />
                </View>
                <Text style={styles.word}>{mode === 'meaning' ? currentWord.definition : currentWord.word}</Text>
                <Text style={styles.wordMeta}>{[currentWord.phonetic, currentWord.pos].filter(Boolean).join(' ') || 'IELTS 词条'}</Text>
                {mode !== 'meaning' ? <Text style={styles.definition}>{currentWord.definition}</Text> : null}
                {mode === 'listening' || mode === 'dictation' || mode === 'radio' ? <PrimaryButton label="播放发音" onPress={() => void playWord()} /> : null}
                {mode === 'follow' ? <PrimaryButton label={speechState.status === 'recording' ? '停止录音' : '开始跟读'} onPress={() => void toggleRecording()} /> : null}
                {mode === 'follow' ? (
                  <View style={styles.micStrip}>
                    <Mic color={theme.colors.primaryDark} size={18} />
                    <Text style={styles.micText}>音量 {Math.round(speechState.level * 100)}% · {speechState.finalText || speechState.partialText || '等待录音'}</Text>
                  </View>
                ) : null}
                {mode === 'quickmemory' ? (
                  <View style={styles.answerRow}>
                    <Pressable style={[styles.answerButton, styles.confirmButton]} onPress={() => void submit('known')}>
                      <CheckCircle2 color={theme.colors.success} size={18} />
                      <Text style={styles.answerButtonText}>认识</Text>
                    </Pressable>
                    <Pressable style={[styles.answerButton, styles.rejectButton]} onPress={() => void submit('unknown')}>
                      <XCircle color={theme.colors.danger} size={18} />
                      <Text style={styles.answerButtonText}>不认识</Text>
                    </Pressable>
                  </View>
                ) : mode === 'listening' ? (
                  <View style={styles.choiceWrap}>
                    {optionsForWord.map(option => (
                      <Pressable key={option} style={styles.choiceButton} onPress={() => void submit(option)}>
                        <Text style={styles.choiceText}>{option}</Text>
                      </Pressable>
                    ))}
                  </View>
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
                {mode !== 'follow' && currentWord.examples?.length ? (
                  <View style={styles.exampleBox}>
                    <Text style={styles.exampleTitle}>例句</Text>
                    <Text style={styles.exampleText}>{currentWord.examples[0]?.en || ''}</Text>
                    <Text style={styles.exampleHint}>{currentWord.examples[0]?.zh || ''}</Text>
                  </View>
                ) : null}
              </Card>
            ) : completed ? (
              <PracticeCompletionCard
                onChangeScope={() => setSheet('scope')}
                onRestart={() => void startPractice(mode, bookId, chapterId)}
                wordCount={queue.length}
              />
            ) : (
              <Card>
                <Heading>{mode === 'errors' ? '错词练习' : '选择章节开始练习'}</Heading>
                <Meta>{mode === 'errors' ? '当前会读取错词队列。' : '可以从顶部状态栏搜索词书或章节。'}</Meta>
                <PrimaryButton label="选择范围" onPress={() => setSheet('scope')} />
              </Card>
            )}
          </>
        )}
      </ScreenScroll>
      <Modal animationType="slide" onRequestClose={() => setSheet(null)} transparent visible={sheet !== null}>
        <View style={styles.sheetRoot}>
          <Pressable accessibilityRole="button" onPress={() => setSheet(null)} style={styles.sheetBackdrop} />
          <View style={styles.sheetPanel}>
            <StickerLayer slots={practiceSheetStickerSlots} />
            <View style={styles.sheetGrabber} />
            {sheet === 'mode' ? (
              <>
                <Text style={styles.sheetTitle}>切换练习模式</Text>
                <Text style={styles.sheetSubtitle}>沿用当前范围，切换后直接重新出题。</Text>
                <ScrollView keyboardShouldPersistTaps="handled" style={styles.sheetScroll} contentContainerStyle={styles.sheetScrollContent}>
                  {MODES.map(item => {
                    const active = item === mode
                    return (
                      <Pressable key={item} accessibilityRole="button" onPress={() => void chooseMode(item)} style={[styles.sheetRow, active ? styles.sheetRowActive : null]}>
                        <View style={styles.sheetIcon}>
                          <Text style={styles.sheetIndex}>{PRACTICE_MODE_LABELS[item].slice(0, 1)}</Text>
                        </View>
                        <View style={styles.sheetBody}>
                          <Text style={styles.sheetLabel}>{PRACTICE_MODE_LABELS[item]}</Text>
                          <Text style={styles.sheetMeta}>{MODE_HINTS[item]}</Text>
                        </View>
                        <ChevronRight color={theme.colors.textTertiary} size={18} />
                      </Pressable>
                    )
                  })}
                </ScrollView>
              </>
            ) : (
              <>
                <Text style={styles.sheetTitle}>选择练习范围</Text>
                <Text style={styles.sheetSubtitle}>搜索词书或章节，章节为空时默认按整本词书出题。</Text>
                <Field value={scopeQuery} onChangeText={setScopeQuery} placeholder="搜索当前词书或章节" />
                <ScrollView keyboardShouldPersistTaps="handled" style={styles.sheetScroll} contentContainerStyle={styles.sheetScrollContent}>
                  <Text style={styles.sheetGroup}>词书</Text>
                  {filteredBooks.map(book => {
                    const active = String(book.id) === bookId
                    return (
                      <Pressable key={String(book.id)} accessibilityRole="button" onPress={() => void selectBook(String(book.id))} style={[styles.sheetRow, active ? styles.sheetRowActive : null]}>
                        <View style={styles.sheetBody}>
                          <Text numberOfLines={1} style={styles.sheetLabel}>{book.title}</Text>
                          <Text style={styles.sheetMeta}>{book.total_words || book.word_count || 0} 词</Text>
                        </View>
                        <ChevronRight color={theme.colors.textTertiary} size={18} />
                      </Pressable>
                    )
                  })}
                  {bookId ? <Text style={styles.sheetGroup}>章节</Text> : null}
                  {bookId ? (
                    <Pressable accessibilityRole="button" onPress={() => void chooseChapter(null)} style={[styles.sheetRow, chapterId == null ? styles.sheetRowActive : null]}>
                      <View style={styles.sheetIcon}>
                        <Text style={styles.sheetIndex}>全</Text>
                      </View>
                      <View style={styles.sheetBody}>
                        <Text style={styles.sheetLabel}>整本词书</Text>
                        <Text style={styles.sheetMeta}>不限定章节，按当前词书生成队列。</Text>
                      </View>
                      <ChevronRight color={theme.colors.textTertiary} size={18} />
                    </Pressable>
                  ) : null}
                  {filteredChapters.map((chapter, idx) => (
                    <Pressable key={String(chapter.id)} accessibilityRole="button" onPress={() => void chooseChapter(chapter)} style={[styles.sheetRow, String(chapter.id) === String(chapterId) ? styles.sheetRowActive : null]}>
                      <View style={styles.sheetIcon}>
                        <Text style={styles.sheetIndex}>{String(idx + 1).padStart(2, '0')}</Text>
                      </View>
                      <View style={styles.sheetBody}>
                        <Text numberOfLines={1} style={styles.sheetLabel}>{chapter.title}</Text>
                        <Text style={styles.sheetMeta}>{chapter.word_count || chapter.group_count || 0} 项</Text>
                      </View>
                      <ChevronRight color={theme.colors.textTertiary} size={18} />
                    </Pressable>
                  ))}
                </ScrollView>
              </>
            )}
          </View>
        </View>
      </Modal>
    </>
  )
}
