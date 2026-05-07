import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import {
  BrainCircuit,
  BookOpen,
  CheckCircle2,
  Headphones,
  Keyboard,
  Mic,
  Sparkles,
  TriangleAlert,
  Volume2,
  XCircle,
  type LucideIcon,
} from 'lucide-react-native'
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
import { theme } from '../theme'

const MODES: PracticeMode[] = ['smart', 'quickmemory', 'listening', 'meaning', 'dictation', 'follow', 'radio', 'errors']

type ModeMeta = {
  Icon: LucideIcon
  hint: string
}

const MODE_META: Record<PracticeMode, ModeMeta> = {
  smart: { Icon: BrainCircuit, hint: '先看系统推荐，再决定怎么练' },
  quickmemory: { Icon: Sparkles, hint: '快速认词，决定要不要进复习链' },
  listening: { Icon: Headphones, hint: '听音辨义，训练反应速度' },
  meaning: { Icon: BookOpen, hint: '看中文，主动拼出英文' },
  dictation: { Icon: Keyboard, hint: '听音写词，抓住拼写细节' },
  follow: { Icon: Mic, hint: '跟读发音，记录语音表现' },
  radio: { Icon: Volume2, hint: '连续播放，适合碎片复习' },
  errors: { Icon: TriangleAlert, hint: '直接拉起错词队列' },
}

function scoreLabel(label: string, value: number) {
  return `${label} ${value}`
}

function choiceTone(selected: boolean) {
  return selected ? 'primary' : 'neutral'
}

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
  const completed = queue.length > 0 && index >= queue.length
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
      const words = nextMode === 'errors' ? await loadWrongWords() : await loadChapterWords(bookId, nextChapterId)
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

  const progress = queue.length ? Math.min(100, (index / queue.length) * 100) : 0

  return (
    <ScreenScroll hideHeader title="练习" subtitle="基础模式原生闭环：答题、进度、错词、复习和跟读录音。">
      <StatusText error={error || speechState.error} loading={loading} />
      <Card style={styles.hero}>
        <View style={styles.heroTop}>
          <View style={styles.heroCopy}>
            <Meta>练习工作台</Meta>
            <Heading>{PRACTICE_MODE_LABELS[mode]}</Heading>
            <Text style={styles.heroHint}>{MODE_META[mode].hint}</Text>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${progress}%` }]} />
            </View>
          </View>
          <View style={styles.scoreBox}>
            <Text style={styles.scoreValue}>{queue.length || '0'}</Text>
            <Text style={styles.scoreLabel}>词</Text>
          </View>
        </View>
        <Row>
          <Pill label={scoreLabel('对', correctCount)} />
          <Pill label={scoreLabel('错', wrongCount)} />
          <Pill label={bookId ? '已选词书' : '未选词书'} />
        </Row>
      </Card>
      <Card>
        <View style={styles.sectionHead}>
          <Heading>模式</Heading>
          <Sparkles color={theme.colors.muted} size={20} />
        </View>
        <View style={styles.modeGrid}>
          {MODES.map(item => {
            const meta = MODE_META[item]
            return (
              <Pressable
                key={item}
                accessibilityRole="button"
                style={[styles.modeCard, item === mode ? styles.modeCardActive : null]}
                onPress={() => {
                  setMode(item)
                  void startPractice(item)
                }}
              >
                <View style={[styles.modeIcon, item === mode ? styles.modeIconActive : null]}>
                  <meta.Icon color={item === mode ? theme.colors.primaryDark : theme.colors.text} size={20} strokeWidth={2.4} />
                </View>
                <Text style={styles.modeLabel}>{PRACTICE_MODE_LABELS[item]}</Text>
                <Text style={styles.modeHint}>{meta.hint}</Text>
              </Pressable>
            )
          })}
        </View>
      </Card>
      <Card>
        <View style={styles.sectionHead}>
          <Heading>范围</Heading>
          <BookOpen color={theme.colors.muted} size={20} />
        </View>
        <View style={styles.chipWrap}>
          {books.slice(0, 6).map(book => (
            <PrimaryButton key={String(book.id)} label={book.title} tone={choiceTone(String(book.id) === bookId)} onPress={() => void selectBook(String(book.id))} />
          ))}
        </View>
        <View style={styles.chipWrap}>
          {chapters.slice(0, 12).map(chapter => (
            <PrimaryButton
              key={String(chapter.id)}
              label={chapter.title}
              tone={choiceTone(String(chapter.id) === String(chapterId))}
              onPress={() => {
                setChapterId(chapter.id)
                void startPractice(mode, chapter.id)
              }}
            />
          ))}
        </View>
        <PrimaryButton label="开始 / 重载练习" disabled={!bookId && mode !== 'errors'} onPress={() => void startPractice()} />
      </Card>
      {currentWord ? (
        <Card style={styles.workbench}>
          <View style={styles.workbenchTop}>
            <Pill label={`${index + 1}/${queue.length || 1}`} />
            <Pill label={speechState.status === 'recording' ? '录音中' : '待答题'} />
          </View>
          <Text style={styles.word}>{mode === 'meaning' ? currentWord.definition : currentWord.word}</Text>
          <Text style={styles.wordMeta}>{[currentWord.phonetic, currentWord.pos].filter(Boolean).join(' ') || 'IELTS 词条'}</Text>
          {mode !== 'meaning' ? <Text style={styles.definition}>{currentWord.definition}</Text> : null}
          {mode === 'listening' || mode === 'dictation' || mode === 'radio' ? (
            <PrimaryButton label="播放发音" onPress={() => void playWord()} />
          ) : null}
          {mode === 'follow' ? (
            <PrimaryButton
              label={speechState.status === 'recording' ? '停止录音' : '开始跟读'}
              onPress={() => void toggleRecording()}
            />
          ) : null}
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
        <Card>
          <Heading>本轮完成</Heading>
          <Meta>{queue.length} 个词已过一遍，下一轮可换模式继续压强。</Meta>
          <Row>
            <Pill label={`对 ${correctCount}`} />
            <Pill label={`错 ${wrongCount}`} />
            <Pill label={`音量 ${Math.round(speechState.level * 100)}%`} />
          </Row>
          <PrimaryButton label="再来一轮" onPress={() => void startPractice(mode, chapterId)} />
        </Card>
      ) : (
        <Card>
          <Heading>先选择词书和章节</Heading>
          <Meta>{mode === 'errors' ? '错词强化会直接读取错词队列。' : '其他模式需要先选一个章节，工作台才会开始出题。'}</Meta>
        </Card>
      )}
    </ScreenScroll>
  )
}

const styles = StyleSheet.create({
  answerButton: {
    alignItems: 'center',
    borderRadius: theme.radius.control,
    flex: 1,
    flexDirection: 'row',
    gap: theme.spacing.xs,
    justifyContent: 'center',
    minHeight: 48,
  },
  answerButtonText: {
    color: theme.colors.text,
    fontWeight: '900',
  },
  answerRow: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginTop: theme.spacing.sm,
  },
  chipWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
  },
  choiceButton: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.control,
    flexBasis: '48%',
    flexGrow: 1,
    justifyContent: 'center',
    minHeight: 54,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.sm,
  },
  choiceText: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    fontWeight: '800',
    textAlign: 'center',
  },
  choiceWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
    marginTop: theme.spacing.sm,
  },
  confirmButton: {
    backgroundColor: theme.colors.emeraldSoft,
  },
  definition: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 23,
    marginTop: theme.spacing.sm,
  },
  exampleBox: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.card,
    marginTop: theme.spacing.md,
    padding: theme.spacing.md,
  },
  exampleHint: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    lineHeight: 18,
    marginTop: theme.spacing.xs,
  },
  exampleText: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    lineHeight: 20,
    marginTop: theme.spacing.xs,
  },
  exampleTitle: {
    color: theme.colors.primaryDark,
    fontSize: theme.typography.caption,
    fontWeight: '900',
  },
  hero: {
    backgroundColor: theme.colors.surface,
  },
  heroCopy: {
    flex: 1,
  },
  heroHint: {
    color: theme.colors.muted,
    fontSize: theme.typography.label,
    lineHeight: 20,
    marginTop: theme.spacing.xs,
  },
  heroTop: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.md,
    justifyContent: 'space-between',
  },
  micStrip: {
    alignItems: 'center',
    backgroundColor: theme.colors.infoSoft,
    borderRadius: theme.radius.control,
    flexDirection: 'row',
    gap: theme.spacing.xs,
    marginTop: theme.spacing.sm,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
  },
  micText: {
    color: theme.colors.info,
    flex: 1,
    fontSize: theme.typography.caption,
    fontWeight: '700',
  },
  modeCard: {
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    flexBasis: '48%',
    flexGrow: 1,
    minHeight: 124,
    padding: theme.spacing.md,
  },
  modeCardActive: {
    backgroundColor: theme.colors.primarySoft,
    borderColor: theme.colors.primary,
  },
  modeGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
  },
  modeHint: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    lineHeight: 18,
    marginTop: theme.spacing.xs,
  },
  modeIcon: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.pill,
    height: 34,
    justifyContent: 'center',
    width: 34,
  },
  modeIconActive: {
    backgroundColor: theme.colors.surfaceElevated,
  },
  modeLabel: {
    color: theme.colors.text,
    fontSize: theme.typography.label,
    fontWeight: '900',
    marginTop: theme.spacing.sm,
  },
  progressFill: {
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.pill,
    height: '100%',
  },
  progressTrack: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radius.pill,
    height: 10,
    marginTop: theme.spacing.md,
    overflow: 'hidden',
  },
  rejectButton: {
    backgroundColor: theme.colors.dangerSoft,
  },
  scoreBox: {
    alignItems: 'center',
    backgroundColor: theme.colors.primarySoft,
    borderRadius: theme.radius.card,
    minWidth: 82,
    paddingVertical: theme.spacing.md,
  },
  scoreLabel: {
    color: theme.colors.primaryDark,
    fontSize: theme.typography.caption,
    fontWeight: '800',
  },
  scoreValue: {
    color: theme.colors.primaryDark,
    fontSize: 24,
    fontWeight: '900',
  },
  sectionHead: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm,
  },
  word: {
    color: theme.colors.text,
    fontSize: 26,
    fontWeight: '900',
  },
  wordMeta: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '700',
    marginTop: theme.spacing.xs,
  },
  workbench: {
    backgroundColor: theme.colors.surfaceElevated,
  },
  workbenchTop: {
    flexDirection: 'row',
    gap: theme.spacing.xs,
  },
})
