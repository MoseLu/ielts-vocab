import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { PracticePageQuickMemoryLayout } from './PracticePageStates'

vi.mock('../PracticeControlBar', () => ({
  default: ({ onWordListToggle }: { onWordListToggle: () => void }) => (
    <button type="button" onClick={onWordListToggle}>
      单词列表
    </button>
  ),
}))

vi.mock('../QuickMemoryMode', () => ({
  default: () => <div data-testid="quickmemory-mode">quickmemory-mode</div>,
}))

vi.mock('../../settings/SettingsPanel', () => ({
  default: () => null,
}))

function QuickMemoryLayoutHarness() {
  const [showWordList, setShowWordList] = useState(false)

  return (
    <PracticePageQuickMemoryLayout
      mode="quickmemory"
      currentDay={1}
      practiceBookId={null}
      practiceChapterId={null}
      errorMode={false}
      vocabulary={[
        { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' },
        { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta def' },
      ]}
      currentChapterTitle="艾宾浩斯复习"
      bookChapters={[]}
      showWordList={showWordList}
      showPracticeSettings={false}
      onWordListToggle={() => setShowWordList(value => !value)}
      onSettingsToggle={() => {}}
      onModeChange={() => {}}
      onDayChange={() => {}}
      navigate={vi.fn()}
      onExitHome={() => {}}
      queue={[0, 1]}
      queueIndex={1}
      wordStatuses={{ 0: 'correct', 1: 'wrong' }}
      settings={{}}
      reviewMode={false}
      reviewOffset={0}
      reviewHasMore={false}
      onWrongWord={() => {}}
      onQuickMemoryRecordChange={() => {}}
      onIndexChange={() => {}}
    />
  )
}

describe('PracticePageQuickMemoryLayout', () => {
  it('opens the word list panel in quick-memory mode', async () => {
    const user = userEvent.setup()
    const { container } = render(<QuickMemoryLayoutHarness />)

    expect(container.querySelector('.wordlist-panel.open')).toBeNull()

    await user.click(screen.getByRole('button', { name: '单词列表' }))

    expect(container.querySelector('.wordlist-panel.open')).not.toBeNull()
    expect(container.querySelector('.wordlist-backdrop')).not.toBeNull()
    expect(container.querySelector('.wordlist-item.current .wordlist-word')?.textContent).toBe('beta')
  })
})
