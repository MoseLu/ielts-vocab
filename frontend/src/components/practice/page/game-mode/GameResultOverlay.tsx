import type { GameCampaignState } from '../../../../lib'
import { gameAsset } from './gameAssets'
import { GameTemplateDebugLayer } from './GameTemplateDebugLayer'
import { layoutSlotStyle } from './gameTemplateLayout'

export function GameResultOverlay({
  state,
  onContinue,
  onBackToMap,
}: {
  state: GameCampaignState
  onContinue: () => void
  onBackToMap: () => void
}) {
  const overlay = state.session?.resultOverlay
  const rewards = state.rewards ?? {
    coins: 0,
    diamonds: 0,
    exp: 0,
    stars: 0,
    chest: 'normal',
    bestHits: 0,
  }
  const title = typeof overlay?.title === 'string' ? overlay.title : '词关结算'
  const score = typeof overlay?.score === 'number' ? overlay.score : state.session?.score ?? 0
  const passed = Boolean(overlay?.passed ?? score >= (state.launcher?.passScore ?? 70))
  const chestAsset = rewards.chest === 'golden'
    ? gameAsset.reward.chestGolden
    : rewards.chest === 'sapphire'
      ? gameAsset.reward.chestSapphire
      : rewards.chest === 'special'
        ? gameAsset.reward.chestSpecial
        : gameAsset.reward.chestNormal

  return (
    <section className={`practice-game-result is-${passed ? 'passed' : 'pending'}`} aria-label="词关结算">
      <span className="practice-game-result__dim" aria-hidden="true" />
      <GameTemplateDebugLayer layoutId="stageSettlement" />
      <div
        className="practice-game-result__medal practice-template-slot"
        data-layout-slot="settlement.medal"
        style={layoutSlotStyle('stageSettlement', 'settlement.medal')}
      >
        <img className="practice-game-result__medal-chest" src={chestAsset} alt="" aria-hidden="true" />
        <strong>{score}</strong>
      </div>
      <div
        className="practice-game-result__copy practice-template-slot"
        data-layout-slot="settlement.copy"
        style={layoutSlotStyle('stageSettlement', 'settlement.copy')}
      >
        <span>{passed ? '通关成功' : '仍需补强'}</span>
        <h2>{title}</h2>
        <p>{passed ? '奖励已结算，下一段地图已准备好。' : '回流区会保留失手节点，补强后可以继续推进。'}</p>
      </div>
      <div
        className="practice-game-result__rewards practice-template-slot"
        data-layout-slot="settlement.rewards"
        style={layoutSlotStyle('stageSettlement', 'settlement.rewards')}
      >
        <span><img src={gameAsset.reward.coin} alt="" aria-hidden="true" />x{rewards.coins}</span>
        <span><img src={gameAsset.reward.diamond} alt="" aria-hidden="true" />x{rewards.diamonds}</span>
        <span><img src={gameAsset.reward.exp} alt="" aria-hidden="true" />x{rewards.exp}</span>
      </div>
      <div
        className="practice-game-result__actions practice-template-slot"
        data-layout-slot="settlement.actions"
        style={layoutSlotStyle('stageSettlement', 'settlement.actions')}
      >
        <button type="button" onClick={onContinue}>
          <span>继续词关</span>
        </button>
        <button type="button" className="is-secondary" onClick={onBackToMap}>
          <span>回到地图</span>
        </button>
      </div>
    </section>
  )
}
