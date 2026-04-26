import type { CSSProperties } from 'react'
import type { GameCampaignState, GameLevelCard, GameMapPathNode } from '../../../../lib'
import {
  PrdExitButton,
  PrdMapHud,
  PrdStartButton,
  prdMapBackgroundForTheme,
} from './GamePrdUi'
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

const MAP_NODE_STATUS_LABEL = {
  current: '当前',
  cleared: '已亮',
  locked: '待练',
  refill: '回流',
  boss: 'Boss',
  reward: '奖励',
} as const

const MAP_NODE_STATUS_CLASS = {
  current: 'active',
  cleared: 'cleared',
  locked: 'locked',
  refill: 'active',
  boss: 'active',
  reward: 'cleared',
} as const

type MapNodeStatus = keyof typeof MAP_NODE_STATUS_LABEL

const dynamicAsset = gameAsset.campaignDynamic

function formatCount(value: number): string {
  return Math.max(0, value).toLocaleString('zh-CN')
}

function progressPercent(done: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((done / total) * 100)))
}

function taskFocusLabel(state: GameCampaignState): string {
  const task = state.taskFocus?.task
  if (task === 'due-review') return '到期复习'
  if (task === 'error-review') return '错维回流'
  if (task === 'speaking') return '口语补练'
  if (task === 'add-book') return '添加词书'
  return '主线新词'
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
  onSelectThemeChapter?: (chapterId: string, page: number) => void
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
  const fallbackNodes: GameMapPathNode[] = SEGMENT_NODE_LAYOUT.slice(0, segmentSlotCount).map((_, index) => {
    const nodeNumber = segmentSlotOffset + index + 1
    const isCleared = nodeNumber <= segmentCleared
    const isCurrent = nodeNumber === currentSlot && Boolean(state.currentNode)
    return {
      nodeType: 'word',
      nodeKey: `fallback:${nodeNumber}`,
      index: nodeNumber,
      title: `词 ${nodeNumber}`,
      subtitle: null,
      status: isCleared ? 'cleared' : isCurrent ? 'current' : 'locked',
      dimension: null,
      failedDimensions: [],
    }
  })
  const sourceNodes = state.mapPath?.nodes?.length ? state.mapPath.nodes : fallbackNodes
  const segmentNodes = sourceNodes.slice(0, SEGMENT_NODE_LAYOUT.length).map(
    (node, index) => ({
      ...SEGMENT_NODE_LAYOUT[index],
      ...node,
      status: node.status as MapNodeStatus,
      statusClass: MAP_NODE_STATUS_CLASS[node.status as MapNodeStatus],
      statusLabel: MAP_NODE_STATUS_LABEL[node.status as MapNodeStatus],
      stars: node.status === 'cleared' ? 3 : node.status === 'current' ? activeNodeStars : 0,
    }),
  )
  const activeNodeIndex = Math.max(0, segmentNodes.findIndex(node => node.status === 'current'))
  const routeStep = Math.min(Math.max(1, activeNodeIndex + 1), Math.max(1, segmentNodes.length))
  const routeProgress = segmentNodes.length <= 1 ? 0 : Math.round(((routeStep - 1) / (segmentNodes.length - 1)) * 100)
  const canStart = Boolean(state.currentNode)
  const notice = error ?? (!canStart ? '当前没有可挑战词关。' : null)
  const prdMapBackground = prdMapBackgroundForTheme(state.theme?.id ?? state.scope.themeId)

  return (
    <section className="practice-game-map" aria-label="五维词关地图">
      <picture className="practice-game-map__main-art" aria-hidden="true">
        <source media="(max-width: 640px)" srcSet={prdMapBackground} />
        <source media="(max-width: 1100px)" srcSet={prdMapBackground} />
        <img src={prdMapBackground} alt="" />
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

      <PrdMapHud
        avatar={dynamicAsset.avatar}
        playerLevel={playerLevel}
        levelProgress={levelProgress}
        energy={energy}
        energyMax={energyMax}
        coins={state.rewards.coins}
        diamonds={state.rewards.diamonds}
        unreadMessages={unreadMessages}
        onBackToPlan={onBackToPlan}
      />

      <PrdExitButton onBackToPlan={onBackToPlan} />

      <div className="practice-game-map__title">
        <img className="practice-game-map__title-frame" src={dynamicAsset.titleScroll} alt="" aria-hidden="true" />
        <span className="practice-game-map__title-copy">
          <span className="practice-game-map__title-scope">词链防线地图</span>
          <strong className="practice-game-map__title-heading">当前词链 {currentSegment} / {totalSegments}</strong>
        </span>
      </div>

      <section className="practice-game-map__progress" aria-label="词汇战役进度">
        <div className="practice-game-map__progress-content">
          <div className="practice-game-map__progress-line">
            <span>词汇进度</span>
            <strong>{formatCount(passedWords)} / {formatCount(totalWords)}</strong>
          </div>
          <div className="practice-game-map__bar" aria-hidden="true">
            <span style={{ width: `${wordProgress}%` }} />
          </div>
          <div className="practice-game-map__progress-line">
            <span>词链进度</span>
            <strong>{currentSegment} / {totalSegments}</strong>
          </div>
          <div className="practice-game-map__bar is-segment" aria-hidden="true">
            <span style={{ width: `${segmentProgress}%` }} />
          </div>
          <div className="practice-game-map__progress-line">
            <span>当前任务</span>
            <strong>{taskFocusLabel(state)}</strong>
          </div>
        </div>
      </section>

      <div className="practice-game-map__segment-path">
        {segmentNodes.map((node, index) => {
          return (
            <span
              key={node.nodeKey}
              className={`practice-game-map__segment-node is-${node.statusClass}`}
              style={{
                '--map-node-x': `${node.x}%`,
                '--map-node-y': `${node.y}%`,
                '--map-node-delay': `${index * 60}ms`,
              } as SegmentNodeStyle}
            >
              <span className="practice-game-map__segment-node-glow" aria-hidden="true" />
              <span className="practice-game-map__segment-node-art" data-status={node.status}>
                <span className="practice-game-map__segment-node-ring" aria-hidden="true" />
                <span className="practice-game-map__segment-node-value">{node.index}</span>
                <span className="practice-game-map__segment-node-state">{node.title}</span>
                <span className="practice-game-map__segment-node-state">
                  {node.statusLabel}
                </span>
              </span>
            </span>
          )
        })}
      </div>

      <PrdStartButton
        canStart={canStart}
        isStarting={isStarting}
        onStart={onStart}
      />

      {notice ? <div className="practice-game-map__notice">{notice}</div> : null}
    </section>
  )
}
