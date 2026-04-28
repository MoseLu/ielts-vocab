import type { GameLevelKind } from '../../../../lib'
import { gameAsset } from './gameAssets'

function firstAssetUrl(primary?: string | null, fallback = ''): string {
  return typeof primary === 'string' && primary.trim() ? primary : fallback
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
