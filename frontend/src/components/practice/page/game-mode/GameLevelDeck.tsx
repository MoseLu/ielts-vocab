import type { GameLevelCard, GameLevelKind } from '../../../../lib'
import { gameAsset } from './gameAssets'

const STATUS_LABELS: Record<GameLevelCard['status'], string> = {
  locked: '锁定',
  ready: '待挑战',
  active: '挑战中',
  pending: '补强中',
  passed: '已通关',
}

export function GameLevelDeck({
  cards,
  activeKind,
}: {
  cards: GameLevelCard[]
  activeKind: GameLevelKind
}) {
  return (
    <div className="practice-game-level-deck" aria-label="五维关卡进度">
      {cards.map(card => (
        <article
          key={card.kind}
          className={`practice-game-level-card is-${card.status}${card.kind === activeKind ? ' is-current' : ''}`}
        >
          <img src={gameAsset.levels[card.kind]} alt="" className="practice-game-level-card__art" aria-hidden="true" />
          <div className="practice-game-level-card__body">
            <span>{card.step}/5</span>
            <strong>{card.label}</strong>
            <small>{STATUS_LABELS[card.status]} · {card.passStreak}/4</small>
          </div>
        </article>
      ))}
    </div>
  )
}
