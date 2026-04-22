import type { GameCampaignState } from '../../../../lib'
import { gameAsset } from './gameAssets'

function StatPill({
  icon,
  value,
  label,
}: {
  icon: string
  value: string | number
  label: string
}) {
  return (
    <span className="practice-game-map__stat">
      <img src={icon} alt="" aria-hidden="true" />
      <strong>{value}</strong>
      <small>{label}</small>
    </span>
  )
}

function DockMeta({
  icon,
  text,
}: {
  icon: string
  text: string
}) {
  return (
    <span className="practice-game-map__dock-meta-item">
      <img src={icon} alt="" aria-hidden="true" />
      <span>{text}</span>
    </span>
  )
}

export function GameMapShell({
  state,
  isStarting,
  error,
  onStart,
  onBackToPlan,
}: {
  state: GameCampaignState
  isStarting: boolean
  error: string | null
  onStart: () => void
  onBackToPlan?: () => void
}) {
  const launcher = state.launcher
  const session = state.session
  const currentNode = state.currentNode
  const rewards = state.rewards ?? {
    coins: 0,
    diamonds: 0,
    exp: 0,
    stars: 0,
    chest: 'normal',
    bestHits: 0,
  }
  const levelCards = state.levelCards ?? []
  const energy = session?.energy ?? 0
  const energyMax = session?.energyMax ?? 5
  const energyCost = launcher?.energyCost ?? 2
  const canStart = energy >= energyCost && Boolean(currentNode)

  return (
    <section className="practice-game-map" aria-label="五维词关地图">
      <div className="practice-game-map__hud">
        <button type="button" className="practice-game-map__home" onClick={() => onBackToPlan?.()}>
          <img src={gameAsset.icons.home} alt="" aria-hidden="true" />
          <span>学习计划</span>
        </button>
        <div className="practice-game-map__title">
          <span>
            <img src={gameAsset.icons.target} alt="" aria-hidden="true" />
            五维词关
          </span>
          <strong>{state.campaign.scopeLabel}</strong>
        </div>
        <div className="practice-game-map__stats" aria-label="游戏资源">
          <StatPill icon={gameAsset.reward.energy} value={`${energy}/${energyMax}`} label="体力" />
          <StatPill icon={gameAsset.reward.coin} value={rewards.coins} label="金币" />
          <StatPill icon={gameAsset.reward.diamond} value={rewards.diamonds} label="宝石" />
        </div>
      </div>

      <div className="practice-game-map__world">
        <picture className="practice-game-map__picture" aria-hidden="true">
          <source media="(max-width: 640px)" srcSet={gameAsset.map.backgrounds.mobile} />
          <source media="(max-width: 1100px)" srcSet={gameAsset.map.backgrounds.tablet} />
          <img src={gameAsset.map.backgrounds.desktop} alt="" className="practice-game-map__image" />
        </picture>
        <img src={gameAsset.map.layers.far} alt="" className="practice-game-map__layer practice-game-map__layer--far" aria-hidden="true" />
        <img src={gameAsset.map.layers.mid} alt="" className="practice-game-map__layer practice-game-map__layer--mid" aria-hidden="true" />
        <img src={gameAsset.map.forest} alt="" className="practice-game-map__landmark practice-game-map__landmark--forest" aria-hidden="true" />
        <img src={gameAsset.map.lake} alt="" className="practice-game-map__landmark practice-game-map__landmark--lake" aria-hidden="true" />
        <img src={gameAsset.map.mountain} alt="" className="practice-game-map__landmark practice-game-map__landmark--mountain" aria-hidden="true" />
        <img src={gameAsset.map.castle} alt="" className="practice-game-map__landmark practice-game-map__landmark--castle" aria-hidden="true" />
        {levelCards.map((card, index) => (
          <div
            key={card.kind}
            className={`practice-game-map__node practice-game-map__node--${card.kind} is-${card.status}`}
          >
            <img src={gameAsset.map.nodes[index] ?? gameAsset.map.nodes[0]} alt="" aria-hidden="true" />
            <strong>{card.step}/5</strong>
            <span>{card.label}</span>
          </div>
        ))}
        <img src={gameAsset.map.layers.front} alt="" className="practice-game-map__layer practice-game-map__layer--front" aria-hidden="true" />
        <img src={gameAsset.character.boyIdle} alt="" className="practice-game-map__hero" aria-hidden="true" />
        <img src={gameAsset.character.teacher} alt="" className="practice-game-map__mentor" aria-hidden="true" />
      </div>

      <div className="practice-game-map__dock">
        <div>
          <span>当前章节</span>
          <strong>{launcher?.title ?? state.segment.title}</strong>
          <div className="practice-game-map__dock-meta">
            <DockMeta icon={gameAsset.icons.current} text={`当前第 ${state.campaign.currentSegment} 段`} />
            <DockMeta icon={gameAsset.icons.notebook} text={`本段 ${state.segment.clearedWords}/${state.segment.totalWords}`} />
            <DockMeta icon={gameAsset.icons.reward} text={`预计 ${rewards.stars} 星结算`} />
          </div>
          <small>
            已通关 {state.campaign.passedWords}/{state.campaign.totalWords} 个词，
            本段 {state.segment.clearedWords}/{state.segment.totalWords}
          </small>
        </div>
        <button
          type="button"
          className="practice-game-map__start"
          onClick={onStart}
          disabled={!canStart || isStarting}
        >
          {isStarting ? '进入中...' : session?.status === 'result' ? '继续下一段' : '开始词关'}
          <span>消耗 {energyCost} 体力</span>
        </button>
      </div>

      {!canStart ? (
        <div className="practice-game-map__warning">
          {currentNode ? '体力不足，稍后恢复后继续。' : '当前范围没有待挑战节点。'}
        </div>
      ) : null}
      {error ? <div className="practice-game-map__warning">{error}</div> : null}
    </section>
  )
}
