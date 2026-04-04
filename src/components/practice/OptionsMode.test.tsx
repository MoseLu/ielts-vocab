import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import OptionsMode from './OptionsMode'
import type { OptionItem, Word } from './types'

function makeWord(): Word {
  return {
    word: 'guy',
    phonetic: '/gaɪ/',
    pos: 'n.',
    definition: '家伙',
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
        previousWord={null}
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

    const revealedWords = Array.from(container.querySelectorAll('.option-word-reveal')).map(node => node.textContent)
    expect(revealedWords).toEqual(['guide', 'guy'])
    expect(screen.getByText('马上复盘这关的听音误差')).toBeInTheDocument()
    expect(screen.getByText('这一步干什么')).toBeInTheDocument()
  })
})
