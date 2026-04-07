import {
  type WrongWordCollectionScope,
  type WrongWordDimension,
  type WrongWordRecord,
  getWrongWordActiveCount,
} from '../../../features/vocabulary/wrongWordsStore'
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

  return (
    <div className="errors-item">
      <div className="errors-item-main">
        <div className="errors-item-word-row">
          <span className="errors-item-word">{word.word}</span>
          <span className="errors-item-total-count">
            {scope === 'pending'
              ? `待清错次×${getWrongWordActiveCount(word, 'pending')}`
              : `累计错次×${getWrongWordActiveCount(word, 'history')}`}
          </span>
        </div>
        {(word.phonetic || collectedOn) && (
          <div className="errors-item-meta">
            {word.phonetic && <div className="errors-item-phonetic">{word.phonetic}</div>}
            {collectedOn && <span className="errors-item-date">收录于 {collectedOn}</span>}
          </div>
        )}
        <div className="errors-item-definition">
          {word.pos && <span className="word-pos-tag">{word.pos}</span>}
          {word.definition}
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
        <div className="errors-stage-note">{progress.statusDescription}</div>

        <div className="errors-item-meters">
          <div className="errors-meter">
            <div className="errors-meter-head">
              <span>错词本进度</span>
              <strong>{progress.bookProgressLabel}</strong>
            </div>
            <div className="errors-meter-bar">
              <span
                className={`errors-meter-fill errors-meter-fill--${progress.statusTone}`}
                style={{ width: `${progress.bookProgressPercent}%` }}
              />
            </div>
            <div className="errors-meter-note">{progress.bookProgressNote}</div>
          </div>

          <div className="errors-meter">
            <div className="errors-meter-head">
              <span>长期复习</span>
              <strong>{progress.reviewProgressLabel}</strong>
            </div>
            <div className="errors-meter-bar">
              <span
                className={`errors-meter-fill ${word.ebbinghaus_completed ? 'errors-meter-fill--success' : 'errors-meter-fill--accent'}`}
                style={{ width: `${progress.reviewProgressPercent}%` }}
              />
            </div>
            <div className="errors-meter-note">{progress.reviewProgressNote}</div>
          </div>
        </div>

        <div className="errors-item-dim-tracks">
          {progress.dimensions.map(dimension => (
            <div
              key={dimension.dimension}
              className={`errors-dim-track${dimension.pending ? ' is-pending' : ' is-cleared'}${dimFilter === dimension.dimension ? ' is-highlighted' : ''}`}
            >
              <div className="errors-dim-track-head">
                <span>{dimension.label}</span>
                <strong>{dimension.headline}</strong>
              </div>
              <div className="errors-dim-track-bar">
                <span
                  className={`errors-dim-track-fill${dimension.pending ? '' : ' is-cleared'}`}
                  style={{ width: `${dimension.progressPercent}%` }}
                />
              </div>
              <div className="errors-dim-track-note">{dimension.detail}</div>
            </div>
          ))}
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
