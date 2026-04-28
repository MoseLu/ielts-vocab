import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const prdUiStyles = readFileSync(
  resolve(process.cwd(), 'src/styles/pages/practice/practice-game-prd-ui.scss'),
  'utf-8',
)
const templateStyles = readFileSync(
  resolve(process.cwd(), 'src/styles/pages/practice/practice-game-templates.scss'),
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

  it('does not override manifest-driven slot positions with positional selectors', () => {
    expect(templateStyles).not.toContain('nth-child')
    expect(templateStyles).not.toContain('!important')
    expect(templateStyles).toContain('.practice-template-slot')
    expect(templateStyles).toContain('left: var(--template-slot-left);')
    expect(templateStyles).toContain('top: var(--template-slot-top);')
    expect(templateStyles).toContain('left: var(--template-mobile-slot-left, var(--template-slot-left));')
    expect(templateStyles).toContain('.practice-template-debug--mobile')
    expect(templateStyles).toContain('object-fit: fill;')
  })

  it('centers template node words inside the plaque overlay', () => {
    const nodeArtBlock = templateStyles.match(/\.practice-game-map__segment-node-art\s*\{[^}]+\}/u)?.[0] ?? ''
    const labelBlock = templateStyles.match(/\.practice-game-map__segment-label\s*\{[^}]+\}/u)?.[0] ?? ''
    const labelTextBlock = templateStyles.match(
      /\.practice-game-map__segment-label strong\s*\{[^}]+\}/u,
    )?.[0] ?? ''
    const labelStatusBlock = templateStyles.match(
      /\.practice-game-map__segment-node-art small,\n\.practice-game-map__segment-label small\s*\{[^}]+\}/u,
    )?.[0] ?? ''

    expect(nodeArtBlock).toContain('display: none;')
    expect(templateStyles).toContain('width: var(--template-slot-width);')
    expect(templateStyles).toContain('height: var(--template-slot-height);')
    expect(labelBlock).toContain('overflow: hidden;')
    expect(labelBlock).toContain('display: flex;')
    expect(labelBlock).toContain('align-items: center;')
    expect(labelBlock).toContain('justify-content: center;')
    expect(labelBlock).toContain('line-height: 1;')
    expect(labelTextBlock).toContain('display: block;')
    expect(labelTextBlock).toContain('width: 100%;')
    expect(labelTextBlock).toContain('overflow: hidden;')
    expect(labelTextBlock).toContain('text-align: center;')
    expect(labelTextBlock).toContain('text-overflow: ellipsis;')
    expect(labelTextBlock).toContain('color: color-mix(in srgb, var(--surface-code) var(--mix-90), var(--warning));')
    expect(labelTextBlock).toContain('font-size: var(--map-label-font-size, clamp(var(--size-6), 1.05vw, var(--size-13)));')
    expect(labelTextBlock).toContain('font-weight: 900;')
    expect(labelTextBlock).toContain('letter-spacing: 0;')
    expect(labelTextBlock).not.toContain('translateY')
    expect(labelTextBlock).toContain('text-shadow:')
    expect(labelStatusBlock).toContain('display: none;')
  })

  it('centers live template text by controlling line boxes inside manifest slots', () => {
    const fieldBlock = templateStyles.match(
      /\.practice-game-map__template-field,[\s\S]+?\.practice-game-map__template-action\s*\{[^}]+\}/u,
    )?.[0] ?? ''
    const sideItemBlock = templateStyles.match(
      /\.practice-game-map__template-side-title,[\s\S]+?\.practice-game-map__template-side-item\s*\{[^}]+\}/u,
    )?.[0] ?? ''
    const sideTermBlock = templateStyles.match(
      /\.practice-game-map__template-side dt,[\s\S]+?\.practice-game-map__template-side dd\s*\{[^}]+\}/u,
    )?.[0] ?? ''
    const titleBlock = templateStyles.match(/\.practice-game-map__template-title\s*\{[^}]+\}/u)?.[0] ?? ''
    const actionSmallBlock = templateStyles.match(/\.practice-game-map__template-action small\s*\{[^}]+\}/u)?.[0] ?? ''
    const actionStrongBlock = templateStyles.match(/\.practice-game-map__template-action strong\s*\{[^}]+\}/u)?.[0] ?? ''
    const bottomBlock = templateStyles.match(/\.practice-game-map__template-bottom\s*\{[^}]+\}/u)?.[0] ?? ''

    expect(fieldBlock).toContain('place-items: center;')
    expect(fieldBlock).toContain('line-height: 1;')
    expect(titleBlock).toContain('align-content: center;')
    expect(sideItemBlock).toContain('align-content: center;')
    expect(sideItemBlock).toContain('justify-items: center;')
    expect(sideItemBlock).toContain('line-height: 1;')
    expect(templateStyles).toContain('gap: var(--size-4);')
    expect(templateStyles).toContain('padding: 0 var(--size-4);')
    expect(sideTermBlock).toContain('width: 100%;')
    expect(sideTermBlock).toContain('line-height: 1;')
    expect(templateStyles).toContain('font-size: clamp(var(--size-8), 0.75vw, var(--size-10));')
    expect(templateStyles).toContain('font-size: clamp(var(--size-10), 1vw, var(--size-13));')
    expect(actionSmallBlock).toContain('line-height: 1;')
    expect(actionStrongBlock).toContain('line-height: 1;')
    expect(bottomBlock).toContain('align-content: center;')
    expect(bottomBlock).toContain('justify-items: center;')
    expect(bottomBlock).toContain('text-align: center;')
  })
})
