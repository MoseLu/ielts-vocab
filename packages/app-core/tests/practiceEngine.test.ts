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
    assert.equal(buildWrongWordRecord(word, 'test').mistake_type, 'recognition')
    assert.equal(evaluatePracticeAnswer(word, 'test', 'known').correct, true)
    assert.equal(evaluatePracticeAnswer(word, 'test', 'unknown').correct, false)

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

  it('skips inflected distractors when building listening options', () => {
    const listeningWord: MobileWord = {
      ...word,
      word: 'guide',
      phonetic: '/gaid/',
      definition: '向导',
    }
    const options = buildPracticeOptions(listeningWord, [
      listeningWord,
      { ...word, word: 'guiding', definition: '引导；“guide”的现在分词' },
      { ...word, word: 'guided', definition: '有指导的；“guide”的过去式和过去分词' },
      { ...word, word: 'guides', definition: '向导；“guide”的复数' },
      { ...word, word: 'guy', phonetic: '/gai/', definition: '家伙' },
      { ...word, word: 'guise', phonetic: '/gaiz/', definition: '伪装' },
      { ...word, word: 'guile', phonetic: '/gail/', definition: '狡诈' },
      { ...word, word: 'guild', phonetic: '/gild/', definition: '协会' },
    ])

    assert.equal(options.length, 4)
    assert.ok(options.includes('向导'))
    assert.ok(options.includes('家伙'))
    assert.ok(options.includes('伪装'))
    assert.ok(options.includes('狡诈'))
    assert.ok(!options.includes('引导；“guide”的现在分词'))
    assert.ok(!options.includes('有指导的；“guide”的过去式和过去分词'))
    assert.ok(!options.includes('向导；“guide”的复数'))
    assert.ok(!options.includes('协会'))
  })
})
