import type { GameCampaignNode, GameCampaignWord, GameLevelKind } from '../../../../lib'
import { BattleTopHud, ObjectivePanel, ThreatRoute } from './GameBattleHud'
import { prdMobileSceneBackdrop, prdSceneBackdropForKind } from './GamePrdUi'
import { GameTemplateDebugLayer } from './GameTemplateDebugLayer'
import { gameAsset } from './gameAssets'
import { type GameTemplateLayoutId, layoutSlotStyle, responsiveLayoutSlotStyle } from './gameTemplateLayout'
import {
  LEVEL_KIND_LABELS,
  getWaveNumber,
} from '../../../../features/practice/gameMode/gameData'

const WORD_DIMENSION_ITEMS: Array<{ kind: GameLevelKind; dimension: keyof GameCampaignWord['dimension_states'] }> = [
  { kind: 'speaking', dimension: 'recognition' },
  { kind: 'definition', dimension: 'meaning' },
  { kind: 'spelling', dimension: 'dictation' },
  { kind: 'pronunciation', dimension: 'speaking' },
  { kind: 'example', dimension: 'listening' },
]

export const MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT: Record<string, string> = {
  'mission.hud': 'mobileMission.hud', 'mission.route': 'mobileMission.route',
  'mission.objective': 'mobileMission.objective', 'mission.answerPanel': 'mobileMission.answerPanel',
  'refill.hud': 'mobileMission.hud', 'refill.list': 'mobileMission.route',
  'refill.objective': 'mobileMission.objective', 'refill.answerPanel': 'mobileMission.answerPanel',
}

export function missionSlotStyle(layoutId: GameTemplateLayoutId, slotId: string) {
  const mobileSlotId = MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT[slotId]
  if (!mobileSlotId) return layoutSlotStyle(layoutId, slotId)
  return responsiveLayoutSlotStyle(layoutId, slotId, 'mobileWordMission', mobileSlotId)
}

export function BattleBanner({
  tone,
  message,
}: {
  tone: 'success' | 'warning'
  message: string
}) {
  return <div className={`practice-game-mode__banner is-${tone}`}>{message}</div>
}

export function ChoiceGrid({
  choices,
  selectedChoice,
  onSelectChoice,
}: {
  choices: Array<{ key: string; label: string; meta: string; correct: boolean }>
  selectedChoice: string | null
  onSelectChoice: (value: string) => void
}) {
  return (
    <div className="practice-game-mode__choice-grid">
      {choices.map(choice => (
        <button
          key={choice.key}
          type="button"
          className={`practice-game-mode__choice${selectedChoice === choice.key ? ' is-selected' : ''}`}
          onClick={() => onSelectChoice(choice.key)}
        >
          <strong>{choice.label}</strong>
          <span>{choice.meta}</span>
        </button>
      ))}
    </div>
  )
}

export function DimensionDefenseStrip({
  word,
  activeKind,
}: {
  word: GameCampaignWord
  activeKind: GameLevelKind
}) {
  const completedCount = WORD_DIMENSION_ITEMS.filter(item => (
    (word.dimension_states[item.dimension]?.pass_streak ?? 0) >= 1
  )).length

  return (
    <section className="practice-game-mode__dimension-defense" aria-label="当前词五维防线">
      <div className="practice-game-mode__dimension-defense-head">
        <span>当前词五维防线</span>
        <strong>{completedCount}/5</strong>
      </div>
      <div className="practice-game-mode__dimension-defense-row">
        {WORD_DIMENSION_ITEMS.map(item => {
          const passStreak = word.dimension_states[item.dimension]?.pass_streak ?? 0
          const statusKey = item.kind === activeKind ? 'active' : passStreak >= 1 ? 'passed' : 'locked'
          const status = statusKey === 'active' ? '当前' : statusKey === 'passed' ? '已过' : '待解锁'
          return (
            <span key={item.kind} className={`practice-game-mode__dimension-chip is-${statusKey}`}>
              <span className="practice-game-mode__dimension-chip-core" aria-hidden="true" />
              <strong>{LEVEL_KIND_LABELS[item.kind]}</strong>
              <small>{status}</small>
            </span>
          )
        })}
      </div>
    </section>
  )
}

function sceneAssetForLevel(levelKind: GameLevelKind, variant: 'mission' | 'refill' = 'mission') {
  return prdSceneBackdropForKind(levelKind, variant)
}

export function WordScene({
  node,
  word,
  levelKind,
  layoutId,
  sceneVariant = 'mission',
  onExitToMap,
}: {
  node: GameCampaignNode
  word: GameCampaignWord
  levelKind: GameLevelKind
  layoutId: Extract<GameTemplateLayoutId, 'wordMission' | 'refillState'>
  sceneVariant?: 'mission' | 'refill'
  onExitToMap?: () => void
}) {
  const image = word.image
  const showSceneImage = image.status === 'ready' && Boolean(image.url)
  const [hudSlot, routeSlot, objectiveSlot] = layoutId === 'refillState'
    ? ['refill.hud', 'refill.list', 'refill.objective']
    : ['mission.hud', 'mission.route', 'mission.objective']

  return (
    <div className={`practice-game-mode__scene practice-game-mode__scene--${levelKind} is-${image.status}`}>
      <picture aria-hidden="true">
        <source media="(max-width: 640px)" srcSet={prdMobileSceneBackdrop()} />
        <img src={sceneAssetForLevel(levelKind, sceneVariant)} alt="" className="practice-game-mode__scene-backdrop" />
      </picture>
      <GameTemplateDebugLayer layoutId={layoutId} mobileLayoutId="mobileWordMission" />
      {showSceneImage ? <img src={image.url ?? undefined} alt={image.alt} className="practice-game-mode__scene-image" /> : null}
      <div className="practice-game-mode__scene-overlay" />
      <BattleTopHud
        node={node}
        word={word}
        levelKind={levelKind}
        onExitToMap={onExitToMap}
        slotId={hudSlot}
        mobileSlotId={MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT[hudSlot]}
        slotStyle={missionSlotStyle(layoutId, hudSlot)}
      />
      <ThreatRoute
        slotId={routeSlot}
        mobileSlotId={MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT[routeSlot]}
        slotStyle={missionSlotStyle(layoutId, routeSlot)}
      />
      <ObjectivePanel
        word={word}
        levelKind={levelKind}
        slotId={objectiveSlot}
        mobileSlotId={MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT[objectiveSlot]}
        slotStyle={missionSlotStyle(layoutId, objectiveSlot)}
      />
      <div className="practice-game-mode__coach-line">
        <img src={gameAsset.character.robot} alt="" aria-hidden="true" />
        <span>{image.status === 'ready' ? '图像情报已同步。' : image.status === 'failed' ? '图像情报缺失，使用基础战场。' : '图像情报生成中，先守住当前波。'}</span>
      </div>
      <div className="practice-game-mode__scene-caption">
        <strong>{word.definition}</strong>
        <span>{word.pos || 'IELTS vocabulary'} · {LEVEL_KIND_LABELS[levelKind]}</span>
      </div>
    </div>
  )
}

export function WordMissionWave({ word }: { word: GameCampaignWord }) {
  return <span className="practice-game-mode__sheet-wave">第 {getWaveNumber(word)}/4 波</span>
}
