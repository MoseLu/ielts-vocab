import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { apiBaseUrl } from '../src/config'

describe('mobile config', () => {
  it('uses production gateway by default', () => {
    assert.equal(apiBaseUrl, 'https://axiomaticworld.com')
  })
})
