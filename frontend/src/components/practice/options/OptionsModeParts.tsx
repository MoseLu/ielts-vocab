import { useEffect, useRef, type CSSProperties } from 'react'
import smartDictationIcon from '../../../assets/icons/smart-dictation.svg'
import smartListeningIcon from '../../../assets/icons/smart-listening.svg'
import smartMeaningIcon from '../../../assets/icons/smart-meaning.svg'
import ExampleAudioIcon from '../../ui/ExampleAudioIcon'
import WordMeaningGroups from '../../ui/WordMeaningGroups'
import { WRONG_WORD_DIMENSION_LABELS } from '../../../features/vocabulary/wrongWordsStore'
import type {
  LastState,
  OptionItem,
  SmartDimension,
  SpellingSubmitSource,
  WordPlaybackHandler,
} from '../types'
import { buildBlankSentence } from '../exampleSentence'
import PracticeStageGuide from '../PracticeStageGuide.tsx'
import { buildChoiceStageGuide } from '../practiceStageGuide'

interface PrevWordBlockProps {
  previousWord: LastState['prevWord']
  lastState: LastState | null
  onGoBack: () => void
  className?: string
}

export function PrevWordBlock({ previousWord, lastState, onGoBack, className }: PrevWordBlockProps) {
  if (!previousWord) return null
  const rootClassName = className ? `prev-word-inline ${className}` : 'prev-word-inline'
  return (
    <div className={rootClassName}>
      <button className="prev-back-btn" onClick={onGoBack} disabled={!lastState} title="返回上一个词">←</button>
      <div className="prev-word-info">
        <div className="prev-word-text">{previousWord.word}</div>
        <div className="prev-word-phonetic">{previousWord.phonetic}</div>
        <WordMeaningGroups
          className="prev-word-def"
          definition={previousWord.definition}
          pos={previousWord.pos}
          size="sm"
        />
      </div>
    </div>
  )
}

interface BottomBarProps {
  progressValue: number
  total: number
  queueIndex: number
}

export function BottomBar({ progressValue, total, queueIndex }: BottomBarProps) {
  return (
    <div className="practice-bottom-bar">
      <div className="bottom-progress-track">
        <div
          className="bottom-progress-fill"
          style={{ '--progress-percent': `${progressValue * 100}%` } as CSSProperties}
        >
          <div className="bottom-progress-dot"></div>
        </div>
      </div>
      <span className="bottom-progress-count">{queueIndex + 1}/{total}</span>
    </div>
  )
}

interface OptionsGridProps {
  options: OptionItem[]
  optionsLoading?: boolean
  selectedAnswer: number | null
  wrongSelections: number[]
  showResult: boolean
  correctIndex: number
  onOptionSelect: (idx: number) => void
}

function simplifyPosLabel(pos: string): string {
  const normalized = pos.trim().toLowerCase().replace(/\.+$/g, '')
  if (!normalized) return ''
  if (normalized === 'adj') return 'adj'
  if (normalized === 'adv') return 'adv'
  if (normalized.startsWith('v')) return 'v'
  if (normalized.startsWith('n')) return 'n'
  if (normalized.startsWith('prep')) return 'prep'
  if (normalized.startsWith('pron')) return 'pron'
  if (normalized.startsWith('conj')) return 'conj'
  if (normalized.startsWith('num')) return 'num'
  if (normalized.startsWith('art')) return 'art'
  if (normalized.startsWith('int')) return 'int'
  return normalized
}

export function OptionsGrid({
  options,
  optionsLoading = false,
  selectedAnswer,
  wrongSelections,
  showResult,
  correctIndex,
  onOptionSelect,
}: OptionsGridProps) {
  if (optionsLoading) {
    return <div className="options-loading">正在生成选项...</div>
  }

  const wrongSet = new Set(wrongSelections)

  return (
    <div className="options-grid">
      {options.map((option, idx) => {
        let cls = 'option-btn'
        const isWrong = wrongSet.has(idx)
        const isCorrect = showResult && idx === correctIndex
        const shouldRevealWord = Boolean(option.word) && (isWrong || isCorrect)

        if (isCorrect) cls += ' correct'
        else if (isWrong) cls += ' wrong'
        else if (!showResult && selectedAnswer === idx) cls += ' selected'

        return (
          <button key={idx} className={cls} onClick={() => onOptionSelect(idx)} disabled={showResult}>
            <div className="option-header">
              <span className="option-pos-group">
                <span className="option-pos">{simplifyPosLabel(option.pos)}</span>
                {shouldRevealWord && (
                  <span className="option-word-reveal">{option.word}</span>
                )}
              </span>
              <span className="option-key">快捷键: {idx + 1}</span>
            </div>
            {option.display_mode === 'word' && option.word ? (
              <div className="option-text-wrap">
                <span className="option-text option-text--word">{option.word}</span>
                {option.phonetic && <span className="option-subtext">{option.phonetic}</span>}
              </div>
            ) : (
              <span className="option-text">{option.definition}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}

interface WordDisplayProps {
  currentWord: { word: string; phonetic: string; pos: string; definition: string }
  displayMode: 'audio' | 'definition'
}

export function WordDisplay({
  currentWord,
  displayMode,
}: WordDisplayProps) {
  return (
    <div className="word-display-area">
      {displayMode === 'definition' && (
        <div className="meaning-prompt-card">
          <div className="meaning-prompt-label">看中文释义，拼英文单词</div>
          <WordMeaningGroups
            className="meaning-prompt-definition"
            definition={currentWord.definition}
            pos={currentWord.pos}
            size="lg"
          />
        </div>
      )}
    </div>
  )
}

interface ListeningExamplePromptProps {
  sentence: string
  targetWord: string
  onPlayAudio?: () => void
}

export function ListeningExamplePrompt({
  sentence,
  targetWord,
  onPlayAudio,
}: ListeningExamplePromptProps) {
  if (!sentence.trim()) return null
  const sentenceContent = buildBlankSentence(sentence, targetWord)

  return (
    <div className="listening-example-prompt">
      {onPlayAudio ? (
        <button
          type="button"
          className="listening-example-audio-btn"
          aria-label="播放例句"
          title="播放例句（点击例句或按 Alt）"
          onClick={onPlayAudio}
        >
          <ExampleAudioIcon className="example-audio-icon" />
        </button>
      ) : null}
      {onPlayAudio ? (
        <button
          type="button"
          className="listening-example-sentence listening-example-sentence--interactive"
          title="点击例句播放"
          onClick={onPlayAudio}
        >
          {sentenceContent}
        </button>
      ) : (
        <div className="listening-example-sentence">{sentenceContent}</div>
      )}
    </div>
  )
}

const SMART_DIM_CONFIG: Record<SmartDimension, { label: string; iconSrc: string; cls: string }> = {
  listening: { label: WRONG_WORD_DIMENSION_LABELS.listening, iconSrc: smartListeningIcon, cls: 'smart-badge-listening' },
  meaning:   { label: WRONG_WORD_DIMENSION_LABELS.meaning, iconSrc: smartMeaningIcon, cls: 'smart-badge-meaning' },
  dictation: { label: WRONG_WORD_DIMENSION_LABELS.dictation, iconSrc: smartDictationIcon, cls: 'smart-badge-dictation' },
}

interface SmartDimBadgeProps {
  dimension: SmartDimension
}

export function SmartDimBadge({ dimension }: SmartDimBadgeProps) {
  const cfg = SMART_DIM_CONFIG[dimension]
  return (
    <div className={`smart-dim-badge ${cfg.cls}`}>
      <span className="smart-badge-icon">
        <img src={cfg.iconSrc} alt="" aria-hidden="true" />
      </span>
      <span className="smart-badge-label">{cfg.label}</span>
    </div>
  )
}

interface SmartDictationProps {
  currentWord: { word: string; definition: string; pos: string; phonetic: string }
  spellingInput: string
  spellingResult: 'correct' | 'wrong' | null
  speechConnected: boolean
  speechRecording: boolean
  onSpellingInputChange: (v: string) => void
  onSpellingSubmit: (source?: SpellingSubmitSource) => void
  onStartRecording: () => void
  onStopRecording: () => void
  onPlayWord: WordPlaybackHandler
}

export function SmartDictation({
  currentWord,
  spellingInput,
  spellingResult,
  speechConnected,
  speechRecording,
  onSpellingInputChange,
  onSpellingSubmit,
  onStartRecording,
  onStopRecording,
  onPlayWord,
}: SmartDictationProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (spellingResult === null) {
      setTimeout(() => inputRef.current?.focus(), 400)
    }
  }, [spellingResult])

  useEffect(() => {
    if (spellingResult !== 'wrong') return
    const timerId = window.setTimeout(() => {
      onPlayWord(currentWord.word)
    }, 320)
    return () => window.clearTimeout(timerId)
  }, [spellingResult, onPlayWord, currentWord.word])

  return (
    <div className="smart-dictation-area">
      <div className="dictation-letter-hint">
        {currentWord.word.split('').map((ch, i) =>
          ch === ' '
            ? <span key={i} className="letter-hint-space" />
            : <span key={i} className="letter-hint-blank">_</span>
        )}
      </div>

      {spellingResult === 'correct' && (
        <div className="spelling-answer correct-answer">正确！</div>
      )}

      <div className={`spelling-input-wrapper ${spellingResult || ''}`}>
        <input
          ref={inputRef}
          type="text"
          className="spelling-input"
          value={spellingInput}
          onChange={e => onSpellingInputChange(e.target.value)}
          onKeyDown={e => {
            if (e.key !== 'Enter') return
            e.preventDefault()
            if (e.repeat) return
            onSpellingSubmit('enter')
          }}
          placeholder="输入你听到的单词..."
          disabled={!!spellingResult}
          autoComplete="off"
          spellCheck={false}
        />
        {!spellingResult && (
          <button
            className={`mic-btn ${speechRecording ? 'recording' : ''} ${!speechConnected ? 'disconnected' : ''}`}
            onClick={speechRecording ? onStopRecording : onStartRecording}
            disabled={!speechConnected}
            title={speechRecording ? '停止录音' : speechConnected ? '语音输入' : '语音服务未连接'}
          >
            {!speechConnected ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="2" width="6" height="11" rx="3"></rect>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
                <line x1="4" y1="4" x2="20" y2="20" stroke="red" strokeWidth="2"></line>
              </svg>
            ) : speechRecording ? (
              <svg viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="2"></rect>
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="2" width="6" height="11" rx="3"></rect>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
              </svg>
            )}
          </button>
        )}
        {!spellingResult && (
          <button className="spelling-submit-btn" onClick={() => onSpellingSubmit('button')} title="确认">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </button>
        )}
      </div>
    </div>
  )
}

interface MeaningRecallInputProps {
  currentWord: { word: string; definition: string; pos: string; phonetic: string }
  spellingInput: string
  spellingResult: 'correct' | 'wrong' | null
  speechConnected: boolean
  speechRecording: boolean
  onSpellingInputChange: (v: string) => void
  onSpellingSubmit: (source?: SpellingSubmitSource) => void
  onStartRecording: () => void
  onStopRecording: () => void
  onSkip: () => void
}

export function MeaningRecallInput({
  currentWord,
  spellingInput,
  spellingResult,
  speechConnected,
  speechRecording,
  onSpellingInputChange,
  onSpellingSubmit,
  onStartRecording,
  onStopRecording,
  onSkip,
}: MeaningRecallInputProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (spellingResult === null) {
      window.setTimeout(() => inputRef.current?.focus(), 250)
    }
  }, [spellingResult, currentWord.word])

  return (
    <div className="meaning-recall-area">
      <p className="meaning-recall-hint">不看选项，按中文释义拼出英文单词。</p>

      {spellingResult === 'correct' && (
        <div className="spelling-answer correct-answer">正确！</div>
      )}

      {spellingResult === 'wrong' && (
        <div className="meaning-recall-answer">
          <div className="spelling-answer">正确答案：{currentWord.word}</div>
          {currentWord.phonetic && (
            <div className="meaning-recall-phonetic">{currentWord.phonetic}</div>
          )}
        </div>
      )}

      <div className={`spelling-input-wrapper ${spellingResult || ''}`}>
        <input
          ref={inputRef}
          type="text"
          className="spelling-input"
          value={spellingInput}
          onChange={e => onSpellingInputChange(e.target.value)}
          onKeyDown={e => {
            if (e.key !== 'Enter') return
            e.preventDefault()
            if (e.repeat) return
            onSpellingSubmit('enter')
          }}
          placeholder="输入英文单词..."
          disabled={!!spellingResult}
          autoComplete="off"
          spellCheck={false}
        />
        {!spellingResult && (
          <button
            className={`mic-btn ${speechRecording ? 'recording' : ''} ${!speechConnected ? 'disconnected' : ''}`}
            onClick={speechRecording ? onStopRecording : onStartRecording}
            disabled={!speechConnected}
            title={speechRecording ? '停止录音' : speechConnected ? '语音输入' : '语音服务未连接'}
          >
            {!speechConnected ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="2" width="6" height="11" rx="3"></rect>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
                <line x1="4" y1="4" x2="20" y2="20" stroke="red" strokeWidth="2"></line>
              </svg>
            ) : speechRecording ? (
              <svg viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="2"></rect>
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="2" width="6" height="11" rx="3"></rect>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
              </svg>
            )}
          </button>
        )}
        {!spellingResult && (
          <button className="spelling-submit-btn" onClick={() => onSpellingSubmit('button')} title="确认">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </button>
        )}
      </div>

      {!spellingResult && (
        <div className="meaning-recall-footer">
          <button className="skip-btn" onClick={onSkip}>不知道</button>
        </div>
      )}
    </div>
  )
}

interface ChoiceStageGuideProps {
  mode: 'smart' | 'listening' | 'meaning' | 'radio'
  smartDimension: SmartDimension
  queueIndex: number
  total: number
  errorMode: boolean
  reviewMode: boolean
  answered: boolean
}

export function ChoiceStageGuide(props: ChoiceStageGuideProps) {
  return <PracticeStageGuide guide={buildChoiceStageGuide(props)} />
}
