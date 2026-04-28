import { describe, expect, it } from 'vitest'

import { prdTemplateAsset, prdUiAsset, prdUiAssetList } from './prdUiAssets'

describe('PRD magic UI assets', () => {
  it('serves map templates from the frontend asset base instead of legacy game assets', () => {
    expect(prdTemplateAsset('/ui/templates/word-chain-map-text-safe.png')).toBe(
      `${import.meta.env.BASE_URL}ui/templates/word-chain-map-text-safe.png?v=20260429-magic-ui-1`,
    )
    expect(prdUiAsset.templates.wordChainMap).toContain('/ui/templates/word-chain-map-text-safe.png')
    expect(prdUiAsset.templates.wordChainMap).not.toContain('/game/')
    expect(prdUiAssetList.every(path => path.startsWith(import.meta.env.BASE_URL))).toBe(true)
  })
})
