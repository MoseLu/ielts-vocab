import type { MatchCard, MatchWord } from '../confusableMatch'
import { getSelectionHint, type ActiveLine } from './confusableMatchPageHelpers'
import {
  buildConfusableContrastNote,
  buildWordDiffParts,
  getConfusableGroupAccent,
  summarizeConfusableWords,
} from './confusableBoardPresentation'

export interface ConfusableBoardGroup {
  key: string
  groupNumber: number
  words: MatchWord[]
  cards: MatchCard[]
}

interface ConfusableMatchBoardProps {
  boardGroups: ConfusableBoardGroup[]
  queuedGroups: ConfusableBoardGroup[]
  selectedCard: MatchCard | null
  activeLine: ActiveLine | null
  errorCardIds: string[]
  successCardIds: string[]
  answeredGroupCount: number
  totalGroups: number
  completedGroup: ConfusableBoardGroup | null
  errorComparison: { fromWord: string; toWord: string } | null
  groupBoardRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>
  cardRefs: React.MutableRefObject<Record<string, HTMLButtonElement | null>>
  onCardClick: (card: MatchCard) => void
}

function renderWordParts(word: string, compareTo?: string) {
  return buildWordDiffParts(word, compareTo).map((part, index) => (
    <span
      key={`${word}-${index}-${part.text}`}
      className={part.isDiff ? 'confusable-card-word-part is-diff' : 'confusable-card-word-part'}
    >
      {part.text}
    </span>
  ))
}

export function ConfusableMatchBoard({
  boardGroups,
  queuedGroups,
  selectedCard,
  activeLine,
  errorCardIds,
  successCardIds,
  answeredGroupCount,
  totalGroups,
  completedGroup,
  errorComparison,
  groupBoardRefs,
  cardRefs,
  onCardClick,
}: ConfusableMatchBoardProps) {
  const activeGroup = boardGroups[0] ?? null
  const activeLinePath = activeLine?.path ?? null
  const showActiveLine = Boolean(
    activeGroup
    && activeLinePath
    && activeLine?.groupKey === activeGroup.key,
  )
  const focusGroup = completedGroup ?? activeGroup
  const focusAccent = focusGroup ? getConfusableGroupAccent(focusGroup.key) : 'var(--accent)'
  const progressRatio = totalGroups > 0 ? answeredGroupCount / totalGroups : 0
  const summaryTitle = completedGroup
    ? `词族 ${completedGroup.groupNumber} 已完成`
    : selectedCard
      ? '已选中一张卡片'
      : activeGroup
        ? `词族 ${activeGroup.groupNumber} / ${totalGroups}`
        : '等待下一组'
  const summaryHint = completedGroup
    ? '先看一眼这一组的差异，再进入下一组。'
    : getSelectionHint(selectedCard)

  return (
    <div className="confusable-board">
      <div className="confusable-workspace">
        <section
          className={`confusable-focus-panel ${completedGroup ? 'is-completed' : ''}`}
          style={{
            ['--confusable-group-accent' as string]: focusAccent,
            ['--confusable-progress-ratio' as string]: String(progressRatio),
          }}
        >
          <div className="confusable-focus-head">
            <div className="confusable-focus-copy">
              <span className="confusable-focus-kicker">{summaryTitle}</span>
              <h2>{focusGroup ? summarizeConfusableWords(focusGroup.words, 5) : '当前词族已完成'}</h2>
              <p>{summaryHint}</p>
            </div>

            <div className="confusable-progress-ring" aria-label={`已完成 ${answeredGroupCount} / ${totalGroups} 组`}>
              <div className="confusable-progress-ring__core">
                <strong>{answeredGroupCount}</strong>
                <span>/ {totalGroups} 组</span>
              </div>
            </div>
          </div>

          <div className="confusable-focus-body">
            <div className="confusable-group-board" ref={element => {
              if (activeGroup) {
                groupBoardRefs.current[activeGroup.key] = element
              }
            }}>
              <svg className="confusable-lines" aria-hidden="true">
                {showActiveLine ? (
                  <path d={activeLinePath ?? undefined} className="confusable-line confusable-line--success" />
                ) : null}
              </svg>

              <div className="confusable-card-grid">
                {activeGroup?.cards.map(card => {
                  const isSelected = selectedCard?.id === card.id
                  const isSuccess = successCardIds.includes(card.id)
                  const isError = errorCardIds.includes(card.id)
                  const compareWord = errorComparison
                    ? card.word === errorComparison.fromWord
                      ? errorComparison.toWord
                      : card.word === errorComparison.toWord
                        ? errorComparison.fromWord
                        : undefined
                    : undefined

                  return (
                    <button
                      key={card.id}
                      ref={element => { cardRefs.current[card.id] = element }}
                      type="button"
                      data-card-id={card.id}
                      className={[
                        'confusable-card',
                        `confusable-card--${card.side}`,
                        isSelected ? 'is-selected' : '',
                        isSuccess ? 'is-success' : '',
                        isError ? 'is-error' : '',
                      ].filter(Boolean).join(' ')}
                      onClick={() => onCardClick(card)}
                    >
                      <span className={`confusable-card-badge confusable-card-badge--${card.side}`}>
                        {card.side === 'word' ? 'EN' : '中'}
                      </span>
                      {card.side === 'word' ? (
                        <>
                          <span className="confusable-card-word">
                            {renderWordParts(card.label, compareWord)}
                          </span>
                          {card.phonetic && <span className="confusable-card-phonetic">{card.phonetic}</span>}
                        </>
                      ) : (
                        <span className="confusable-card-definition">{card.label}</span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            <aside className="confusable-side-rail">
              <section className={`confusable-insight-panel ${completedGroup ? 'is-visible' : ''}`}>
                <span className="confusable-side-kicker">
                  {completedGroup ? '本组辨析' : '辨析提示'}
                </span>
                <strong>
                  {focusGroup ? summarizeConfusableWords(focusGroup.words, 3) : '完成一组后，这里会显示提示'}
                </strong>
                <p>
                  {focusGroup ? buildConfusableContrastNote(focusGroup.words) : '先完成当前词族，再看这一组为什么容易混。'}
                </p>
                {focusGroup && (
                  <div className="confusable-insight-list">
                    {focusGroup.words.map(word => (
                      <div key={word.key} className="confusable-insight-item">
                        <span className="confusable-insight-word">{word.word}</span>
                        <span className="confusable-insight-meaning">{word.definition}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="confusable-queue-panel">
                <span className="confusable-side-kicker">下一组</span>
                <div className="confusable-queue-list">
                  {queuedGroups.length > 0 ? queuedGroups.map(group => (
                    <div
                      key={group.key}
                      className="confusable-queue-item"
                      style={{ ['--confusable-group-accent' as string]: getConfusableGroupAccent(group.key) }}
                    >
                      <strong>词族 {group.groupNumber}</strong>
                      <span>{summarizeConfusableWords(group.words, 3)}</span>
                    </div>
                  )) : (
                    <div className="confusable-queue-empty">当前章节只剩这一组，完成后即可通关。</div>
                  )}
                </div>
              </section>
            </aside>
          </div>
        </section>
      </div>
    </div>
  )
}
