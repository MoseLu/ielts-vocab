import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import OptionsMode from './OptionsMode'
import type { OptionItem, Word } from './types'

const playExampleAudioMock = vi.fn()

vi.mock('./utils', async () => {
  const actual = await vi.importActual<typeof import('./utils')>('./utils')
  return {
    ...actual,
    playExampleAudio: (...args: unknown[]) => playExampleAudioMock(...args),
  }
})

function makeWord(): Word {
  return {
    word: 'guy',
    phonetic: '/gaɪ/',
    pos: 'n.',
    definition: '家伙',
  }
}

function makeWordWithExample(word: string, phonetic: string, definition: string, example: string): Word {
  return {
    word,
    phonetic,
    pos: 'n.',
    definition,
    examples: [{ en: example, zh: '' }],
  }
}

function makeDefinitionOption(word: string, pos: string, definition: string): OptionItem {
  return {
    word,
    pos,
    definition,
    display_mode: 'definition',
  }
}

describe('OptionsMode listening feedback', () => {
  it('reveals the clicked word and simplifies part-of-speech labels in listening mode', () => {
    const { container } = render(
      <OptionsMode
        currentWord={makeWord()}
        previousWord={{ ...makeWord(), word: 'rate', phonetic: '/reɪt/', definition: '率；速度；比率；价格；费用；' }}
        lastState={null}
        mode="listening"
        options={[
          makeDefinitionOption('guide', 'vt.', '向导'),
          makeDefinitionOption('guy', 'n.', '家伙'),
          makeDefinitionOption('quietly', 'adv.', '安静地'),
          makeDefinitionOption('quick', 'adj.', '快的'),
        ]}
        selectedAnswer={0}
        wrongSelections={[0]}
        showResult
        correctIndex={1}
        spellingInput=""
        spellingResult={null}
        speechConnected
        speechRecording={false}
        settings={{}}
        progressValue={0.25}
        total={4}
        queueIndex={0}
        onOptionSelect={vi.fn()}
        onSkip={vi.fn()}
        onGoBack={vi.fn()}
        onSpellingSubmit={vi.fn()}
        onSpellingInputChange={vi.fn()}
        onStartRecording={vi.fn()}
        onStopRecording={vi.fn()}
        onPlayWord={vi.fn()}
      />,
    )

    const posLabels = Array.from(container.querySelectorAll('.option-pos')).map(node => node.textContent)
    expect(posLabels).toEqual(['v', 'n', 'adv', 'adj'])
    expect(container.querySelector('.prev-word-inline--choice')).not.toBeNull()

    const revealedWords = Array.from(container.querySelectorAll('.option-word-reveal')).map(node => node.textContent)
    expect(revealedWords).toEqual(['guide', 'guy'])
    expect(container.querySelector('.play-btn-large')).toBeNull()
    expect(screen.getByLabelText('再读一遍，快捷键 Tab')).toBeInTheDocument()
    expect(screen.queryByText('马上复盘这关的听音误差')).not.toBeInTheDocument()
    expect(screen.queryByText('这一步干什么')).not.toBeInTheDocument()
  })

  it('shows a blanked example sentence when the listening word includes an example', () => {
    const { container } = render(
      <OptionsMode
        currentWord={makeWordWithExample('two', '/tuː/', '二', 'He adds two and three to get five.')}
        previousWord={null}
        lastState={null}
        mode="listening"
        options={[
          makeDefinitionOption('two', 'num.', '二'),
          { ...makeDefinitionOption('too', 'adv.', '也；太'), phonetic: '/tuː/' },
          { ...makeDefinitionOption('tow', 'v.', '拖；拉'), phonetic: '/təʊ/' },
          { ...makeDefinitionOption('team', 'n.', '团队'), phonetic: '/tiːm/' },
        ]}
        selectedAnswer={null}
        wrongSelections={[]}
        showResult={false}
        correctIndex={0}
        spellingInput=""
        spellingResult={null}
        speechConnected
        speechRecording={false}
        settings={{}}
        progressValue={0.25}
        total={4}
        queueIndex={0}
        onOptionSelect={vi.fn()}
        onSkip={vi.fn()}
        onGoBack={vi.fn()}
        onSpellingSubmit={vi.fn()}
        onSpellingInputChange={vi.fn()}
        onStartRecording={vi.fn()}
        onStopRecording={vi.fn()}
        onPlayWord={vi.fn()}
      />,
    )

    const sentence = container.querySelector('.listening-example-sentence')
    expect(sentence?.textContent).toContain('He adds')
    expect(sentence?.textContent).toContain('and three to get five.')
    expect(sentence?.textContent).not.toContain('two')
    expect(container.querySelectorAll('.example-blank-segment')).toHaveLength(1)
  })

  it('plays example audio from the listening prompt when requested', () => {
    render(
      <OptionsMode
        currentWord={makeWordWithExample('two', '/tuː/', '二', 'He adds two and three to get five.')}
        previousWord={null}
        lastState={null}
        mode="listening"
        options={[
          makeDefinitionOption('two', 'num.', '二'),
          { ...makeDefinitionOption('too', 'adv.', '也；太'), phonetic: '/tuː/' },
          { ...makeDefinitionOption('tow', 'v.', '拖；拉'), phonetic: '/təʊ/' },
          { ...makeDefinitionOption('team', 'n.', '团队'), phonetic: '/tiːm/' },
        ]}
        selectedAnswer={null}
        wrongSelections={[]}
        showResult={false}
        correctIndex={0}
        spellingInput=""
        spellingResult={null}
        speechConnected
        speechRecording={false}
        settings={{ playbackSpeed: '0.9', volume: '70' }}
        progressValue={0.25}
        total={4}
        queueIndex={0}
        onOptionSelect={vi.fn()}
        onSkip={vi.fn()}
        onGoBack={vi.fn()}
        onSpellingSubmit={vi.fn()}
        onSpellingInputChange={vi.fn()}
        onStartRecording={vi.fn()}
        onStopRecording={vi.fn()}
        onPlayWord={vi.fn()}
      />,
    )

    screen.getByRole('button', { name: '播放例句' }).click()

    expect(playExampleAudioMock).toHaveBeenCalledWith(
      'He adds two and three to get five.',
      'two',
      { playbackSpeed: '0.9', volume: '70' },
    )
  })

  it('keeps the listening prompt hidden when the listening word has no example', () => {
    const { container } = render(
      <OptionsMode
        currentWord={makeWord()}
        previousWord={null}
        lastState={null}
        mode="listening"
        options={[
          { ...makeDefinitionOption('guide', 'n.', '向导'), phonetic: '/ɡaɪd/' },
          { ...makeDefinitionOption('guy', 'n.', '家伙'), phonetic: '/ɡaɪ/' },
          { ...makeDefinitionOption('guise', 'n.', '伪装'), phonetic: '/ɡaɪz/' },
          { ...makeDefinitionOption('guild', 'n.', '协会'), phonetic: '/ɡɪld/' },
        ]}
        selectedAnswer={null}
        wrongSelections={[]}
        showResult={false}
        correctIndex={0}
        spellingInput=""
        spellingResult={null}
        speechConnected
        speechRecording={false}
        settings={{}}
        progressValue={0.25}
        total={4}
        queueIndex={0}
        onOptionSelect={vi.fn()}
        onSkip={vi.fn()}
        onGoBack={vi.fn()}
        onSpellingSubmit={vi.fn()}
        onSpellingInputChange={vi.fn()}
        onStartRecording={vi.fn()}
        onStopRecording={vi.fn()}
        onPlayWord={vi.fn()}
      />,
    )

    expect(container.querySelector('.listening-example-sentence')).toBeNull()
  })

  it('uses the shared problem-type labels on smart mode badges', () => {
    render(
      <OptionsMode
        currentWord={makeWord()}
        previousWord={null}
        lastState={null}
        mode="smart"
        smartDimension="meaning"
        options={[]}
        selectedAnswer={null}
        wrongSelections={[]}
        showResult={false}
        correctIndex={0}
        spellingInput=""
        spellingResult={null}
        speechConnected
        speechRecording={false}
        settings={{}}
        progressValue={0.25}
        total={4}
        queueIndex={0}
        onOptionSelect={vi.fn()}
        onSkip={vi.fn()}
        onGoBack={vi.fn()}
        onSpellingSubmit={vi.fn()}
        onSpellingInputChange={vi.fn()}
        onStartRecording={vi.fn()}
        onStopRecording={vi.fn()}
        onPlayWord={vi.fn()}
      />,
    )

    expect(screen.getByText('默写模式')).toBeInTheDocument()
  })
})
