import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const baseStyles = readFileSync(resolve(process.cwd(), 'src/styles/base.scss'), 'utf-8')
const readRootLayerToken = (tokenName: string) => {
  const escapedName = tokenName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = baseStyles.match(new RegExp(`${escapedName}:\\s*(\\d+)`, 'u'))
  return Number(match?.[1] ?? 0)
}

describe('layer tokens', () => {
  it('keeps modal overlays above fixed chrome and floating topmost surfaces', () => {
    expect(readRootLayerToken('--layer-modal')).toBeGreaterThan(readRootLayerToken('--layer-header'))
    expect(readRootLayerToken('--layer-modal')).toBeGreaterThan(readRootLayerToken('--layer-topmost'))
  })
})
