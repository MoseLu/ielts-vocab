import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { apiBaseUrl, resolveMobileBaseUrls, speechBaseUrl } from '../src/config'

describe('mobile config', () => {
  it('uses production gateway by default', () => {
    assert.equal(apiBaseUrl, 'https://axiomaticworld.com')
    assert.equal(speechBaseUrl, 'https://axiomaticworld.com')
  })

  it('uses the local wifi host for dev builds', () => {
    const urls = resolveMobileBaseUrls({
      devHost: '192.168.1.4',
      environment: 'dev',
    })

    assert.equal(urls.apiBaseUrl, 'http://192.168.1.4:8000')
    assert.equal(urls.speechBaseUrl, 'http://192.168.1.4:5001')
  })
})
