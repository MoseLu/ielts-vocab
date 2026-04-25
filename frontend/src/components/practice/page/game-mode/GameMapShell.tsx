import type { CSSProperties } from 'react'
import type { GameCampaignState, GameLevelCard } from '../../../../lib'
import { gameAsset } from './gameAssets'

type SegmentNodeStyle = CSSProperties & {
  '--map-node-x': string
  '--map-node-y': string
  '--map-node-delay': string
}

type RouteStyle = CSSProperties & {
  '--map-route-progress': string
}

const SEGMENT_NODE_LAYOUT = [
  { x: 18, y: 66 },
  { x: 38, y: 60 },
  { x: 56, y: 55 },
  { x: 72, y: 54 },
  { x: 88, y: 40 },
] as const

const SEGMENT_STATUS_LABEL = {
  active: '当前',
  cleared: '已亮',
  locked: '待练',
} as const

type SegmentStatus = keyof typeof SEGMENT_STATUS_LABEL

const dynamicAsset = gameAsset.campaignDynamic

function segmentBattleNodeAsset(status: SegmentStatus): string {
  if (status === 'cleared') return dynamicAsset.battleNodes.cleared
  if (status === 'active') return dynamicAsset.battleNodes.active
  return dynamicAsset.battleNodes.locked
}

function formatCount(value: number): string {
  return Math.max(0, value).toLocaleString('zh-CN')
}

function progressPercent(done: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((done / total) * 100)))
}

export function GameMapShell({
  state,
  levelCards,
  isStarting,
  error,
  onStart,
  onBackToPlan,
}: {
  state: GameCampaignState
  levelCards: GameLevelCard[]
  isStarting: boolean
  error: string | null
  onStart: () => void
  onBackToPlan?: () => void
}) {
  const session = state.session
  const energy = session?.energy ?? 0
  const energyMax = session?.energyMax ?? 0
  const totalWords = Math.max(0, state.campaign.totalWords)
  const passedWords = Math.max(0, state.campaign.passedWords)
  const wordProgress = progressPercent(passedWords, totalWords)
  const totalSegments = Math.max(1, state.campaign.totalSegments)
  const currentSegment = Math.min(Math.max(1, state.campaign.currentSegment), totalSegments)
  const segmentTotal = Math.max(1, state.segment.totalWords)
  const segmentCleared = Math.min(Math.max(0, state.segment.clearedWords), segmentTotal)
  const segmentProgress = progressPercent(segmentCleared, segmentTotal)
  const hud = state.hud ?? {
    playerLevel: Math.max(1, state.campaign.clearedSegments + 1),
    levelProgressPercent: segmentProgress,
    unreadMessages: 0,
  }
  const playerLevel = Math.max(1, hud.playerLevel)
  const levelProgress = Math.min(100, Math.max(0, hud.levelProgressPercent || segmentProgress))
  const unreadMessages = Math.max(0, hud.unreadMessages)
  const currentSlot = Math.min(segmentTotal, segmentCleared + 1)
  const completedDimensions = levelCards.filter(card => card.status === 'passed').length
  const activeNodeStars = Math.min(3, Math.ceil((completedDimensions / Math.max(1, levelCards.length)) * 3))
  const segmentSlotCount = Math.min(segmentTotal, SEGMENT_NODE_LAYOUT.length)
  const segmentSlotOffset = Math.min(
    Math.max(0, currentSlot - Math.ceil(segmentSlotCount / 2)),
    Math.max(0, segmentTotal - segmentSlotCount),
  )
  const segmentNodes = SEGMENT_NODE_LAYOUT.slice(0, segmentSlotCount).map(
    (layout, index) => {
      const nodeNumber = segmentSlotOffset + index + 1
      const isCleared = nodeNumber <= segmentCleared
      const isActive = nodeNumber === currentSlot && Boolean(state.currentNode)
      const status: SegmentStatus = isCleared ? 'cleared' : isActive ? 'active' : 'locked'
      return {
        ...layout,
        nodeNumber,
        status,
        stars: isCleared ? 3 : isActive ? activeNodeStars : 0,
      }
    },
  )
  const routeStep = Math.min(Math.max(1, currentSlot - segmentSlotOffset), Math.max(1, segmentNodes.length))
  const routeProgress = segmentNodes.length <= 1 ? 0 : Math.round(((routeStep - 1) / (segmentNodes.length - 1)) * 100)
  const canStart = energy > 0 && Boolean(state.currentNode)
  const notice = error ?? (!canStart ? '当前没有可挑战词关或体力不足。' : null)

  return (
    <section className="practice-game-map" aria-label="五维词关地图">
      <picture className="practice-game-map__main-art" aria-hidden="true">
        <source media="(max-width: 640px)" srcSet={gameAsset.map.backgrounds.mobile} />
        <source media="(max-width: 1100px)" srcSet={gameAsset.map.backgrounds.tablet} />
        <img src={gameAsset.map.backgrounds.desktop} alt="" />
      </picture>

      <div
        className="practice-game-map__route-layer"
        style={{ '--map-route-progress': `${routeProgress}` } as RouteStyle}
        aria-hidden="true"
      >
        <svg className="practice-game-map__route-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
          <path
            className="practice-game-map__route-shadow"
            d="M2 75 C14 68 24 71 35 65 C48 58 56 53 66 57 C78 62 84 51 91 44 C96 39 98 38 100 37"
          />
          <path
            className="practice-game-map__route-track"
            d="M2 75 C14 68 24 71 35 65 C48 58 56 53 66 57 C78 62 84 51 91 44 C96 39 98 38 100 37"
          />
          <path
            className="practice-game-map__route-progress"
            d="M2 75 C14 68 24 71 35 65 C48 58 56 53 66 57 C78 62 84 51 91 44 C96 39 98 38 100 37"
          />
        </svg>
      </div>

      <header className="practice-game-map__hud" aria-label="真实学习数据">
        <button
          type="button"
          className="practice-game-map__avatar"
          onClick={() => onBackToPlan?.()}
          aria-label="返回学习计划"
        >
          <span className="practice-game-map__avatar-frame">
            <img src={dynamicAsset.avatar} alt="" aria-hidden="true" />
          </span>
          <span className="practice-game-map__avatar-meta">
            <strong>Lv.{playerLevel}</strong>
            <span className="practice-game-map__avatar-level" aria-hidden="true">
              <span style={{ width: `${levelProgress}%` }} />
            </span>
          </span>
        </button>
        <span className="practice-game-map__counter is-energy" aria-label="体力">
          <img src={dynamicAsset.counters.energy} alt="" aria-hidden="true" />
          <strong>{energy}/{energyMax}</strong>
        </span>
        <span className="practice-game-map__counter is-coin" aria-label="金币">
          <img src={dynamicAsset.counters.coin} alt="" aria-hidden="true" />
          <strong>{formatCount(state.rewards.coins)}</strong>
        </span>
        <span className="practice-game-map__counter is-gem" aria-label="钻石">
          <img src={dynamicAsset.counters.gem} alt="" aria-hidden="true" />
          <strong>{formatCount(state.rewards.diamonds)}</strong>
        </span>
        <button type="button" className="practice-game-map__mail" aria-label={`站内信，${unreadMessages} 条未读`}>
          <img src={dynamicAsset.mailButton} alt="" aria-hidden="true" />
          {unreadMessages > 0 ? <strong>{formatCount(unreadMessages)}</strong> : null}
        </button>
      </header>

      <button type="button" className="practice-game-map__exit" onClick={() => onBackToPlan?.()} aria-label="退出地图">
        <img src={dynamicAsset.exitButton} alt="" aria-hidden="true" />
        <span className="sr-only">退出</span>
      </button>

      <div className="practice-game-map__title">
        <img className="practice-game-map__title-frame" src={dynamicAsset.titleScroll} alt="" aria-hidden="true" />
        <span className="practice-game-map__title-copy">
          <span className="practice-game-map__title-scope">{state.campaign.scopeLabel} · 第 {currentSegment}/{totalSegments} 段</span>
          <strong className="practice-game-map__title-heading">{state.segment.title}</strong>
        </span>
      </div>

      <section className="practice-game-map__progress" aria-label="词汇战役进度">
        <img className="practice-game-map__progress-frame" src={dynamicAsset.progressPanel} alt="" aria-hidden="true" />
        <div className="practice-game-map__progress-content">
          <div className="practice-game-map__progress-line">
            <span>总词量</span>
            <strong>{formatCount(passedWords)} / {formatCount(totalWords)}</strong>
          </div>
          <div className="practice-game-map__bar" aria-hidden="true">
            <span style={{ width: `${wordProgress}%` }} />
          </div>
          <div className="practice-game-map__progress-line">
            <span>当前分段</span>
            <strong>{currentSegment} / {totalSegments}</strong>
          </div>
          <div className="practice-game-map__bar is-segment" aria-hidden="true">
            <span style={{ width: `${segmentProgress}%` }} />
          </div>
        </div>
      </section>

      <div className="practice-game-map__segment-path" aria-label={`当前分段 ${segmentCleared}/${segmentTotal} 个词`}>
        {segmentNodes.map((node, index) => {
          return (
            <button
              key={node.nodeNumber}
              type="button"
              className={`practice-game-map__segment-node is-${node.status}`}
              style={{
                '--map-node-x': `${node.x}%`,
                '--map-node-y': `${node.y}%`,
                '--map-node-delay': `${index * 60}ms`,
              } as SegmentNodeStyle}
              onClick={onStart}
              disabled={node.status !== 'active' || !canStart || isStarting}
              aria-label={`进入第 ${node.nodeNumber} 个词，${SEGMENT_STATUS_LABEL[node.status]}，${node.stars} 星`}
            >
              <span className="practice-game-map__segment-node-glow" aria-hidden="true" />
              <span className="practice-game-map__segment-node-art" data-status={node.status}>
                <img
                  className="practice-game-map__segment-node-frame"
                  src={segmentBattleNodeAsset(node.status)}
                  alt=""
                  aria-hidden="true"
                />
                <span className="practice-game-map__segment-node-value">{node.nodeNumber}/{segmentTotal}</span>
                <span className="practice-game-map__segment-node-stars" aria-hidden="true">
                  {Array.from({ length: 3 }).map((_, starIndex) => (
                    <img
                      key={starIndex}
                      src={starIndex < node.stars ? dynamicAsset.starFull : dynamicAsset.starEmpty}
                      alt=""
                      aria-hidden="true"
                    />
                  ))}
                </span>
              </span>
              <span className="practice-game-map__segment-node-badge">{SEGMENT_STATUS_LABEL[node.status]}</span>
            </button>
          )
        })}
      </div>

      <div className="practice-game-map__reward-cover" aria-hidden="true">
        <img className="practice-game-map__reward-chest" src={dynamicAsset.treasureChestBase} alt="" />
        <img className="practice-game-map__reward-frame" src={dynamicAsset.treasureChest} alt="" />
        <strong>{segmentCleared}/{segmentTotal}</strong>
      </div>

      {notice ? <div className="practice-game-map__notice">{notice}</div> : null}
    </section>
  )
}
