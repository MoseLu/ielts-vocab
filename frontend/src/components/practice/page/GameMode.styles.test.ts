import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import { gameAsset } from './game-mode/gameAssets'

const gameMapArtStyles = readFileSync(
  resolve(process.cwd(), 'src/styles/pages/practice/practice-game-map-art-ui.scss'),
  'utf-8',
)
const stylesDir = resolve(process.cwd(), 'src/styles')
const baseTokenStyles = readFileSync(resolve(stylesDir, 'base.tokens.scss'), 'utf-8')
const gameMapStyleFiles = readdirSync(resolve(stylesDir, 'pages/practice'))
  .filter(fileName => fileName.startsWith('practice-game-map') && fileName.endsWith('.scss'))
  .map(fileName => ({
    fileName,
    content: readFileSync(resolve(stylesDir, 'pages/practice', fileName), 'utf-8'),
  }))

describe('GameMode map style contract', () => {
  it('keeps the map title scroll symmetric and the copy centered', () => {
    expect(gameAsset.campaignDynamic.titleScroll).toBe('/game/campaign-dynamic/title_scroll_empty.png')
    const titleCopyBlock = gameMapArtStyles
      .match(/\.practice-game-map__title\s+\.practice-game-map__title-copy\s*\{[^}]+\}/u)?.[0] ?? ''
    const titleTextBlock = gameMapArtStyles
      .match(/\.practice-game-map__title\s+\.practice-game-map__title-scope,\s*\.practice-game-map__title\s+\.practice-game-map__title-heading\s*\{[^}]+\}/u)?.[0] ?? ''
    const titleScopeBlock = gameMapArtStyles
      .match(/\.practice-game-map__title\s+\.practice-game-map__title-scope\s*\{[^}]+\}/u)?.[0] ?? ''
    const titleHeadingBlock = gameMapArtStyles
      .match(/\.practice-game-map__title\s+\.practice-game-map__title-heading\s*\{\s*display:[^}]+\}/u)?.[0] ?? ''

    expect(titleCopyBlock).toContain('left: 50%;')
    expect(titleCopyBlock).toContain('display: grid;')
    expect(titleCopyBlock).toContain('max-width: none;')
    expect(titleCopyBlock).toContain('calc(-50% - var(--size-6))')
    expect(titleTextBlock).toContain('max-width: none;')
    expect(titleScopeBlock).toContain('font-size: var(--size-10);')
    expect(titleHeadingBlock).toContain('font-size: var(--size-24);')
  })

  it('uses defined size tokens for game map styles so art layers keep dimensions', () => {
    const definedSizeTokens = new Set(
      Array.from(baseTokenStyles.matchAll(/--size-\d+:/gu), match => match[0].slice(0, -1)),
    )
    const missingTokens = gameMapStyleFiles.flatMap(({ fileName, content }) => (
      Array.from(content.matchAll(/var\((--size-\d+)\)/gu), match => match[1])
        .filter(token => !definedSizeTokens.has(token))
        .map(token => `${fileName}:${token}`)
    ))

    expect(missingTokens).toEqual([])
  })
})
