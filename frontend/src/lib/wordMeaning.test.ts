import { describe, expect, it } from 'vitest'
import { parseWordMeaningGroups } from './wordMeaning'

describe('parseWordMeaningGroups', () => {
  it('splits mixed part-of-speech definitions into ordered groups', () => {
    expect(parseWordMeaningGroups({
      pos: 'v.',
      definition: '测试；试验；“test”的过去式和过去分词； adj. 经受过考验的；',
    })).toEqual([
      {
        posLabel: 'v.',
        meaningText: '测试；试验；“test”的过去式和过去分词',
      },
      {
        posLabel: 'adj.',
        meaningText: '经受过考验的',
      },
    ])
  })

  it('keeps a single compact group when the definition has no embedded part-of-speech labels', () => {
    expect(parseWordMeaningGroups({
      pos: 'prep.',
      definition: '没有；外面；外部',
    })).toEqual([
      {
        posLabel: 'prep.',
        meaningText: '没有；外面；外部',
      },
    ])
  })

  it('uses embedded labels even when the outer part of speech is empty', () => {
    expect(parseWordMeaningGroups({
      pos: '',
      definition: 'n. 记录；录制； v. 录音；录制',
    })).toEqual([
      {
        posLabel: 'n.',
        meaningText: '记录；录制',
      },
      {
        posLabel: 'v.',
        meaningText: '录音；录制',
      },
    ])
  })
})
