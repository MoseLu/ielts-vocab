import type { GameCampaignState, GameLevelCard, GameLevelKind } from '../../../../lib'
import { LEVEL_KIND_LABELS } from './gameData'
import { prdUiAsset } from './prdUiAssets'

type CounterKind = 'energy' | 'coin' | 'gem'

const PRD_DIMENSION_BY_KIND: Record<GameLevelKind, {
  label: string
  name: string
  card: string
  icon: string
}> = {
  spelling: {
    label: 'Language Use',
    name: '语言应用',
    card: prdUiAsset.cards.languageUse,
    icon: prdUiAsset.icons.abc,
  },
  pronunciation: {
    label: 'Speaking',
    name: '口语',
    card: prdUiAsset.cards.speaking,
    icon: prdUiAsset.icons.microphone,
  },
  definition: {
    label: 'Reading',
    name: '阅读',
    card: prdUiAsset.cards.reading,
    icon: prdUiAsset.icons.book,
  },
  speaking: {
    label: 'Listening',
    name: '听力',
    card: prdUiAsset.cards.listening,
    icon: prdUiAsset.icons.sound,
  },
  example: {
    label: 'Writing',
    name: '写作',
    card: prdUiAsset.cards.writing,
    icon: prdUiAsset.icons.pen,
  },
}

const SIDE_ACTIONS = [
  { label: '背包', icon: prdUiAsset.icons.bag },
  { label: '任务', icon: prdUiAsset.icons.task },
  { label: '成就', icon: prdUiAsset.icons.achievement },
  { label: '商店', icon: prdUiAsset.icons.shop },
  { label: '排行', icon: prdUiAsset.icons.rank },
  { label: '设置', icon: prdUiAsset.icons.setting },
] as const

function formatCount(value: number): string {
  return Math.max(0, value).toLocaleString('zh-CN')
}

export function prdMapBackgroundForTheme(themeId?: string | null): string {
  return themeId === 'environment-nature'
    ? prdUiAsset.background.mapEnvironment
    : prdUiAsset.background.mapEducation
}

export function prdSceneBackdropForKind(_levelKind: GameLevelKind): string {
  return prdUiAsset.background.classroomBlur
}

export function prdSegmentBadgeAsset(status: 'active' | 'cleared' | 'locked' | 'ready'): string {
  if (status === 'cleared') return prdUiAsset.map.levelBadgeGold
  if (status === 'active') return prdUiAsset.map.levelBadgeBlue
  if (status === 'ready') return prdUiAsset.map.levelBadgeGray
  return prdUiAsset.map.levelBadgeLocked
}

export function prdStarAsset(filled: boolean): string {
  return filled ? prdUiAsset.map.starFull : prdUiAsset.map.starEmpty
}

export function prdCurrentNodeAsset(): string {
  return prdUiAsset.map.nodeCurrent
}

function buttonAssetForStatus(status: GameLevelCard['status']): string {
  if (status === 'passed') return prdUiAsset.buttons.gold
  if (status === 'active' || status === 'ready') return prdUiAsset.buttons.green
  if (status === 'pending') return prdUiAsset.buttons.purple
  if (status === 'locked') return prdUiAsset.buttons.disabled
  return prdUiAsset.buttons.blue
}

function badgeAssetForCardStatus(status: GameLevelCard['status']): string {
  if (status === 'passed') return prdUiAsset.map.levelBadgeGold
  if (status === 'active') return prdUiAsset.map.levelBadgeBlue
  if (status === 'locked') return prdUiAsset.map.levelBadgeLocked
  return prdUiAsset.map.levelBadgeGray
}

function ctaForStatus(status: GameLevelCard['status']): string {
  if (status === 'passed') return '已完成'
  if (status === 'active') return '开始训练'
  if (status === 'ready') return '继续训练'
  if (status === 'pending') return '复习'
  return '未解锁'
}

function counterIcon(kind: CounterKind): string {
  if (kind === 'energy') return prdUiAsset.hud.iconEnergy
  if (kind === 'coin') return prdUiAsset.hud.iconCoin
  return prdUiAsset.hud.iconGem
}

export function PrdMapHud({
  avatar,
  playerLevel,
  levelProgress,
  energy,
  energyMax,
  coins,
  diamonds,
  unreadMessages,
  onBackToPlan,
}: {
  avatar: string
  playerLevel: number
  levelProgress: number
  energy: number
  energyMax: number
  coins: number
  diamonds: number
  unreadMessages: number
  onBackToPlan?: () => void
}) {
  const counters = [
    { kind: 'energy' as const, label: '体力', value: `${energy}/${energyMax}` },
    { kind: 'coin' as const, label: '金币', value: formatCount(coins) },
    { kind: 'gem' as const, label: '钻石', value: formatCount(diamonds) },
  ]

  return (
    <header className="practice-game-map__hud practice-game-map__prd-hud" aria-label="真实学习数据">
      <button
        type="button"
        className="practice-game-map__prd-avatar"
        onClick={() => onBackToPlan?.()}
        aria-label="返回学习计划"
      >
        <span className="practice-game-map__prd-avatar-portrait">
          <img className="practice-game-map__prd-avatar-frame" src={prdUiAsset.hud.avatarFrame} alt="" aria-hidden="true" />
          <img className="practice-game-map__prd-avatar-photo" src={avatar} alt="" aria-hidden="true" />
        </span>
        <span className="practice-game-map__prd-avatar-level-pill">
          <img className="practice-game-map__prd-avatar-pill" src={prdUiAsset.hud.resourcePill} alt="" aria-hidden="true" />
          <strong>Lv.{playerLevel}</strong>
          <span className="practice-game-map__avatar-level" aria-hidden="true">
            <span style={{ width: `${levelProgress}%` }} />
          </span>
        </span>
      </button>
      {counters.map(counter => (
        <span key={counter.kind} className={`practice-game-map__prd-counter is-${counter.kind}`} aria-label={counter.label}>
          <img className="practice-game-map__prd-counter-frame" src={prdUiAsset.hud.resourcePill} alt="" aria-hidden="true" />
          <img className="practice-game-map__prd-counter-icon" src={counterIcon(counter.kind)} alt="" aria-hidden="true" />
          <strong>{counter.value}</strong>
        </span>
      ))}
      <button type="button" className="practice-game-map__prd-mail" aria-label={`站内信，${unreadMessages} 条未读`}>
        <img src={prdUiAsset.hud.iconMail} alt="" aria-hidden="true" />
        {unreadMessages > 0 ? <strong>{formatCount(unreadMessages)}</strong> : null}
      </button>
    </header>
  )
}

export function PrdExitButton({
  onBackToPlan,
}: {
  onBackToPlan?: () => void
}) {
  return (
    <button type="button" className="practice-game-map__prd-exit" onClick={() => onBackToPlan?.()} aria-label="退出地图">
      <img className="practice-game-map__prd-exit-bg" src={prdUiAsset.buttons.red} alt="" aria-hidden="true" />
      <img className="practice-game-map__prd-exit-icon" src={prdUiAsset.icons.back} alt="" aria-hidden="true" />
      <span>退出</span>
    </button>
  )
}

export function PrdSideRail() {
  return (
    <nav className="practice-game-map__prd-side" aria-label="地图功能栏">
      {SIDE_ACTIONS.map(action => (
        <button key={action.label} type="button" aria-label={action.label}>
          <img src={action.icon} alt="" aria-hidden="true" />
          <span>{action.label}</span>
        </button>
      ))}
    </nav>
  )
}

export function PrdStartButton({
  canStart,
  isStarting,
  onStart,
}: {
  canStart: boolean
  isStarting: boolean
  onStart: () => void
}) {
  const disabled = !canStart || isStarting
  return (
    <button
      type="button"
      className="practice-game-map__prd-start"
      onClick={onStart}
      disabled={disabled}
      aria-label="开始当前词关"
    >
      <img src={disabled ? prdUiAsset.buttons.disabled : prdUiAsset.buttons.green} alt="" aria-hidden="true" />
      <span>{isStarting ? '进入中' : '开始当前词关'}</span>
    </button>
  )
}

export function PrdDimensionDeck({
  levelCards,
  canStart,
  isStarting,
  onStart,
}: {
  levelCards: GameLevelCard[]
  canStart: boolean
  isStarting: boolean
  onStart: () => void
}) {
  return (
    <section className="practice-game-map__prd-dimensions" aria-label="五维训练入口">
      {levelCards.map(card => {
        const config = PRD_DIMENSION_BY_KIND[card.kind]
        const disabled = card.status === 'locked' || !canStart || isStarting
        return (
          <article key={card.kind} className={`practice-game-map__prd-card is-${card.status}`}>
            <img className="practice-game-map__prd-card-bg" src={config.card} alt="" aria-hidden="true" />
            {card.status === 'active' ? (
              <img className="practice-game-map__prd-card-focus" src={prdUiAsset.buttons.focusGlow} alt="" aria-hidden="true" />
            ) : null}
            <img className="practice-game-map__prd-card-badge" src={badgeAssetForCardStatus(card.status)} alt="" aria-hidden="true" />
            <img className="practice-game-map__prd-card-icon" src={config.icon} alt="" aria-hidden="true" />
            <div className="practice-game-map__prd-card-copy">
              <span>{config.label}</span>
              <strong>{config.name}</strong>
              <small>{card.subtitle || LEVEL_KIND_LABELS[card.kind]}</small>
            </div>
            <button type="button" onClick={onStart} disabled={disabled} aria-label={`${config.name}：${ctaForStatus(card.status)}`}>
              <img src={buttonAssetForStatus(disabled ? 'locked' : card.status)} alt="" aria-hidden="true" />
              <span>{ctaForStatus(card.status)}</span>
            </button>
          </article>
        )
      })}
    </section>
  )
}

export function PrdReportPanel({
  state,
}: {
  state: GameCampaignState
}) {
  const totalWords = Math.max(0, state.campaign.totalWords)
  const passedWords = Math.max(0, state.campaign.passedWords)
  return (
    <aside className="practice-game-map__prd-report" aria-label="学习报告入口">
      <img className="practice-game-map__prd-report-bg" src={prdUiAsset.modal.panelReport} alt="" aria-hidden="true" />
      <img className="practice-game-map__prd-report-title" src={prdUiAsset.modal.parchmentTitle} alt="" aria-hidden="true" />
      <img className="practice-game-map__prd-report-boss" src={prdUiAsset.map.nodeBoss} alt="" aria-hidden="true" />
      <div>
        <span>学习报告</span>
        <strong>{formatCount(passedWords)} / {formatCount(totalWords)}</strong>
        <small>五维能力与主题掌握度</small>
      </div>
      <button type="button">
        <img src={prdUiAsset.buttons.purple} alt="" aria-hidden="true" />
        <span>查看报告</span>
      </button>
    </aside>
  )
}

export function PrdRewardCover({
  cleared,
  total,
}: {
  cleared: number
  total: number
}) {
  const isOpen = total > 0 && cleared >= total
  return (
    <div className="practice-game-map__reward-cover practice-game-map__prd-treasure" aria-hidden="true">
      <img className="practice-game-map__reward-chest" src={isOpen ? prdUiAsset.map.treasureOpen : prdUiAsset.map.treasureClosed} alt="" />
      <strong>{cleared}/{total}</strong>
    </div>
  )
}
