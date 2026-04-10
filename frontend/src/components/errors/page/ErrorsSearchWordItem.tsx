import type { WrongWordRecord } from '../../../features/vocabulary/wrongWordsStore'
import { normalizeWrongWordKey } from './errorsPageHelpers'

interface ErrorsSearchWordItemProps {
  word: WrongWordRecord
  selectedWordKeySet: Set<string>
  toggleWordSelection: (word: string) => void
}

function buildSearchMeaningLine(word: WrongWordRecord): string {
  return [word.pos?.trim(), word.definition?.trim()].filter(Boolean).join(' ')
}

export function ErrorsSearchWordItem({
  word,
  selectedWordKeySet,
  toggleWordSelection,
}: ErrorsSearchWordItemProps) {
  const wordKey = normalizeWrongWordKey(word.word)
  const checked = selectedWordKeySet.has(wordKey)
  const meaningLine = buildSearchMeaningLine(word)

  return (
    <div className={`errors-search-item${checked ? ' is-selected' : ''}`}>
      <div className="errors-search-item-main">
        <div className="errors-search-item-row">
          <span className="errors-search-item-word">{word.word}</span>
          <span className="errors-search-item-definition">
            {meaningLine || '暂无释义'}
          </span>
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
