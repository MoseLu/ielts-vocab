import type { CSSProperties, ReactNode } from 'react'
import type { QuickMemoryModeVariant } from '../../../features/practice/quickMemorySession'
import type { Word } from '../types'
import { QuickMemoryCountdownRing } from './QuickMemoryCountdownRing'

interface QuickMemoryCardProps {
  modeVariant: QuickMemoryModeVariant
  phase: 'question' | 'reveal'
  countdown: number
  totalSeconds: number
  progressPercent: number
  currentPosition: number
  totalCount: number
  currentWord: Word
  choice: 'known' | 'unknown' | null
  wasFuzzy: boolean
  questionReady: boolean
  knownChoiceAvailable: boolean
  favoriteSlot?: ReactNode
  replayWordHint: string
  canGoPrev: boolean
  isLast: boolean
  onReplay: () => void
  onKnown: () => void
  onFamiliar: () => void
  onUnknown: () => void
  onPrev: () => void
  onNext: () => void
}

function CrossIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M9 18l6-6-6-6" />
    </svg>
  )
}

function ChevronLeftIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M15 18l-6-6 6-6" />
    </svg>
  )
}

function SpeakerIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14" />
    </svg>
  )
}

export function QuickMemoryCard({
  modeVariant,
  phase,
  countdown,
  totalSeconds,
  progressPercent,
  currentPosition,
  totalCount,
  currentWord,
  choice,
  wasFuzzy,
  questionReady,
  knownChoiceAvailable,
  favoriteSlot,
  replayWordHint,
  canGoPrev,
  isLast,
  onReplay,
  onKnown,
  onFamiliar,
  onUnknown,
  onPrev,
  onNext,
}: QuickMemoryCardProps) {
  const isTestMode = modeVariant === 'test'
  const resultLabel = choice === 'known'
    ? '✓ 认识'
    : wasFuzzy && isTestMode
      ? '△ 不熟悉'
      : '✗ 不认识'
  const keyHints = (
    <div className="qm-key-hints">
      {canGoPrev && <span className="qm-key-hint"><kbd>←</kbd> 上一个</span>}
      {phase === 'question' && (!isTestMode || (questionReady && knownChoiceAvailable)) && (
        <span className="qm-key-hint"><kbd>→</kbd> 认识</span>
      )}
      {phase === 'reveal' && <span className="qm-key-hint"><kbd>→</kbd> 下一个</span>}
      <span className="qm-key-hint">点右上角喇叭或 <kbd>Tab</kbd> 重播发音</span>
    </div>
  )

  return (
    <div className="qm-root">
      <div className="qm-stage">
        <div className="qm-progress-track">
          <div className="qm-progress-fill" style={{ '--progress-percent': `${progressPercent}%` } as CSSProperties} />
        </div>
        <div className="qm-progress-label">{currentPosition} / {totalCount}</div>
        <div className={`qm-card ${phase === 'reveal' ? 'qm-card--reveal' : ''}${isTestMode ? ' qm-card--test' : ''}`}>
          <div className="qm-card-toolbar">
            {favoriteSlot ? <div className="qm-card-toolbar__side">{favoriteSlot}</div> : null}
            <div className="qm-card-toolbar__audio-group">
              <button type="button" className="qm-card-toolbar__icon-btn" onClick={onReplay} aria-label="重播发音" title={replayWordHint}>
                <SpeakerIcon />
              </button>
            </div>
          </div>
          {phase === 'question' && isTestMode && (
            <>
              {questionReady
                ? countdown > 0 && <div className="qm-countdown-ring"><QuickMemoryCountdownRing seconds={countdown} total={totalSeconds} /></div>
                : <div className="qm-audio-prompt"><SpeakerIcon /></div>}
              <p className="qm-hint">听完发音后判断熟悉度</p>
              {questionReady && (
                <>
                  <div className="qm-choice-row">
                    {knownChoiceAvailable && (
                      <button className="qm-btn qm-btn--known" onClick={onKnown}>
                        <CheckIcon />
                        认识
                      </button>
                    )}
                    <button className="qm-btn qm-btn--familiar" onClick={onFamiliar}>
                      <CheckIcon />
                      不熟悉
                    </button>
                    <button className="qm-btn qm-btn--unknown" onClick={onUnknown}>
                      <CrossIcon />
                      不认识
                    </button>
                  </div>
                  {keyHints}
                </>
              )}
            </>
          )}
          {phase === 'question' && !isTestMode && (
            <>
              {countdown > 0 && <div className="qm-countdown-ring"><QuickMemoryCountdownRing seconds={countdown} total={totalSeconds} /></div>}
              <div className="qm-word">{currentWord.word}</div>
              <p className="qm-hint">你认识这个单词吗？</p>
              <div className="qm-choice-row">
                <button className="qm-btn qm-btn--unknown" onClick={onUnknown}>
                  <CrossIcon />
                  不认识
                </button>
                <button className="qm-btn qm-btn--known" onClick={onKnown}>
                  <CheckIcon />
                  认识
                </button>
              </div>
              {keyHints}
            </>
          )}
          {phase === 'reveal' && (
            <>
              <div className={`qm-result-badge ${choice === 'known' ? 'qm-badge--known' : 'qm-badge--unknown'}${wasFuzzy ? ' qm-badge--fuzzy' : ''}`}>
                {resultLabel}
                {wasFuzzy && <span className="qm-badge-fuzzy-tag">模糊</span>}
              </div>
              <div className="qm-word">{currentWord.word}</div>
              {currentWord.phonetic && <div className="qm-phonetic">{currentWord.phonetic}</div>}
              <div className="qm-definition-line">
                {currentWord.pos && <span className="qm-pos">{currentWord.pos.toLowerCase()}</span>}
                <span className="qm-definition">{currentWord.definition}</span>
              </div>
              <div className="qm-nav-row">
                {canGoPrev && <button className="qm-btn-prev" onClick={onPrev}><ChevronLeftIcon />上一个</button>}
                <button className="qm-btn-next" onClick={onNext}>
                  {!isLast ? <span className="qm-btn-next-inner">下一个<ChevronRightIcon /></span> : '查看结果'}
                </button>
              </div>
              {keyHints}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
