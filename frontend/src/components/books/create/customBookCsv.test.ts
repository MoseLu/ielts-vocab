import { describe, expect, it } from 'vitest'
import { parseCustomBookCsv } from './customBookCsv'

describe('parseCustomBookCsv', () => {
  it('groups rows by chapter columns and maps common word fields', () => {
    const chapters = parseCustomBookCsv(
      'chapter,word,phonetic,pos,definition\nUnit 1,abandon,/əˈbændən/,v.,放弃\nUnit 2,ability,/əˈbɪləti/,n.,能力',
      15,
    )

    expect(chapters).toHaveLength(2)
    expect(chapters[0].title).toBe('Unit 1')
    expect(chapters[0].entries[0]).toEqual({
      word: 'abandon',
      phonetic: '/əˈbændən/',
      pos: 'v.',
      definition: '放弃',
    })
    expect(chapters[1].entries[0].word).toBe('ability')
  })

  it('chunks single-column CSV rows by chapter word target', () => {
    const chapters = parseCustomBookCsv('abandon\nability\nabsorb', 2)

    expect(chapters).toHaveLength(2)
    expect(chapters[0].entries.map(entry => entry.word)).toEqual(['abandon', 'ability'])
    expect(chapters[1].entries.map(entry => entry.word)).toEqual(['absorb'])
  })
})
