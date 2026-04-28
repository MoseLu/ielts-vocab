import type { GameCampaignState, GameLevelCard, GameMapPathNode } from '../../../../lib'
import { prdMapBackgroundForTheme, prdMobileMapBackgroundForTheme } from './GamePrdUi'
import { GameTemplateDebugLayer } from './GameTemplateDebugLayer'
import { responsiveLayoutSlotStyle } from './gameTemplateLayout'

type SegmentSlotStyle = ReturnType<typeof responsiveLayoutSlotStyle> & {
  '--map-node-delay': string
}

type SegmentLabelStyle = SegmentSlotStyle & {
  '--map-label-scale': string
  '--map-label-font-size': string
}

const WORD_SLOT_IDS = [
  'map.word.1',
  'map.word.2',
  'map.word.3',
  'map.word.4',
  'map.word.5',
] as const

const DESKTOP_MAP_LAYOUT = 'wordChainMap'
const MOBILE_MAP_LAYOUT = 'mobileWordChainMap'

const SAMPLE_WORD_TITLES = ['language', 'context', 'evidence', 'analysis', 'structure'] as const

const DECORATIVE_LABEL_NODES = [
  { nodeKey: 'template:boss', title: 'Boss', slotId: 'map.boss', status: 'boss' },
  { nodeKey: 'template:refill', title: '回流', slotId: 'map.refill', status: 'refill' },
  { nodeKey: 'template:reward', title: '宝箱', slotId: 'map.reward', status: 'reward' },
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
  refill: 'refill',
  boss: 'boss',
  reward: 'cleared',
} as const

type MapNodeStatus = keyof typeof MAP_NODE_STATUS_LABEL

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

function nodeSlotId(node: GameMapPathNode, status: MapNodeStatus, wordIndex: number): string {
  if (status === 'boss' || node.nodeType === 'speaking_boss') return 'map.boss'
  if (status === 'reward' || node.nodeType === 'speaking_reward') return 'map.reward'
  return WORD_SLOT_IDS[Math.min(wordIndex, WORD_SLOT_IDS.length - 1)]
}

function segmentSlotStyle(slotId: string, index: number): SegmentSlotStyle {
  return {
    ...mapSlotStyle(slotId),
    '--map-node-delay': `${index * 60}ms`,
  }
}

function mapSlotStyle(slotId: string): ReturnType<typeof responsiveLayoutSlotStyle> {
  return responsiveLayoutSlotStyle(DESKTOP_MAP_LAYOUT, slotId, MOBILE_MAP_LAYOUT, slotId)
}

function labelWeight(text: string): number {
  return Array.from(text).reduce((total, char) => total + (/[\u4e00-\u9fff]/u.test(char) ? 1.7 : 1), 0)
}

function mapLabelScale(text: string): string {
  const weight = labelWeight(text)
  if (weight >= 24) return '0.68'
  if (weight >= 13) return '0.78'
  if (weight >= 10) return '0.86'
  return '1'
}

function mapLabelFontSize(text: string): string {
  const weight = labelWeight(text)
  if (weight >= 24) return 'clamp(var(--size-6), 0.55vw, var(--size-8))'
  if (weight >= 13) return 'clamp(var(--size-6), 0.8vw, var(--size-10))'
  if (weight >= 10) return 'clamp(var(--size-8), 0.9vw, var(--size-11))'
  return 'clamp(var(--size-6), 1.05vw, var(--size-13))'
}

function segmentLabelStyle(slotId: string, index: number, title: string): SegmentLabelStyle {
  return {
    ...segmentSlotStyle(slotId, index),
    '--map-label-scale': mapLabelScale(title),
    '--map-label-font-size': mapLabelFontSize(title),
  }
}

function compactTemplateNodeTitle(node: { slotId: string; title: string }): string {
  if (node.slotId === 'map.boss') return 'Boss'
  if (node.slotId === 'map.refill') return '回流'
  if (node.slotId === 'map.reward') return '宝箱'
  return node.title
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
  }
  const playerLevel = Math.max(1, hud.playerLevel)
  const levelProgress = Math.min(100, Math.max(0, hud.levelProgressPercent || segmentProgress))
  const currentSlot = Math.min(segmentTotal, segmentCleared + 1)
  const completedDimensions = levelCards.filter(card => card.status === 'passed').length
  const dimensionProgress = `${completedDimensions}/${Math.max(1, levelCards.length)}`
  const segmentSlotCount = Math.min(segmentTotal, WORD_SLOT_IDS.length)
  const segmentSlotOffset = Math.min(
    Math.max(0, currentSlot - Math.ceil(segmentSlotCount / 2)),
    Math.max(0, segmentTotal - segmentSlotCount),
  )
  const activeWord = state.currentNode?.word?.word ?? state.currentNode?.title ?? ''
  const segmentWordTitles = Array.from(new Set([
    ...(state.segment.words ?? []),
    activeWord,
    ...(state.currentNode?.targetWords ?? []),
    ...SAMPLE_WORD_TITLES,
  ].map(word => word.trim()).filter(Boolean)))
  const fallbackNodes: GameMapPathNode[] = WORD_SLOT_IDS.slice(0, segmentSlotCount).map((_, index) => {
    const nodeNumber = segmentSlotOffset + index + 1
    const isCleared = nodeNumber <= segmentCleared
    const isCurrent = nodeNumber === currentSlot && Boolean(state.currentNode)
    return {
      nodeType: 'word',
      nodeKey: `fallback:${nodeNumber}`,
      index: nodeNumber,
      title: segmentWordTitles[index] ?? SAMPLE_WORD_TITLES[index] ?? activeWord,
      subtitle: null,
      status: isCleared ? 'cleared' : isCurrent ? 'current' : 'locked',
      dimension: null,
      failedDimensions: [],
    }
  })
  const sourceNodes = state.mapPath?.nodes?.length ? state.mapPath.nodes : fallbackNodes
  let wordNodeIndex = 0
  const segmentNodes = sourceNodes.slice(0, WORD_SLOT_IDS.length + 3).map((node, index) => {
    const status = node.status as MapNodeStatus
    const slotId = nodeSlotId(node, status, wordNodeIndex)
    if (!['boss', 'reward'].includes(status)) wordNodeIndex += 1
    return {
      ...node,
      displayIndex: index + 1,
      slotId,
      status,
      statusClass: MAP_NODE_STATUS_CLASS[status],
      statusLabel: MAP_NODE_STATUS_LABEL[status],
    }
  })
  const usedTemplateSlots = new Set(segmentNodes.map(node => node.slotId))
  const labelNodes = [
    ...segmentNodes,
    ...DECORATIVE_LABEL_NODES
      .filter(node => !usedTemplateSlots.has(node.slotId))
      .map((node, index) => ({
        ...node,
        displayIndex: segmentNodes.length + index + 1,
        statusClass: MAP_NODE_STATUS_CLASS[node.status],
        statusLabel: MAP_NODE_STATUS_LABEL[node.status],
      })),
  ]
  const canStart = Boolean(state.currentNode)
  const notice = error ?? (!canStart ? '当前没有可挑战词关。' : null)
  const prdMapBackground = prdMapBackgroundForTheme(state.theme?.id ?? state.scope.themeId)
  const prdMobileMapBackground = prdMobileMapBackgroundForTheme(state.theme?.id ?? state.scope.themeId)
  const currentWord = activeWord || segmentNodes.find(node => node.status === 'current')?.title || '待选择'
  const bottomProgressLabel = [
    taskFocusLabel(state),
    `小段 ${currentSegment}/${totalSegments}`,
    `全链 ${formatCount(passedWords)}/${formatCount(totalWords)}`,
  ].join(' · ')

  return (
    <section className="practice-game-map" aria-label="五维词关地图">
      <div className="practice-game-map__board">
        <picture className="practice-game-map__main-art" aria-hidden="true">
          <source media="(max-width: 640px)" srcSet={prdMobileMapBackground} />
          <source media="(max-width: 1100px)" srcSet={prdMapBackground} />
          <img src={prdMapBackground} alt="" />
        </picture>
        <GameTemplateDebugLayer layoutId={DESKTOP_MAP_LAYOUT} mobileLayoutId={MOBILE_MAP_LAYOUT} />

        <header className="practice-game-map__template-hud" aria-label="真实学习数据">
          <button
            type="button"
            className="practice-game-map__template-field practice-game-map__template-avatar practice-template-slot"
            onClick={() => onBackToPlan?.()}
            aria-label="返回学习计划"
            data-layout-slot="map.hud.level"
            style={mapSlotStyle('map.hud.level')}
          >
            <strong>Lv.{playerLevel}</strong>
            <span style={{ width: `${levelProgress}%` }} />
          </button>
          <span
            className="practice-game-map__template-field practice-game-map__template-counter is-energy practice-template-slot"
            aria-label="体力"
            data-layout-slot="map.hud.energy"
            style={mapSlotStyle('map.hud.energy')}
          >
            {energy}/{energyMax}
          </span>
          <span
            className="practice-game-map__template-field practice-game-map__template-counter is-coin practice-template-slot"
            aria-label="金币"
            data-layout-slot="map.hud.coins"
            style={mapSlotStyle('map.hud.coins')}
          >
            {formatCount(state.rewards.coins)}
          </span>
          <span
            className="practice-game-map__template-field practice-game-map__template-counter is-gem practice-template-slot"
            aria-label="钻石"
            data-layout-slot="map.hud.diamonds"
            style={mapSlotStyle('map.hud.diamonds')}
          >
            {formatCount(state.rewards.diamonds)}
          </span>
        </header>

        <div
          className="practice-game-map__template-title practice-template-slot"
          aria-label="小段标题"
          data-layout-slot="map.title"
          style={mapSlotStyle('map.title')}
        >
          <span>当前 {segmentTotal} 词小段</span>
          <strong>第 {currentSegment} 小段 / 共 {totalSegments} 段</strong>
        </div>

        <section
          className="practice-game-map__template-side"
          aria-label="词汇战役进度"
        >
          <h2
            className="practice-game-map__template-side-title practice-template-slot"
            data-layout-slot="map.side.title"
            style={mapSlotStyle('map.side.title')}
          >
            小段情报
          </h2>
          <dl>
            <div
              className="practice-game-map__template-side-item practice-template-slot"
              aria-label="当前任务"
              data-layout-slot="map.side.task"
              style={mapSlotStyle('map.side.task')}
            >
              <dt>当前任务</dt>
              <dd>{taskFocusLabel(state)}</dd>
            </div>
            <div
              className="practice-game-map__template-side-item practice-template-slot"
              aria-label="当前词"
              data-layout-slot="map.side.word"
              style={mapSlotStyle('map.side.word')}
            >
              <dt>当前词</dt>
              <dd>{currentWord}</dd>
            </div>
            <div
              className="practice-game-map__template-side-item practice-template-slot"
              aria-label="小段进度"
              data-layout-slot="map.side.segment"
              style={mapSlotStyle('map.side.segment')}
            >
              <dt>小段进度</dt>
              <dd>{formatCount(segmentCleared)} / {formatCount(segmentTotal)} 词</dd>
            </div>
            <div
              className="practice-game-map__template-side-item practice-template-slot"
              aria-label="全链词汇进度"
              data-layout-slot="map.side.total"
              style={mapSlotStyle('map.side.total')}
            >
              <dt>全链词汇进度</dt>
              <dd>{formatCount(passedWords)} / {formatCount(totalWords)}</dd>
            </div>
            <div
              className="practice-game-map__template-side-item practice-game-map__template-side-item--compact practice-template-slot"
              aria-label="五维点亮"
              data-layout-slot="map.side.dimensions"
              style={mapSlotStyle('map.side.dimensions')}
            >
              <dt>五维点亮</dt>
              <dd>{dimensionProgress}</dd>
            </div>
          </dl>
          <div
            className="practice-game-map__template-side-bar practice-template-slot"
            data-layout-slot="map.side.progress"
            style={mapSlotStyle('map.side.progress')}
            aria-hidden="true"
          >
            <span style={{ width: `${wordProgress}%` }} />
          </div>
          <button
            type="button"
            className="practice-game-map__template-action practice-template-slot"
            onClick={onStart}
            disabled={!canStart || isStarting}
            aria-label={isStarting ? '进入中' : '进入当前词'}
            data-layout-slot="map.action"
            style={mapSlotStyle('map.action')}
          >
            <strong>{isStarting ? '进入中' : '进入当前词'}</strong>
          </button>
        </section>

        <div className="practice-game-map__segment-path">
          {segmentNodes.map((node, index) => (
            <span
              key={node.nodeKey}
              className={`practice-game-map__segment-node is-${node.statusClass}`}
              data-layout-slot={node.slotId}
              style={segmentSlotStyle(node.slotId, index)}
            >
              <span className="practice-game-map__segment-node-art" data-status={node.status} aria-hidden="true" />
            </span>
          ))}
          {labelNodes.map((node, index) => {
            const visibleTitle = compactTemplateNodeTitle(node)
            return (
              <span
                key={`${node.nodeKey}:label`}
                className="practice-game-map__segment-label practice-template-slot"
                data-slot={index + 1}
                data-layout-slot={node.slotId}
                title={node.title}
                style={segmentLabelStyle(node.slotId, index, visibleTitle)}
              >
                <strong>{visibleTitle}</strong>
                <small>{node.statusLabel}</small>
              </span>
            )
          })}
        </div>

        <div
          className="practice-game-map__template-bottom practice-game-map__template-bottom--word practice-template-slot"
          aria-label="底部当前词"
          data-layout-slot="map.bottom.word"
          title={currentWord}
          style={mapSlotStyle('map.bottom.word')}
        >
          {currentWord}
        </div>
        <div
          className="practice-game-map__template-bottom practice-game-map__template-bottom--progress practice-template-slot"
          aria-label="底部进度"
          data-layout-slot="map.bottom.progress"
          title={bottomProgressLabel}
          style={mapSlotStyle('map.bottom.progress')}
        >
          {bottomProgressLabel}
        </div>

        {notice ? <div className="practice-game-map__notice">{notice}</div> : null}
      </div>
    </section>
  )
}
