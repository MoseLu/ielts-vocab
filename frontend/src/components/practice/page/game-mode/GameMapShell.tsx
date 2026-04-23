import type { CSSProperties } from 'react'
import type { GameCampaignState, GameLevelCard } from '../../../../lib'
import { gameAsset } from './gameAssets'

type MapHotspotStyle = CSSProperties & {
  '--map-hotspot-x': string
  '--map-hotspot-y': string
}

const MAP_HOTSPOTS = [
  { x: 18, y: 66 },
  { x: 38, y: 60 },
  { x: 56, y: 55 },
  { x: 72, y: 54 },
  { x: 88, y: 40 },
]

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
  const canStart = energy > 0 && Boolean(state.currentNode)

  return (
    <section className="practice-game-map" aria-label="五维词关地图">
      <picture className="practice-game-map__main-art">
        <source media="(max-width: 640px)" srcSet={gameAsset.map.backgrounds.mobile} />
        <source media="(max-width: 1100px)" srcSet={gameAsset.map.backgrounds.tablet} />
        <img src={gameAsset.map.backgrounds.desktop} alt="五维词关地图" />
      </picture>

      <button
        type="button"
        className="practice-game-map__plan-hotspot"
        onClick={() => onBackToPlan?.()}
        aria-label="返回学习计划"
      />

      <div className="practice-game-map__hotspots" aria-label="地图关卡入口">
        {levelCards.map((card, index) => {
          const position = MAP_HOTSPOTS[index] ?? MAP_HOTSPOTS[0]
          return (
            <button
              key={card.kind}
              type="button"
              className={`practice-game-map__hotspot is-${card.status}`}
              style={{
                '--map-hotspot-x': `${position.x}%`,
                '--map-hotspot-y': `${position.y}%`,
              } satisfies MapHotspotStyle}
              onClick={onStart}
              disabled={!canStart || isStarting}
              aria-label={`进入 ${card.step}/5 ${card.label}`}
            />
          )
        })}
      </div>

      <button
        type="button"
        className="practice-game-map__chest"
        onClick={onStart}
        disabled={!canStart || isStarting}
        aria-label={isStarting ? '正在进入词关' : '进入当前词关'}
      />

      {error ? <div className="practice-game-map__notice">{error}</div> : null}
      {!canStart ? <div className="practice-game-map__notice">当前没有可挑战词关或体力不足。</div> : null}
    </section>
  )
}
