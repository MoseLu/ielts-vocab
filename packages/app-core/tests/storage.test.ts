import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { createMemoryStorage, readJson, scopedStorageKey, writeJson } from '../src'

describe('storage adapters', () => {
  it('scopes user-owned keys without changing global keys', () => {
    assert.equal(scopedStorageKey('wrong_words', 42), 'wrong_words:user:42')
    assert.equal(scopedStorageKey('wrong_words', null), 'wrong_words')
  })

  it('round-trips json and falls back on invalid payloads', async () => {
    const storage = createMemoryStorage({ broken: '{' })
    await writeJson(storage, 'settings', { volume: 80 })

    assert.deepEqual(await readJson(storage, 'settings', {}), { volume: 80 })
    assert.deepEqual(await readJson(storage, 'broken', { ok: true }), { ok: true })
  })
})
