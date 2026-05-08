import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { CORE_STORAGE_KEYS, createMemoryStorage, createMemoryTokenStorage, MobileAuthClient } from '../src'

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('MobileAuthClient', () => {
  it('stores a WeChat mobile login session', async () => {
    const appStorage = createMemoryStorage()
    const tokenStorage = createMemoryTokenStorage()
    const calls: Array<[RequestInfo | URL, RequestInit | undefined]> = []
    const fetchImpl = async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push([input, init])
      return response({
        access_token: 'wechat-access',
        refresh_token: 'wechat-refresh',
        token_type: 'Bearer',
        access_expires_in: 3600,
        refresh_expires_in: 2592000,
        user: { id: 7, username: 'wechat_user', email: '' },
      })
    }
    const client = new MobileAuthClient({
      apiBaseUrl: 'https://axiomaticworld.com',
      appStorage,
      fetchImpl: fetchImpl as typeof fetch,
      tokenStorage,
    })

    const session = await client.wechatLogin('auth-code', 'state-1')

    assert.equal(session.user.username, 'wechat_user')
    assert.equal(await tokenStorage.getAccessToken(), 'wechat-access')
    assert.equal(await tokenStorage.getRefreshToken(), 'wechat-refresh')
    assert.equal(
      await appStorage.getItem(CORE_STORAGE_KEYS.authUser),
      JSON.stringify({ id: 7, username: 'wechat_user', email: '', is_admin: false }),
    )
    assert.equal(calls[0][0], 'https://axiomaticworld.com/api/auth/mobile/wechat-login')
    assert.equal(calls[0][1]?.body, JSON.stringify({ code: 'auth-code', state: 'state-1' }))
  })
})
