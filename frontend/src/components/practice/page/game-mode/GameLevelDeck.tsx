import type { GameLevelCard, GameLevelKind } from '../../../../lib'
import { gameAsset } from './gameAssets'

const STATUS_LABELS: Record<GameLevelCard['status'], string> = {
  locked: '锁定',
  ready: '待挑战',
  active: '挑战中',
  pending: '补强中',
  passed: '已通关',
}

function getEarnedStars(card: GameLevelCard) {
  if (card.status === 'passed') return 3
  if (card.status === 'active') return Math.max(1, Math.min(2, card.passStreak))
  if (card.status === 'pending') return 1
  return card.passStreak > 0 ? 1 : 0
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
          <div className="practice-game-level-card__stars" aria-label={`${getEarnedStars(card)}/3 星`}>
            {[0, 1, 2].map(index => (
              <img
                key={index}
                src={index < getEarnedStars(card) ? gameAsset.reward.star1 : gameAsset.reward.starGrey1}
                alt=""
                aria-hidden="true"
              />
            ))}
          </div>
          <div className="practice-game-level-card__body">
            <span>{card.step}/5</span>
            <strong>{card.label}</strong>
            <small>{STATUS_LABELS[card.status]} · 熟练 {card.passStreak}/4</small>
            <img src={gameAsset.icons[card.kind]} alt="" aria-hidden="true" className="practice-game-level-card__icon" />
          </div>
        </article>
      ))}
    </div>
  )
}
