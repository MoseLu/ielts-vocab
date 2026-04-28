import type { CSSProperties } from 'react'
import type { GameCampaignNode, GameCampaignWord, GameLevelKind } from '../../../../lib'
import {
  LEVEL_KIND_LABELS,
  NODE_STATUS_LABELS,
  NODE_TYPE_LABELS,
  getChallengeStep,
  getWaveNumber,
} from './gameData'

const LEVEL_TACTICS: Record<GameLevelKind, { tower: string; threat: string; objective: string }> = {
  definition: {
    tower: '语义哨塔',
    threat: '释义迷雾',
    objective: '锁定正确释义，清除这一波干扰。',
  },
  pronunciation: {
    tower: '声纹炮台',
    threat: '发音偏移',
    objective: '跟读目标词，让声纹命中判定区。',
  },
  speaking: {
    tower: '听辨雷达',
    threat: '音频诱饵',
    objective: '听准目标词，从干扰项里拦截正确答案。',
  },
  spelling: {
    tower: '字母炮塔',
    threat: '拼写气球',
    objective: '听音并输入完整拼写，击破当前目标。',
  },
  example: {
    tower: '语境核心',
    threat: '句意裂隙',
    objective: '把词放回句子语境，修复最后防线。',
  },
}

type TemplateSlotProps = {
  slotId?: string
  mobileSlotId?: string
  slotStyle?: CSSProperties
}

export function BattleTopHud({
  node,
  word,
  levelKind,
  onExitToMap,
  slotId,
  mobileSlotId,
  slotStyle,
}: {
  node: GameCampaignNode
  word: GameCampaignWord
  levelKind: GameLevelKind
  onExitToMap?: () => void
} & TemplateSlotProps) {
  const step = getChallengeStep(node)
  const wave = getWaveNumber(word)

  return (
    <header
      className={`practice-game-mode__battle-hud${slotId ? ' practice-template-slot' : ''}`}
      data-layout-slot={slotId}
      data-mobile-layout-slot={mobileSlotId}
      style={slotStyle}
    >
      {onExitToMap ? (
        <button type="button" className="practice-game-mode__battle-back" onClick={onExitToMap}>
          地图
        </button>
      ) : (
        <span className="practice-game-mode__battle-back is-static">IELTS</span>
      )}
      <div className="practice-game-mode__battle-status">
        <span>{LEVEL_TACTICS[levelKind].tower}</span>
        <strong>{step}/5</strong>
      </div>
      <div className="practice-game-mode__wave-meter" aria-label={`第 ${wave}/4 波`}>
        {Array.from({ length: 4 }, (_, index) => (
          <span key={index} className={index < wave ? 'is-lit' : undefined} />
        ))}
      </div>
    </header>
  )
}

export function BossTopHud({
  node,
  isBoss,
  onExitToMap,
  slotId,
  mobileSlotId,
  slotStyle,
}: {
  node: GameCampaignNode
  isBoss: boolean
  onExitToMap?: () => void
} & TemplateSlotProps) {
  return (
    <header
      className={`practice-game-mode__battle-hud${slotId ? ' practice-template-slot' : ''}`}
      data-layout-slot={slotId}
      data-mobile-layout-slot={mobileSlotId}
      style={slotStyle}
    >
      {onExitToMap ? (
        <button type="button" className="practice-game-mode__battle-back" onClick={onExitToMap}>
          地图
        </button>
      ) : null}
      <div className="practice-game-mode__battle-status">
        <span>{NODE_TYPE_LABELS[node.nodeType]}</span>
        <strong>{NODE_STATUS_LABELS[node.status]}</strong>
      </div>
      <div className="practice-game-mode__boss-health" aria-label={isBoss ? 'Boss 战' : '奖励关'}>
        <span />
      </div>
    </header>
  )
}

export function ThreatRoute({
  slotId,
  mobileSlotId,
  slotStyle,
}: {
} & TemplateSlotProps) {
  return (
    <div
      className={`practice-game-mode__threat-route${slotId ? ' practice-template-slot' : ''}`}
      data-layout-slot={slotId}
      data-mobile-layout-slot={mobileSlotId}
      style={slotStyle}
      aria-hidden="true"
    />
  )
}

export function ObjectivePanel({
  word,
  levelKind,
  slotId,
  mobileSlotId,
  slotStyle,
}: {
  word: GameCampaignWord
  levelKind: GameLevelKind
} & TemplateSlotProps) {
  return (
    <aside
      className={`practice-game-mode__objective-panel${slotId ? ' practice-template-slot' : ''}`}
      data-layout-slot={slotId}
      data-mobile-layout-slot={mobileSlotId}
      style={slotStyle}
    >
      <span>{LEVEL_TACTICS[levelKind].threat}</span>
      <strong>{levelKind === 'spelling' ? word.definition : word.word}</strong>
      {word.phonetic ? <small>{word.phonetic}</small> : null}
      <p>{LEVEL_TACTICS[levelKind].objective}</p>
    </aside>
  )
}
