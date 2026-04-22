import type { GameCampaignState } from '../../../../lib'
import { gameAsset } from './gameAssets'

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
      <div className="practice-game-result__medal">
        <img src={chestAsset} alt="" aria-hidden="true" />
        <strong>{score}</strong>
      </div>
      <div className="practice-game-result__copy">
        <span>{passed ? '通关成功' : '仍需补强'}</span>
        <h2>{title}</h2>
        <p>{passed ? '奖励已结算，下一段地图已准备好。' : '回流区会保留失手节点，补强后可以继续推进。'}</p>
      </div>
      <div className="practice-game-result__rewards">
        <span><img src={gameAsset.reward.coin} alt="" aria-hidden="true" />x{rewards.coins}</span>
        <span><img src={gameAsset.reward.diamond} alt="" aria-hidden="true" />x{rewards.diamonds}</span>
        <span><img src={gameAsset.reward.exp} alt="" aria-hidden="true" />x{rewards.exp}</span>
      </div>
      <div className="practice-game-result__actions">
        <button type="button" onClick={onContinue}>继续词关</button>
        <button type="button" className="is-secondary" onClick={onBackToMap}>回到地图</button>
      </div>
    </section>
  )
}
