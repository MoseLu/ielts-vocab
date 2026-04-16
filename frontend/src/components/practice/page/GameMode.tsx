import { useEffect, useMemo, useState } from 'react'
import PracticePronunciationButton from './PracticePronunciationButton'
import WordListActionButton from '../WordListActionButton'
import { fetchGamePracticeState, submitWordMasteryAttempt } from '../../../lib/gamePractice'
import type { GamePracticeState, GamePracticeWord, Word } from '../../../lib'
import type { WordListActionControls } from '../types'

const DIMENSION_LABELS = {
  recognition: '认词',
  meaning: '释义',
  listening: '听辨',
  speaking: '发音',
  dictation: '拼写',
} as const

type GameDimension = keyof typeof DIMENSION_LABELS

interface GameModeProps {
  bookId: string | null
  chapterId: string | null
  currentDay?: number
  vocabulary: Word[]
  playWord: (word: string) => void
  wordListActionControls?: WordListActionControls
}

function normalizeAnswer(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ')
}

function buildListeningOptions(activeWord: Word, vocabulary: Word[]): Word[] {
  const confusables = Array.isArray(activeWord.listening_confusables)
    ? activeWord.listening_confusables.map(item => ({
        word: item.word,
        phonetic: item.phonetic,
        pos: item.pos,
        definition: item.definition,
      }))
    : []
  const distractors = vocabulary.filter(item => item.word !== activeWord.word).slice(0, 6)
  const candidates = [activeWord, ...confusables, ...distractors]
  const deduped = new Map<string, Word>()
  for (const candidate of candidates) {
    const key = candidate.word.trim().toLowerCase()
    if (!key || deduped.has(key)) continue
    deduped.set(key, candidate)
  }
  return Array.from(deduped.values()).slice(0, 4)
}

function buildWordPayload(activeWord: GamePracticeState['activeWord']): Partial<Word> | null {
  if (!activeWord) return null
  return {
    word: activeWord.word,
    phonetic: activeWord.phonetic,
    pos: activeWord.pos,
    definition: activeWord.definition,
    chapter_id: activeWord.chapter_id ?? undefined,
    chapter_title: activeWord.chapter_title ?? undefined,
    listening_confusables: activeWord.listening_confusables,
    examples: activeWord.examples,
  }
}

function GameWordImagePanel({ image, word, definition }: {
  image: GamePracticeWord['image']
  word: string
  definition: string
}) {
  const isReady = image.status === 'ready' && Boolean(image.url)
  const statusLabel = {
    queued: '排队中',
    generating: '生成中',
    ready: '已就绪',
    failed: '稍后重试',
  }[image.status]
  const helperText = {
    queued: '配图生成中',
    generating: '配图生成中',
    ready: `${image.model || 'wanx-v1'} · 教育插画`,
    failed: '暂时使用占位图，稍后重试',
  }[image.status]

  return (
    <aside className="practice-game-mode__image-panel" aria-label="当前词配图">
      <div className="practice-game-mode__image-meta">
        <span className="practice-game-mode__image-eyebrow">词义配图</span>
        <span className={`practice-game-mode__image-status is-${image.status}`}>{statusLabel}</span>
      </div>

      <div className={`practice-game-mode__image-frame is-${image.status}`}>
        {isReady ? (
          <img src={image.url ?? undefined} alt={image.alt} className="practice-game-mode__image" />
        ) : (
          <div className="practice-game-mode__image-placeholder" aria-live="polite">
            <span className="practice-game-mode__image-token">{word.slice(0, 2).toUpperCase()}</span>
            <span className="practice-game-mode__image-copy">{image.status === 'failed' ? '占位图' : '生成中'}</span>
          </div>
        )}
      </div>

      <div className="practice-game-mode__image-caption">
        <strong>{definition}</strong>
        <span>{helperText}</span>
      </div>
    </aside>
  )
}

export default function GameMode({
  bookId,
  chapterId,
  currentDay,
  vocabulary,
  playWord,
  wordListActionControls,
}: GameModeProps) {
  const [state, setState] = useState<GamePracticeState | null>(null)
  const [answerInput, setAnswerInput] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)

  const activeWord = state?.activeWord ?? null
  const activeDimension = (state?.activeDimension ?? null) as GameDimension | null
  const listeningOptions = useMemo(
    () => (activeWord ? buildListeningOptions(activeWord, vocabulary) : []),
    [activeWord, vocabulary],
  )

  useEffect(() => {
    setAnswerInput('')
    setFeedback(null)
  }, [activeWord?.word, activeDimension])

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    fetchGamePracticeState({
      bookId,
      chapterId,
      day: currentDay,
    }).then(nextState => {
      if (cancelled) return
      setState(nextState)
    }).catch(loadError => {
      if (cancelled) return
      setError(loadError instanceof Error ? loadError.message : '五维闯关状态加载失败')
    }).finally(() => {
      if (!cancelled) setIsLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [bookId, chapterId, currentDay])

  const submitAttempt = async (passed: boolean) => {
    if (!activeWord || !activeDimension) return
    setIsSubmitting(true)
    setError(null)
    setFeedback(null)
    try {
      const response = await submitWordMasteryAttempt({
        bookId,
        chapterId,
        day: currentDay,
        word: activeWord.word,
        dimension: activeDimension,
        passed,
        sourceMode: activeDimension === 'speaking' ? 'speaking' : 'game',
        wordPayload: buildWordPayload(activeWord),
      })
      setState(response.game_state)
      setFeedback(passed ? '本轮通过，继续下一关。' : '这关先记入补考队列，继续回流练。')
      setAnswerInput('')
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : '五维闯关提交失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return <section className="practice-game-mode practice-game-mode--loading">正在加载五维闯关...</section>
  }

  if (error && !state) {
    return <section className="practice-game-mode practice-game-mode--error">{error}</section>
  }

  if (!activeWord || !activeDimension || !state) {
    return <section className="practice-game-mode practice-game-mode--done">当前范围内的词都已通关。</section>
  }

  const activeWordForActions: Word = {
    word: activeWord.word,
    phonetic: activeWord.phonetic,
    pos: activeWord.pos,
    definition: activeWord.definition,
    chapter_id: activeWord.chapter_id ?? undefined,
    chapter_title: activeWord.chapter_title ?? undefined,
    listening_confusables: activeWord.listening_confusables,
    examples: activeWord.examples,
  }

  return (
    <section className="practice-game-mode">
      <div className="practice-game-mode__summary">
        <div>
          <div className="practice-game-mode__eyebrow">五维闯关</div>
          <h2>{activeWord.word}</h2>
          <p>{activeWord.phonetic || activeWord.pos ? `${activeWord.phonetic || ''} ${activeWord.pos || ''}`.trim() : '当前词'} </p>
        </div>
        <div className="practice-game-mode__meta">
          <span>{DIMENSION_LABELS[activeDimension]}关</span>
          <span>{state.summary.passedWords}/{state.summary.totalWords} 词通关</span>
          <span>{state.masteryProgress.completed}/{state.masteryProgress.total} 轮进度</span>
        </div>
      </div>

      <div className="practice-game-mode__stage-card">
        <div className="practice-game-mode__stage-layout">
          <GameWordImagePanel
            image={activeWord.image}
            word={activeWord.word}
            definition={activeWord.definition}
          />

          <div className="practice-game-mode__stage-content">
            <div className="practice-game-mode__stage-header">
              <div>
                <div className="practice-game-mode__stage-label">{DIMENSION_LABELS[activeDimension]}</div>
                <div className="practice-game-mode__stage-status">当前状态：{activeWord.overall_status}</div>
              </div>
              <div className="practice-game-mode__actions">
                {wordListActionControls ? (
                  <>
                    <WordListActionButton
                      kind="familiar"
                      active={wordListActionControls.isFamiliar(activeWord.word)}
                      pending={wordListActionControls.isFamiliarPending(activeWord.word)}
                      onClick={() => wordListActionControls.onFamiliarToggle(activeWordForActions)}
                    />
                    <WordListActionButton
                      kind="favorite"
                      active={wordListActionControls.isFavorite(activeWord.word)}
                      pending={wordListActionControls.isFavoritePending(activeWord.word)}
                      onClick={() => wordListActionControls.onFavoriteToggle(activeWordForActions)}
                    />
                  </>
                ) : null}
              </div>
            </div>

            <div className="practice-game-mode__dimension-row">
              {(Object.entries(DIMENSION_LABELS) as [GameDimension, string][]).map(([dimension, label]) => {
                const dimensionState = activeWord.dimension_states[dimension]
                return (
                  <div
                    key={dimension}
                    className={`practice-game-mode__dimension-chip${dimension === activeDimension ? ' is-active' : ''}${dimensionState?.pass_streak >= 4 ? ' is-passed' : ''}`}
                  >
                    <span>{label}</span>
                    <strong>{dimensionState?.pass_streak ?? 0}/4</strong>
                  </div>
                )
              })}
            </div>

            {activeDimension === 'recognition' ? (
              <div className="practice-game-mode__task">
                <div className="practice-game-mode__prompt">看到这个词时，你能立刻认出它吗？</div>
                <div className="practice-game-mode__recognition">{activeWord.word}</div>
                <div className="practice-game-mode__button-row">
                  <button type="button" onClick={() => void submitAttempt(true)} disabled={isSubmitting}>认识了</button>
                  <button type="button" className="is-secondary" onClick={() => void submitAttempt(false)} disabled={isSubmitting}>还不熟</button>
                </div>
              </div>
            ) : null}

            {activeDimension === 'meaning' ? (
              <div className="practice-game-mode__task">
                <div className="practice-game-mode__prompt">根据中文释义回想英文单词</div>
                <div className="practice-game-mode__definition">{activeWord.definition}</div>
                <div className="practice-game-mode__input-row">
                  <input
                    value={answerInput}
                    onChange={event => setAnswerInput(event.target.value)}
                    placeholder="输入英文单词"
                    disabled={isSubmitting}
                  />
                  <button
                    type="button"
                    onClick={() => void submitAttempt(normalizeAnswer(answerInput) === normalizeAnswer(activeWord.word))}
                    disabled={isSubmitting || !answerInput.trim()}
                  >
                    提交
                  </button>
                </div>
              </div>
            ) : null}

            {activeDimension === 'listening' ? (
              <div className="practice-game-mode__task">
                <div className="practice-game-mode__prompt">先听，再选对应释义</div>
                <div className="practice-game-mode__button-row">
                  <button type="button" onClick={() => playWord(activeWord.word)}>播放单词</button>
                </div>
                <div className="practice-game-mode__option-grid">
                  {listeningOptions.map(option => (
                    <button
                      key={`${option.word}-${option.definition}`}
                      type="button"
                      className="practice-game-mode__option"
                      onClick={() => void submitAttempt(normalizeAnswer(option.word) === normalizeAnswer(activeWord.word))}
                      disabled={isSubmitting}
                    >
                      <span>{option.definition}</span>
                      <small>{option.pos}</small>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {activeDimension === 'speaking' ? (
              <div className="practice-game-mode__task">
                <div className="practice-game-mode__prompt">只检查当前单词发音是否匹配</div>
                <PracticePronunciationButton
                  bookId={bookId}
                  chapterId={chapterId}
                  targetWord={activeWord.word}
                  targetPhonetic={activeWord.phonetic}
                  onEvaluated={() => {
                    void fetchGamePracticeState({
                      bookId,
                      chapterId,
                      day: currentDay,
                    }).then(setState).catch(() => {})
                  }}
                />
              </div>
            ) : null}

            {activeDimension === 'dictation' ? (
              <div className="practice-game-mode__task">
                <div className="practice-game-mode__prompt">听音后完整拼写这个单词</div>
                <div className="practice-game-mode__button-row">
                  <button type="button" onClick={() => playWord(activeWord.word)}>播放单词</button>
                </div>
                <div className="practice-game-mode__input-row">
                  <input
                    value={answerInput}
                    onChange={event => setAnswerInput(event.target.value)}
                    placeholder="输入拼写"
                    disabled={isSubmitting}
                  />
                  <button
                    type="button"
                    onClick={() => void submitAttempt(normalizeAnswer(answerInput) === normalizeAnswer(activeWord.word))}
                    disabled={isSubmitting || !answerInput.trim()}
                  >
                    提交
                  </button>
                </div>
              </div>
            ) : null}

            {feedback ? <div className="practice-game-mode__feedback">{feedback}</div> : null}
            {error ? <div className="practice-game-mode__error">{error}</div> : null}
          </div>
        </div>
      </div>

      <div className="practice-game-mode__queue">
        <div className="practice-game-mode__queue-title">待复习队列</div>
        <div className="practice-game-mode__queue-list">
          {state.reviewQueue.length > 0 ? state.reviewQueue.map(item => (
            <div key={`${item.word}-${item.current_round}`} className="practice-game-mode__queue-item">
              <strong>{item.word}</strong>
              <span>{item.pending_dimensions.map(dimension => DIMENSION_LABELS[dimension as GameDimension] ?? dimension).join(' / ')}</span>
            </div>
          )) : (
            <div className="practice-game-mode__queue-empty">当前没有待复习词。</div>
          )}
        </div>
      </div>
    </section>
  )
}
