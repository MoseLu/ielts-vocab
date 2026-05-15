import {
  type WrongWordCollectionScope,
  type WrongWordDimension,
  type WrongWordRecord,
  getWrongWordActiveCount,
} from '../../../features/vocabulary/wrongWordsStore'
import { formatWrongWordOccurrenceDate } from '../../../features/vocabulary/wrongWordsFilters'
import { parseWordMeaningGroups } from '../../../lib/wordMeaning'
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
  const activeWrongCount = getWrongWordActiveCount(word, scope)
  const meaningGroups = parseWordMeaningGroups({ definition: word.definition, pos: word.pos })
  const meaningText = meaningGroups
    .map(group => group.meaningText)
    .filter(Boolean)
    .join('；') || '暂无释义'
  const posLabel = Array.from(new Set(
    meaningGroups.map(group => group.posLabel).filter(Boolean),
  )).join(' / ')
  const checklistClassName = `errors-item-checklist${progress.dimensions.length > 3 ? ' is-dense' : ''}`

  return (
    <div className={`errors-item${checked ? ' is-selected' : ''}`}>
      <section className="errors-item-card errors-item-card--word">
        <div className="errors-item-word-line errors-item-word-line--head">
          <span className="errors-item-word">{word.word}</span>
          <span className="errors-item-count-badge">错{activeWrongCount}</span>
        </div>

        <div className="errors-item-word-line">
          {word.phonetic && <span className="errors-item-phonetic">{word.phonetic}</span>}
        </div>

        <div className="errors-item-word-line errors-item-word-line--meaning">
          <span className="errors-item-meaning">{meaningText}</span>
          {posLabel && (
            <span className="errors-item-pos-badge">{posLabel}</span>
          )}
        </div>

        <div className="errors-item-word-line">
          {collectedOn && <span className="errors-item-date">收录于 {collectedOn}</span>}
        </div>
      </section>

      <section className="errors-item-card errors-item-card--todo">
        {progress.dimensions.length > 0 ? (
          <div className={checklistClassName}>
            {progress.dimensions.map(dimension => (
              <div
                key={dimension.dimension}
                className={`errors-item-check-row ${dimension.pending ? 'is-pending' : 'is-cleared'}${dimFilter === dimension.dimension ? ' is-highlighted' : ''}`}
                title={dimension.detail}
              >
                <span className="errors-item-check-mark" aria-hidden="true">
                  {dimension.pending ? '' : '✓'}
                </span>
                <span className="errors-item-check-label">{dimension.label}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="errors-item-todo-empty">暂无模式维度</div>
        )}
      </section>

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
