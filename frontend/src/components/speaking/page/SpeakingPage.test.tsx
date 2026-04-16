import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import SpeakingPage from './SpeakingPage'

function renderPage(initialPath = '/speaking') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <SpeakingPage />
    </MemoryRouter>,
  )
}

describe('SpeakingPage', () => {
  it('starts with theme selection instead of the old instructional mock layout', () => {
    renderPage()

    expect(screen.getByRole('button', { name: /家乡与城市生活/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /学习与工作节奏/ })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '雅思口语模拟' })).not.toBeInTheDocument()
    expect(screen.queryByText('考试结构')).not.toBeInTheDocument()
    expect(screen.queryByText('考官关注点')).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Part 1' })).not.toBeInTheDocument()
  })

  it('opens the chosen theme directly on the first speaking question', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /家乡与城市生活/ }))

    expect(screen.getByText('Do you live in a big city or a small town?')).toBeInTheDocument()
    expect(screen.getByText('1 / 10')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '上一题' })).toBeDisabled()
    expect(screen.queryByText('Part 1')).not.toBeInTheDocument()
  })

  it('supports direct links into a selected theme and cue card step', async () => {
    const user = userEvent.setup()
    renderPage('/speaking?theme=city-life&step=5')

    expect(screen.getByText('Describe a place in your city where you like to spend time.')).toBeInTheDocument()
    expect(screen.getByText('1 分钟准备')).toBeInTheDocument()
    expect(screen.getByText('1-2 分钟作答')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '下一题' }))

    expect(screen.getByText('Why do some public places become popular with young people?')).toBeInTheDocument()
    expect(screen.getByText('7 / 10')).toBeInTheDocument()
  })

  it('lets the user return to the topic chooser and switch themes', async () => {
    const user = userEvent.setup()
    renderPage('/speaking?theme=city-life&step=0')

    await user.click(screen.getByRole('button', { name: '换题目' }))
    await user.click(screen.getByRole('button', { name: /学习与工作节奏/ }))

    expect(screen.getByText('Do you work or are you a student?')).toBeInTheDocument()
    expect(screen.getByText('1 / 10')).toBeInTheDocument()
  })
})
