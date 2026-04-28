import type { CSSProperties } from 'react'
import type { GameLevelKind } from '../../../../lib'
import { prdUiAsset } from './prdUiAssets'

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
  if (kind === 'energy') return prdUiAsset.hud.iconEnergy
  if (kind === 'coin') return prdUiAsset.hud.iconCoin
  return prdUiAsset.hud.iconGem
}

export function prdMapBackgroundForTheme(
  _themeId?: string | null,
  _desktopMap?: string | null,
): string {
  return prdUiAsset.templates.wordChainMap
}

export function prdMobileMapBackgroundForTheme(
  _themeId?: string | null,
  _mobileMap?: string | null,
  _desktopMap?: string | null,
): string {
  return prdUiAsset.templates.mobileWordChainMap
}

export function prdSceneBackdropForKind(
  _levelKind: GameLevelKind,
  variant: 'mission' | 'refill' = 'mission',
): string {
  return variant === 'refill' ? prdUiAsset.templates.refillState : prdUiAsset.templates.wordMission
}

export function prdMobileSceneBackdrop(): string {
  return prdUiAsset.templates.mobileWordMission
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
          <img className="practice-game-map__prd-avatar-frame" src={prdUiAsset.hud.avatarFrame} alt="" aria-hidden="true" />
          <img className="practice-game-map__prd-avatar-photo" src={prdUiAsset.icons.book} alt="" aria-hidden="true" />
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
        <span
          key={counter.kind}
          className={`practice-game-map__prd-counter is-${counter.kind}`}
          aria-label={counter.label}
          data-layout-slot={`map.hud.${counter.kind === 'coin' ? 'coins' : counter.kind === 'gem' ? 'diamonds' : 'energy'}`}
          style={counter.style}
        >
          <img className="practice-game-map__prd-counter-frame" src={prdUiAsset.hud.resourcePill} alt="" aria-hidden="true" />
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
      <img src={disabled ? prdUiAsset.buttons.disabled : prdUiAsset.buttons.green} alt="" aria-hidden="true" />
      <span>{isStarting ? '进入中' : '开始当前词关'}</span>
    </button>
  )
}
