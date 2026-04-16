import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import PracticePronunciationButton from './PracticePronunciationButton'

const apiFetchMock = vi.fn()
const startRecordingMock = vi.fn(async () => {})
const stopRecordingMock = vi.fn()
let speechOptions: {
  onResult?: ((text: string) => void) | undefined
  onPartial?: ((text: string) => void) | undefined
  onError?: ((message: string) => void) | undefined
} = {}

vi.mock('../../../hooks/useSpeechRecognition', () => ({
  useSpeechRecognition: (options: typeof speechOptions) => {
    speechOptions = options
    return {
      isConnected: true,
      isRecording: false,
      isProcessing: false,
      startRecording: startRecordingMock,
      stopRecording: stopRecordingMock,
    }
  },
}))

vi.mock('../../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../../lib')>('../../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

describe('PracticePronunciationButton', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    startRecordingMock.mockClear()
    stopRecordingMock.mockClear()
    speechOptions = {}
  })

  it('keeps speaking practice inside the current page and submits pronunciation checks for the active word', async () => {
    const user = userEvent.setup()
    apiFetchMock.mockResolvedValue({
      word: 'dynamic',
      score: 88,
      passed: true,
      stress_feedback: '重音稳定',
      vowel_feedback: '元音清晰',
      speed_feedback: '节奏自然',
    })

    render(
      <PracticePronunciationButton
        bookId="ielts_reading_premium"
        chapterId="1"
        targetWord="dynamic"
        targetPhonetic="/daɪˈnæmɪk/"
      />,
    )

    expect(screen.queryByRole('link', { name: '单词发音练习' })).toBeNull()

    await user.click(screen.getByRole('button', { name: '单词发音练习' }))
    expect(screen.getByText('单词口语练习')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '开始跟读' }))
    expect(startRecordingMock).toHaveBeenCalledTimes(1)

    await act(async () => {
      speechOptions.onResult?.('Dynamic!')
    })

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/ai/pronunciation-check', {
        method: 'POST',
        body: JSON.stringify({
          word: 'dynamic',
          transcript: 'dynamic',
          bookId: 'ielts_reading_premium',
          chapterId: '1',
        }),
      })
    })

    expect(await screen.findByText('88')).toBeInTheDocument()
    expect(screen.getByText('匹配成功，dynamic 发音通过。')).toBeInTheDocument()
  })
})
