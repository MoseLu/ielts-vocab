import React from 'react'
import { render, screen } from '@testing-library/react'
import PracticeControlBar from './PracticeControlBar'

describe('PracticeControlBar layout', () => {
  it('keeps the brand area on the left and packs error controls on the right', () => {
    const { container } = render(
      <PracticeControlBar
        mode="listening"
        currentDay={1}
        bookId={null}
        chapterId={null}
        errorMode={true}
        vocabularyLength={12}
        currentChapterTitle=""
        bookChapters={[]}
        showWordList={false}
        showPracticeSettings={false}
        onWordListToggle={() => {}}
        onSettingsToggle={() => {}}
        onModeChange={() => {}}
        onDayChange={() => {}}
        onNavigate={() => {}}
        onPause={() => {}}
      />,
    )

    expect(screen.getByText('雅思冲刺')).toBeInTheDocument()
    expect(container.querySelector('.practice-ctrl-brand')).not.toBeNull()
    expect(container.querySelector('.practice-ctrl-right .practice-ctx-label')).not.toBeNull()
  })
})
