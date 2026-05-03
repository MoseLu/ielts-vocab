import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { createMemoryTokenStorage, MobileApiClient } from '../src'

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('MobileApiClient', () => {
  it('adds bearer tokens and retries once after refresh', async () => {
    const tokenStorage = createMemoryTokenStorage()
    await tokenStorage.setTokens({ accessToken: 'old-access', refreshToken: 'old-refresh' })
    const responses = [
      response({ error: 'expired' }, 401),
      response({
        access_token: 'new-access',
        refresh_token: 'new-refresh',
        token_type: 'Bearer',
        access_expires_in: 3600,
        refresh_expires_in: 2592000,
        user: { id: 1, username: 'mobile', email: '' },
      }),
      response({ ok: true }),
    ]
    const calls: Array<[RequestInfo | URL, RequestInit | undefined]> = []
    const fetchImpl = async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push([input, init])
      return responses.shift() ?? response({ ok: false }, 500)
    }
    const client = new MobileApiClient({
      baseUrl: 'https://axiomaticworld.com',
      fetchImpl: fetchImpl as typeof fetch,
      tokenStorage,
    })

    const result = await client.request('/api/books')

    assert.equal(result.status, 200)
    assert.equal(calls.length, 3)
    const firstCall = calls[0][1]
    const thirdCall = calls[2][1]
    assert.ok(firstCall)
    assert.ok(thirdCall)
    assert.equal((firstCall.headers as Headers).get('Authorization'), 'Bearer old-access')
    assert.equal((thirdCall.headers as Headers).get('Authorization'), 'Bearer new-access')
    assert.equal(await tokenStorage.getRefreshToken(), 'new-refresh')
  })

  it('returns parsed json and surfaces API errors', async () => {
    const tokenStorage = createMemoryTokenStorage()
    const responses = [
      response({ books: [] }),
      response({ error: 'bad request' }, 400),
    ]
    const client = new MobileApiClient({
      baseUrl: 'https://axiomaticworld.com',
      fetchImpl: (async () => responses.shift() ?? response({}, 500)) as typeof fetch,
      tokenStorage,
    })

    assert.deepEqual(await client.json('/api/books'), { books: [] })
    await assert.rejects(client.json('/api/books'), /bad request/)
  })
})
