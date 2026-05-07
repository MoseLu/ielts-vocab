import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  buildCsv,
  buildPracticeOptions,
  buildProgressSnapshot,
  buildQuickMemorySyncRecord,
  buildWrongWordRecord,
  evaluatePracticeAnswer,
  stripHtml,
  type MobileWord,
} from '../src'

const word: MobileWord = {
  word: 'Dynamic',
  definition: '动态的',
  phonetic: '/daɪˈnæmɪk/',
  pos: 'adj.',
  group_key: '',
  book_id: 'book-1',
  book_title: 'Book',
  chapter_id: 1,
  chapter_title: 'Chapter',
  examples: [],
  listening_confusables: [],
}

describe('mobile practice engine', () => {
  it('normalizes HTML prompts and spelling answers', () => {
    assert.equal(stripHtml('<p>Hello&nbsp;<strong>world</strong></p>'), 'Hello world')
    assert.equal(evaluatePracticeAnswer(word, 'meaning', ' dynamic ').correct, true)
    assert.equal(evaluatePracticeAnswer(word, 'dictation', 'dynamical').correct, false)
  })

  it('builds progress and sync payloads for answer flows', () => {
    const snapshot = buildProgressSnapshot({
      correctCount: 1,
      currentIndex: 1,
      queue: [word],
      wrongCount: 0,
    })
    assert.deepEqual(snapshot.answeredWords, ['Dynamic'])
    assert.equal(snapshot.isCompleted, true)

    const wrong = buildWrongWordRecord(word, 'listening')
    assert.equal(wrong.mistake_type, 'listening')

    const quick = buildQuickMemorySyncRecord(word, false, 1000)
    assert.equal(quick.unknownCount, 1)
    assert.equal(quick.bookId, 'book-1')
  })

  it('creates option and export helpers for mobile screens', () => {
    const options = buildPracticeOptions(word, [
      word,
      { ...word, word: 'Static', definition: '静态的' },
    ])
    assert.ok(options.includes('动态的'))
    assert.match(buildCsv([{ word: 'a,b', definition: '"quoted"' }]), /"a,b"/)
  })
})
