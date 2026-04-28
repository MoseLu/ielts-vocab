import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { prdUiAsset, prdUiAssetList } from './prdUiAssets'

const repoRoot = resolve(process.cwd(), '..')
const assetRoot = resolve(repoRoot, 'frontend/assets/ui')
const manifestPath = resolve(assetRoot, 'manifest.json')

type UiManifestEntry = {
  path: string
  width: number
  height: number
  mode: string
}

function flattenAssetPaths(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (!value || typeof value !== 'object') return []
  return Object.values(value).flatMap(flattenAssetPaths)
}

describe('PRD UI asset map', () => {
  it('exposes every generated UI asset through frontend source paths', () => {
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8')) as {
      assetCount: number
      assets: UiManifestEntry[]
    }
    const expectedPaths = manifest.assets.map(asset => `/ui/${asset.path}`).sort()
    const actualPaths = flattenAssetPaths(prdUiAsset).sort()

    expect(manifest.assetCount).toBe(55)
    expect(prdUiAssetList.sort()).toEqual(expectedPaths)
    expect(actualPaths).toEqual(expectedPaths)
    for (const asset of manifest.assets) {
      expect(existsSync(resolve(assetRoot, asset.path))).toBe(true)
      expect(asset.width).toBeGreaterThan(0)
      expect(asset.height).toBeGreaterThan(0)
    }
  })
})
