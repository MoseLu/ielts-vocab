import type { CSSProperties } from 'react'
import type { GameLevelKind } from '../../../../lib'
import { gameAsset } from './gameAssets'

function firstAssetUrl(primary?: string | null, fallback = ''): string {
  return typeof primary === 'string' && primary.trim() ? primary : fallback
}

type CounterKind = 'energy' | 'coin' | 'gem'

interface PrdMapHudSlotStyles {
  avatar?: CSSProperties
  energy?: CSSProperties
  coin?: CSSProperties
  gem?: CSSProperties
}

function formatCount(value: number): string {
  return Math.max(0, value).toLocaleString('zh-CN')
}

function counterIcon(kind: CounterKind): string {
  if (kind === 'energy') return gameAsset.reward.energy
  if (kind === 'coin') return gameAsset.reward.coin
  return gameAsset.reward.diamond
}

export function prdMapBackgroundForTheme(
  _themeId?: string | null,
  desktopMap?: string | null,
): string {
  return firstAssetUrl(desktopMap, gameAsset.map.backgrounds.desktop)
}

export function prdMobileMapBackgroundForTheme(
  _themeId?: string | null,
  mobileMap?: string | null,
  desktopMap?: string | null,
): string {
  return firstAssetUrl(mobileMap, firstAssetUrl(desktopMap, gameAsset.map.backgrounds.mobile))
}

export function prdSceneBackdropForKind(
  levelKind: GameLevelKind,
  variant: 'mission' | 'refill' = 'mission',
): string {
  if (variant === 'refill') return gameAsset.map.backgrounds.desktop
  return gameAsset.scenes[levelKind]
}

export function prdMobileSceneBackdrop(): string {
  return gameAsset.map.backgrounds.mobile
}

export function PrdMapHud({
  playerLevel,
  levelProgress,
  energy,
  energyMax,
  coins,
  diamonds,
  onBackToPlan,
  slotStyles,
}: {
  playerLevel: number
  levelProgress: number
  energy: number
  energyMax: number
  coins: number
  diamonds: number
  onBackToPlan?: () => void
  slotStyles?: PrdMapHudSlotStyles
}) {
  const counters = [
    { kind: 'energy' as const, label: '体力', value: `${energy}/${energyMax}`, style: slotStyles?.energy },
    { kind: 'coin' as const, label: '金币', value: formatCount(coins), style: slotStyles?.coin },
    { kind: 'gem' as const, label: '钻石', value: formatCount(diamonds), style: slotStyles?.gem },
  ]

  return (
    <header className="practice-game-map__hud practice-game-map__prd-hud" aria-label="真实学习数据">
      <button
        type="button"
        className="practice-game-map__prd-avatar"
        onClick={() => onBackToPlan?.()}
        aria-label="返回学习计划"
        data-layout-slot="map.hud.level"
        style={slotStyles?.avatar}
      >
        <span className="practice-game-map__prd-avatar-portrait">
          <img className="practice-game-map__prd-avatar-frame" src={gameAsset.ui.panelPurple} alt="" aria-hidden="true" />
          <img className="practice-game-map__prd-avatar-photo" src={gameAsset.character.robot} alt="" aria-hidden="true" />
        </span>
        <span className="practice-game-map__prd-avatar-level-pill">
          <img className="practice-game-map__prd-avatar-pill" src={gameAsset.ui.panelBlue} alt="" aria-hidden="true" />
          <strong>Lv.{playerLevel}</strong>
          <span className="practice-game-map__avatar-level" aria-hidden="true">
            <span style={{ width: `${levelProgress}%` }} />
          </span>
        </span>
      </button>
      {counters.map(counter => (
        <span
          key={counter.kind}
          className={`practice-game-map__prd-counter is-${counter.kind}`}
          aria-label={counter.label}
          data-layout-slot={`map.hud.${counter.kind === 'coin' ? 'coins' : counter.kind === 'gem' ? 'diamonds' : 'energy'}`}
          style={counter.style}
        >
          <img className="practice-game-map__prd-counter-frame" src={gameAsset.ui.panelBlue} alt="" aria-hidden="true" />
          <img className="practice-game-map__prd-counter-icon" src={counterIcon(counter.kind)} alt="" aria-hidden="true" />
          <strong>{counter.value}</strong>
        </span>
      ))}
    </header>
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
      aria-label={isStarting ? '进入中' : '开始当前词关'}
    >
      <img src={disabled ? gameAsset.ui.panelPurple : gameAsset.ui.buttonGreen} alt="" aria-hidden="true" />
      <span>{isStarting ? '进入中' : '开始当前词关'}</span>
    </button>
  )
}
