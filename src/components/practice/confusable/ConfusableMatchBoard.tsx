import type { MatchCard } from '../confusableMatch'
import type { ActiveLine } from './confusableMatchPageHelpers'

export interface ConfusableBoardGroup {
  key: string
  cards: MatchCard[]
}

interface ConfusableMatchBoardProps {
  boardGroups: ConfusableBoardGroup[]
  selectedCard: MatchCard | null
  activeLine: ActiveLine | null
  errorCardIds: string[]
  successCardIds: string[]
  groupBoardRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>
  cardRefs: React.MutableRefObject<Record<string, HTMLButtonElement | null>>
  onCardClick: (card: MatchCard) => void
}

export function ConfusableMatchBoard({
  boardGroups,
  selectedCard,
  activeLine,
  errorCardIds,
  successCardIds,
  groupBoardRefs,
  cardRefs,
  onCardClick,
}: ConfusableMatchBoardProps) {
  return (
    <div className="confusable-board">
      <div className="confusable-group-grid">
        {boardGroups.map((group, index) => {
          const isSelectedGroup = selectedCard?.groupKey === group.key
          const isSuccessGroup = activeLine?.groupKey === group.key
          const isErrorGroup = group.cards.some(card => errorCardIds.includes(card.id))

          return (
            <section
              key={group.key}
              className={[
                'confusable-group-panel',
                isSelectedGroup ? 'is-selected' : '',
                isSuccessGroup ? 'is-success' : '',
                isErrorGroup ? 'is-error' : '',
              ].filter(Boolean).join(' ')}
              aria-label={`易混组 ${index + 1}`}
            >
              <div className="confusable-group-head">
                <span className="confusable-group-label">易混组 {index + 1}</span>
                <span className="confusable-group-meta">{Math.max(1, group.cards.length / 2)} 对待消除</span>
              </div>

              <div
                className="confusable-group-board"
                ref={element => { groupBoardRefs.current[group.key] = element }}
              >
                <svg className="confusable-lines" aria-hidden="true">
                  {activeLine?.groupKey === group.key && (
                    <path d={activeLine.path} className="confusable-line confusable-line--success" />
                  )}
                </svg>

                <div className="confusable-card-grid">
                  {group.cards.map(card => {
                    const isSelected = selectedCard?.id === card.id
                    const isSuccess = successCardIds.includes(card.id)
                    const isError = errorCardIds.includes(card.id)

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
                            <span className="confusable-card-word">{card.label}</span>
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
            </section>
          )
        })}
      </div>
    </div>
  )
}
