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
})
