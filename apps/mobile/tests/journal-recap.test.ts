import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'

const mobileRoot = new URL('..', import.meta.url).pathname
const workspaceRoot = join(mobileRoot, '..', '..')

function read(relativePath: string): string {
  return readFileSync(join(workspaceRoot, relativePath), 'utf8')
}

describe('mobile journal recap contract', () => {
  it('loads, edits, and saves today recap through the journal API', () => {
    const learnerApiSource = read('apps/mobile/src/api/learnerApi.ts')
    const journalSource = read('apps/mobile/src/screens/JournalScreen.tsx')
    const appCoreSchemaSource = read('packages/app-core/src/mobileSchemas.ts')

    assert.match(appCoreSchemaSource, /export const JournalEntrySchema/)
    assert.match(learnerApiSource, /export async function loadTodayJournalEntry/)
    assert.match(learnerApiSource, /\/api\/notes\/journal\/today/)
    assert.match(learnerApiSource, /export async function saveTodayJournalEntry/)
    assert.match(learnerApiSource, /\/api\/notes\/journal'/)
    assert.match(journalSource, /<Heading>今日复盘<\/Heading>/)
    assert.match(journalSource, /testID="journal\.recap"/)
    assert.match(journalSource, /testID="journal\.recap\.save"/)
    assert.match(journalSource, /loadTodayJournalEntry\(\)/)
    assert.match(journalSource, /saveTodayJournalEntry\(recapDraft\)/)
  })
})
