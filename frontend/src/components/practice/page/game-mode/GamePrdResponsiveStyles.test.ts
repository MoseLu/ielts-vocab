import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const prdUiStyles = readFileSync(
  resolve(process.cwd(), 'src/styles/pages/practice/practice-game-prd-ui.scss'),
  'utf-8',
)

describe('PRD game map responsive styles', () => {
  it('resets inherited mobile bounds on the progress panel', () => {
    const progressBlock = prdUiStyles.match(/\.practice-game-map__progress\s*\{[^}]+\}/u)?.[0] ?? ''

    expect(progressBlock).toContain('right: auto;')
    expect(progressBlock).toContain('bottom: auto;')
  })

  it('uses tokenized compact map chrome below tablet width', () => {
    const mobileBlock = prdUiStyles.match(/@media \(max-width: 820px\)\s*\{[\s\S]+\n\}/u)?.[0] ?? ''

    expect(prdUiStyles).toContain('.practice-game-mode--map')
    expect(prdUiStyles).toContain('padding: 0;')
    expect(prdUiStyles).toContain('width: 100vw;')
    expect(prdUiStyles).toContain('height: 100vh;')
    expect(prdUiStyles).toContain('border-radius: 0;')
    expect(mobileBlock).toContain('.practice-game-map')
    expect(mobileBlock).toContain('min-height: 100vh;')
    expect(mobileBlock).toContain('.practice-game-map__prd-hud')
    expect(mobileBlock).toContain('right: auto;')
    expect(mobileBlock).toContain('grid-template-columns: var(--size-72);')
    expect(mobileBlock).toContain('flex-wrap: nowrap;')
    expect(mobileBlock).toContain('.practice-game-map__prd-avatar')
    expect(mobileBlock).toContain('width: var(--size-72);')
    expect(mobileBlock).toContain('.practice-game-map__prd-avatar-level-pill')
    expect(mobileBlock).toContain('left: var(--size-24);')
    expect(mobileBlock).toContain('.practice-game-map__title')
    expect(mobileBlock).toContain('top: var(--size-104);')
    expect(mobileBlock).toContain('.practice-game-map__progress')
    expect(mobileBlock).toContain('display: none;')
    expect(mobileBlock).toContain('.practice-game-map__segment-path')
    expect(mobileBlock).toContain('pointer-events: none;')
  })
})
