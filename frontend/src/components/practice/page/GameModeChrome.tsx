import type {
  GameCampaignNode,
  GameCampaignRecoveryItem,
  GameCampaignState,
} from '../../../lib'
import { NODE_STATUS_LABELS, NODE_TYPE_LABELS, getChallengeStep } from './GameModeSections'
import { gameAsset } from './game-mode/gameAssets'
import { LEVEL_KIND_LABELS, getLevelKind } from './game-mode/gameData'

const FALLBACK_REWARDS = {
  coins: 0,
  diamonds: 0,
  exp: 0,
  stars: 0,
  chest: 'normal',
  bestHits: 0,
} as const

function ResourceChip({
  icon,
  value,
  label,
}: {
  icon: string
  value: string | number
  label: string
}) {
  return (
    <span className="practice-game-mode__resource-chip" aria-label={`${label} ${value}`}>
      <img src={icon} alt="" aria-hidden="true" />
      <strong>{value}</strong>
      <small>{label}</small>
    </span>
  )
}

function StarStrip({ earned }: { earned: number }) {
  return (
    <span className="practice-game-mode__star-strip" aria-label={`${earned}/3 星`}>
      {[0, 1, 2].map(index => (
        <img
          key={index}
          src={index < earned ? gameAsset.reward.star1 : gameAsset.reward.starGrey1}
          alt=""
          aria-hidden="true"
        />
      ))}
    </span>
  )
}

function RecoveryStat({
  title,
  items,
}: {
  title: string
  items: GameCampaignRecoveryItem[]
}) {
  const item = items[0]
  return (
    <article className="practice-game-mode__recovery-stat">
      <img src={gameAsset.icons.restart} alt="" aria-hidden="true" />
      <span>{title}</span>
      <strong>{items.length}</strong>
      <small>{item ? item.title : '当前为空'}</small>
    </article>
  )
}

function getLessonLabel(currentNode: GameCampaignNode) {
  if (currentNode.nodeType !== 'word' || !currentNode.dimension) return NODE_TYPE_LABELS[currentNode.nodeType]
  return `${getChallengeStep(currentNode)}/5 ${LEVEL_KIND_LABELS[getLevelKind(currentNode)]}`
}

export function GameCampaignHud({
  state,
  currentNode,
  onBackToPlan,
}: {
  state: GameCampaignState
  currentNode: GameCampaignNode
  onBackToPlan?: () => void
}) {
  const rewards = state.rewards ?? FALLBACK_REWARDS
  const energy = state.session?.energy ?? 0
  const energyMax = state.session?.energyMax ?? 5
  const playerLevel = Math.max(1, state.campaign.clearedSegments + 1)

  return (
    <header className="practice-game-mode__hud">
      <button type="button" className="practice-game-mode__hud-brand" onClick={() => onBackToPlan?.()}>
        <img src={gameAsset.character.boyIdle} alt="" className="practice-game-mode__hud-brand-logo" aria-hidden="true" />
        <span>Lv.{playerLevel}</span>
      </button>

      <div className="practice-game-mode__hud-copy">
        <span className="practice-game-mode__hud-eyebrow">五维词关</span>
        <strong>{state.campaign.title}</strong>
        <span>{state.campaign.scopeLabel}</span>
      </div>

      <div className="practice-game-mode__hud-meta">
        <ResourceChip icon={gameAsset.reward.energy} value={`${energy}/${energyMax}`} label="体力" />
        <ResourceChip icon={gameAsset.reward.coin} value={rewards.coins} label="金币" />
        <ResourceChip icon={gameAsset.reward.diamond} value={rewards.diamonds} label="宝石" />
        <ResourceChip icon={gameAsset.menu.mail} value="Mail" label="信箱" />
        <span>整本词书 {state.campaign.passedWords}/{state.campaign.totalWords} 已通关</span>
        <span>当前第 {state.campaign.currentSegment}/{Math.max(state.campaign.totalSegments, 1)} 段</span>
        <span>分数 {state.session?.score ?? 0} · 连击 {state.session?.hits ?? 0}</span>
        <span>{NODE_TYPE_LABELS[currentNode.nodeType]}</span>
      </div>
    </header>
  )
}

export function GameLessonCard({
  state,
  currentNode,
}: {
  state: GameCampaignState
  currentNode: GameCampaignNode
}) {
  const rewards = state.rewards ?? FALLBACK_REWARDS
  const earnedStars = Math.min(3, Math.max(0, rewards.stars || state.session?.hits || 0))

  return (
    <section className="practice-game-mode__lesson-card">
      <div className="practice-game-mode__lesson-copy">
        <span className="practice-game-mode__lesson-eyebrow">Lesson {state.segment.index}</span>
        <strong>{state.segment.title}</strong>
        <span>{getLessonLabel(currentNode)} · 本段词链 {state.segment.clearedWords}/{state.segment.totalWords}</span>
      </div>

      <div className="practice-game-mode__lesson-score">
        <StarStrip earned={earnedStars} />
        <span>关卡奖励 x{rewards.coins || 200}</span>
      </div>

      <div className="practice-game-mode__lesson-chips">
        <span>Boss {NODE_STATUS_LABELS[state.segment.bossStatus]}</span>
        <span>奖励关 {NODE_STATUS_LABELS[state.segment.rewardStatus]}</span>
        <span>{state.speakingReward ? '口语彩蛋已开启' : '等待奖励触发'}</span>
      </div>
    </section>
  )
}

export function RecoveryDock({
  recoveryPanel,
  onResume,
}: {
  recoveryPanel: GameCampaignState['recoveryPanel']
  onResume: () => void
}) {
  return (
    <section className="practice-game-mode__recovery-dock">
      <div className="practice-game-mode__recovery-head">
        <div>
          <span className="practice-game-mode__lesson-eyebrow">战役回流区</span>
          <strong>独立错词体系</strong>
        </div>
        {recoveryPanel.resumeNode ? (
          <button type="button" className="practice-game-mode__recovery-action" onClick={onResume}>
            回到最近待补节点
          </button>
        ) : null}
      </div>

      <div className="practice-game-mode__recovery-stats">
        <RecoveryStat title="当前回流队列" items={recoveryPanel.queue} />
        <RecoveryStat title="Boss 重打队列" items={recoveryPanel.bossQueue} />
        <RecoveryStat title="最近失手" items={recoveryPanel.recentMisses} />
      </div>
    </section>
  )
}
