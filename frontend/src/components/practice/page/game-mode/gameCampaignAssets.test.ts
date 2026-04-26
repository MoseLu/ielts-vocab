import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const repoRoot = resolve(process.cwd(), '..')
const assetRoot = resolve(repoRoot, 'frontend/assets/game/campaign-v2')
const manifestPath = resolve(assetRoot, 'manifest.json')
const expectedThemeIds = [
  'study-campus',
  'work-business',
  'travel-transport',
  'city-services',
  'health-lifestyle',
  'environment-nature',
  'science-tech',
  'society-culture',
]
const expectedModeIds = ['spelling', 'pronunciation', 'definition', 'speaking', 'example']
const expectedSharedIds = [
  'energy-empty',
  'network-error',
  'scene-generating',
  'scene-failed',
  'recovery-empty',
  'locked',
]

type ManifestEntry = {
  path: string
  category: string
  themeId?: string
  modeId?: string
  variant?: string
  width: number
  height: number
}

describe('campaign-v2 static asset manifest', () => {
  it('covers theme, mobile, mode, and shared static assets', () => {
    expect(existsSync(manifestPath)).toBe(true)
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8')) as {
      version: string
      assets: ManifestEntry[]
    }

    expect(manifest.version).toBe('campaign-v2-static-v1')

    for (const themeId of expectedThemeIds) {
      const themeAssets = manifest.assets.filter(asset => asset.themeId === themeId)
      expect(themeAssets.some(asset => asset.variant === 'desktop-map' && asset.width >= 1920 && asset.height >= 1080)).toBe(true)
      expect(themeAssets.some(asset => asset.variant === 'mobile-map' && asset.width >= 1080 && asset.height >= 1920)).toBe(true)
      expect(themeAssets.some(asset => asset.variant === 'select-card')).toBe(true)
      expect(themeAssets.some(asset => asset.variant === 'empty-state')).toBe(true)
    }

    for (const modeId of expectedModeIds) {
      const modeAssets = manifest.assets.filter(asset => asset.modeId === modeId)
      expect(modeAssets.some(asset => asset.variant === 'stage-desktop')).toBe(true)
      expect(modeAssets.some(asset => asset.variant === 'stage-mobile')).toBe(true)
      expect(modeAssets.some(asset => asset.variant === 'mode-icon')).toBe(true)
      expect(modeAssets.some(asset => asset.variant === 'feedback-success')).toBe(true)
      expect(modeAssets.some(asset => asset.variant === 'feedback-failure')).toBe(true)
    }

    for (const sharedId of expectedSharedIds) {
      expect(manifest.assets.some(asset => asset.category === 'shared' && asset.variant === sharedId)).toBe(true)
    }

    for (const asset of manifest.assets) {
      expect(existsSync(resolve(assetRoot, asset.path))).toBe(true)
    }
  })
})
