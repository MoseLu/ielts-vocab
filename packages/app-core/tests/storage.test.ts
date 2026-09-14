import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  clearPracticeProgressSnapshot,
  createMemoryStorage,
  isUnfinishedPracticeProgressSnapshot,
  practiceProgressStorageKey,
  readJson,
  readPracticeProgressSnapshot,
  restorePracticeQueueFromSnapshot,
  scopedStorageKey,
  writeJson,
  writePracticeProgressSnapshot,
  type MobileWord,
} from '../src'

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

  it('stores unfinished practice snapshots by book and chapter scope', async () => {
    const storage = createMemoryStorage()
    const scope = { bookId: 'book-a', chapterId: 2 }

    assert.equal(practiceProgressStorageKey(scope), 'book-a:chapter:2')
    const snapshot = await writePracticeProgressSnapshot(
      storage,
      scope,
      {
        answeredWords: ['abandon'],
        correctCount: 1,
        currentIndex: 1,
        isCompleted: false,
        mode: 'quickmemory',
        queueWords: ['abandon', 'ability'],
        wordsLearned: 1,
        wrongCount: 0,
      },
      new Date('2026-06-03T00:00:00.000Z'),
    )

    assert.equal(snapshot.updatedAt, '2026-06-03T00:00:00.000Z')
    assert.equal(isUnfinishedPracticeProgressSnapshot(snapshot), true)
    assert.deepEqual(await readPracticeProgressSnapshot(storage, scope), snapshot)

    await clearPracticeProgressSnapshot(storage, scope)
    assert.equal(await readPracticeProgressSnapshot(storage, scope), null)
  })

  it('restores a saved queue prefix before remaining chapter words', () => {
    const queue = [
      word('ability'),
      word('abandon'),
      word('academy'),
    ]

    assert.deepEqual(
      restorePracticeQueueFromSnapshot(queue, { queueWords: ['abandon', 'ability'] }).map(item => item.word),
      ['abandon', 'ability', 'academy'],
    )
  })
})

function word(value: string): MobileWord {
  return {
    book_id: 'book-a',
    book_title: 'Book A',
    chapter_title: 'Chapter 1',
    definition: `${value} definition`,
    examples: [],
    group_key: 'chapter-1',
    listening_confusables: [],
    phonetic: '',
    pos: 'n.',
    word: value,
  }
}
