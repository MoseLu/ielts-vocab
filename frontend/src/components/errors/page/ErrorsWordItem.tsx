import type { CSSProperties } from 'react'
import {
  type WrongWordCollectionScope,
  type WrongWordDimension,
  type WrongWordRecord,
  getWrongWordActiveCount,
} from '../../../features/vocabulary/wrongWordsStore'
import WordMeaningGroups from '../../ui/WordMeaningGroups'
import { formatWrongWordOccurrenceDate } from '../../../features/vocabulary/wrongWordsFilters'
import { normalizeWrongWordKey } from './errorsPageHelpers'
import { buildWrongWordCardModel } from './errorsPageProgress'

interface ErrorsWordItemProps {
  word: WrongWordRecord
  scope: WrongWordCollectionScope
  dimFilter: 'all' | WrongWordDimension
  selectedWordKeySet: Set<string>
  toggleWordSelection: (word: string) => void
}

export function ErrorsWordItem({
  word,
  scope,
  dimFilter,
  selectedWordKeySet,
  toggleWordSelection,
}: ErrorsWordItemProps) {
  const collectedOn = formatWrongWordOccurrenceDate(word)
  const wordKey = normalizeWrongWordKey(word.word)
  const checked = selectedWordKeySet.has(wordKey)
  const progress = buildWrongWordCardModel(word)
  const bookCompactValue = progress.historyDimensionCount > 0
    ? `${progress.clearedDimensionCount}/${progress.historyDimensionCount} 项`
    : '暂无问题项'
  const bookCompactNote = progress.pendingDimensionCount > 0
    ? `待清 ${progress.pendingDimensionCount} 项`
    : '错词本已清空'
  const reviewCompactValue = word.ebbinghaus_completed
    ? '已完成'
    : (progress.reviewTarget > 0 ? `${progress.reviewStreak}/${progress.reviewTarget}` : '未开始')
  const reviewCompactNote = word.ebbinghaus_completed
    ? '长期复习稳定'
    : (
        progress.reviewTarget > 0
          ? `还差 ${progress.reviewRemaining} 次`
          : '清错后进入'
      )
  const compactFocusLabel = progress.focusLabel ?? progress.statusLabel

  return (
    <div className="errors-item">
      <div className="errors-item-main">
        <div className="errors-item-head">
          <div className="errors-item-word-row">
            <span className="errors-item-word">{word.word}</span>
            <span className="errors-item-total-count">
              {scope === 'pending'
                ? `待清错次×${getWrongWordActiveCount(word, 'pending')}`
                : `累计错次×${getWrongWordActiveCount(word, 'history')}`}
            </span>
          </div>

          <div className="errors-stage-row">
            <span className={`errors-stage-pill errors-stage-pill--${progress.statusTone}`}>
              {progress.statusLabel}
            </span>
            {progress.isTodayNew && (
              <span className="errors-stage-pill errors-stage-pill--today">今日新入</span>
            )}
            {progress.feedbackLabel && (
              <span className="errors-stage-pill errors-stage-pill--accent">
                {progress.feedbackLabel}
              </span>
            )}
          </div>
        </div>

        <div className="errors-item-subline">
          {word.phonetic && <span className="errors-item-phonetic">{word.phonetic}</span>}
          {collectedOn && <span className="errors-item-date">收录于 {collectedOn}</span>}
          <WordMeaningGroups
            className="errors-item-definition"
            definition={word.definition}
            pos={word.pos}
            size="sm"
          />
          <span className="errors-item-focus-note" title={progress.statusDescription}>
            {compactFocusLabel}
          </span>
        </div>

        <div className="errors-item-compact-row">
          <div className="errors-item-meters">
            <div className="errors-meter" title={progress.bookProgressNote}>
              <div className="errors-meter-head">
                <span>错词本进度</span>
                <strong>{bookCompactValue}</strong>
              </div>
              <div className="errors-meter-bar">
                <span
                  className={`errors-meter-fill errors-meter-fill--${progress.statusTone}`}
                  style={{ '--progress-percent': `${progress.bookProgressPercent}%` } as CSSProperties}
                />
              </div>
              <div className="errors-meter-note">{bookCompactNote}</div>
            </div>

            <div className="errors-meter" title={progress.reviewProgressNote}>
              <div className="errors-meter-head">
                <span>长期复习</span>
                <strong>{reviewCompactValue}</strong>
              </div>
              <div className="errors-meter-bar">
                <span
                  className={`errors-meter-fill ${word.ebbinghaus_completed ? 'errors-meter-fill--success' : 'errors-meter-fill--accent'}`}
                  style={{ '--progress-percent': `${progress.reviewProgressPercent}%` } as CSSProperties}
                />
              </div>
              <div className="errors-meter-note">{reviewCompactNote}</div>
            </div>
          </div>

          <div className="errors-item-dim-tracks">
            {progress.dimensions.map(dimension => (
              <div
                key={dimension.dimension}
                className={`errors-dim-track${dimension.pending ? ' is-pending' : ' is-cleared'}${dimFilter === dimension.dimension ? ' is-highlighted' : ''}`}
                title={dimension.detail}
              >
                <div className="errors-dim-track-head">
                  <span>{dimension.label}</span>
                  <strong>{dimension.headline}</strong>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <label className={`errors-item-select${checked ? ' errors-item-select--checked' : ''}`}>
        <input
          className="errors-item-checkbox"
          type="checkbox"
          aria-label={`选择 ${word.word}`}
          checked={checked}
          onChange={() => toggleWordSelection(word.word)}
        />
      </label>
    </div>
  )
}
