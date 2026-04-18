import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
        onExitHome={() => {}}
      />,
    )

    expect(screen.getByText('雅思冲刺')).toBeInTheDocument()
    expect(container.querySelector('.practice-ctrl-brand')).not.toBeNull()
    expect(container.querySelector('.practice-ctrl-right .practice-ctx-label')).not.toBeNull()
  })

  it('shows the Ebbinghaus review label instead of Day undefined when no day is selected', () => {
    render(
      <PracticeControlBar
        mode="quickmemory"
        currentDay={undefined}
        bookId={null}
        chapterId={null}
        errorMode={false}
        vocabularyLength={12}
        currentChapterTitle="艾宾浩斯复习"
        bookChapters={[]}
        showWordList={false}
        showPracticeSettings={false}
        onWordListToggle={() => {}}
        onSettingsToggle={() => {}}
        onModeChange={() => {}}
        onDayChange={() => {}}
        onNavigate={() => {}}
        onExitHome={() => {}}
      />,
    )

    expect(screen.getByText('艾宾浩斯复习')).toBeInTheDocument()
    expect(screen.queryByText('Day undefined')).not.toBeInTheDocument()
  })

  it('exits directly to home when the home icon is clicked', async () => {
    const user = userEvent.setup()
    const onExitHome = vi.fn()

    render(
      <PracticeControlBar
        mode="quickmemory"
        currentDay={undefined}
        bookId={null}
        chapterId={null}
        errorMode={false}
        vocabularyLength={12}
        currentChapterTitle="艾宾浩斯复习"
        bookChapters={[]}
        showWordList={false}
        showPracticeSettings={false}
        onWordListToggle={() => {}}
        onSettingsToggle={() => {}}
        onModeChange={() => {}}
        onDayChange={() => {}}
        onNavigate={() => {}}
        onExitHome={onExitHome}
      />,
    )

    await user.click(screen.getByRole('button', { name: '返回主页' }))
    expect(onExitHome).toHaveBeenCalledTimes(1)
  })

  it('shows the selected chapter label and keeps the word-list toggle for classic practice', () => {
    render(
      <PracticeControlBar
        mode="listening"
        currentDay={undefined}
        bookId="ielts_reading_premium"
        chapterId="1"
        errorMode={false}
        vocabularyLength={12}
        currentChapterTitle="Chapter 1"
        bookChapters={[]}
        showWordList={false}
        showPracticeSettings={false}
        onWordListToggle={() => {}}
        onSettingsToggle={() => {}}
        onModeChange={() => {}}
        onDayChange={() => {}}
        onNavigate={() => {}}
        onExitHome={() => {}}
      />,
    )

    expect(screen.getByText('Chapter 1')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '单词列表' })).toBeInTheDocument()
  })
})
