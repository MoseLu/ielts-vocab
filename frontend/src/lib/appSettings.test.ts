import { describe, expect, it } from 'vitest'
import { normalizeAppSettings } from './appSettings'

describe('normalizeAppSettings', () => {
  it('defaults review batches to unlimited when the user has not customized the limit', () => {
    expect(
      normalizeAppSettings({
        reviewInterval: '3',
        reviewLimit: '100',
        reviewLimitCustomized: false,
      }),
    ).toMatchObject({
      reviewInterval: '3',
      reviewLimit: 'unlimited',
      reviewLimitCustomized: false,
    })
  })

  it('preserves an explicit review batch limit when the user customized it', () => {
    expect(
      normalizeAppSettings({
        reviewLimit: '50',
        reviewLimitCustomized: true,
      }),
    ).toMatchObject({
      reviewLimit: '50',
      reviewLimitCustomized: true,
    })
  })

  it('accepts a custom positive review batch limit', () => {
    expect(
      normalizeAppSettings({
        reviewLimit: '37',
        reviewLimitCustomized: true,
      }),
    ).toMatchObject({
      reviewLimit: '37',
      reviewLimitCustomized: true,
    })
  })

  it('defaults the global theme color to logo orange', () => {
    expect(normalizeAppSettings({ themeColor: 'pink' })).toMatchObject({
      themeColor: 'orange',
    })
  })

  it('preserves the alternate green theme color', () => {
    expect(normalizeAppSettings({ themeColor: 'green' })).toMatchObject({
      themeColor: 'green',
    })
  })

  it('accepts the macOS-style tag colors', () => {
    expect(normalizeAppSettings({ themeColor: 'purple' })).toMatchObject({
      themeColor: 'purple',
    })
  })
})
