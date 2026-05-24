import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '../../../contexts'
import GlobalBugScreenshotShortcut from './GlobalBugScreenshotShortcut'
import { captureScreenAsPngFile } from './featureWishScreenshot'

const apiFetchMock = vi.fn()
const createObjectUrlMock = vi.fn()
const revokeObjectUrlMock = vi.fn()

vi.mock('../../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

vi.mock('./featureWishScreenshot', () => ({
  captureScreenAsPngFile: vi.fn(),
}))

const wishesResponse = {
  items: [],
  total: 0,
}

function renderShortcut() {
  return render(
    <ToastProvider>
      <GlobalBugScreenshotShortcut />
    </ToastProvider>,
  )
}

async function dragScreenshotSelection() {
  const selector = await screen.findByRole('dialog', { name: '选择截图区域' })
  fireEvent.pointerDown(selector, { clientX: 20, clientY: 30, pointerId: 1 })
  fireEvent.pointerMove(selector, { clientX: 200, clientY: 150, pointerId: 1 })
  fireEvent.pointerUp(selector, { clientX: 200, clientY: 150, pointerId: 1 })
  return selector
}

describe('GlobalBugScreenshotShortcut', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    apiFetchMock.mockResolvedValue(wishesResponse)
    vi.mocked(captureScreenAsPngFile).mockReset()
    createObjectUrlMock.mockReset()
    revokeObjectUrlMock.mockReset()
    createObjectUrlMock.mockReturnValue('blob:bug-screenshot')
    Object.defineProperty(URL, 'createObjectURL', { value: createObjectUrlMock, configurable: true })
    Object.defineProperty(URL, 'revokeObjectURL', { value: revokeObjectUrlMock, configurable: true })
    Object.defineProperty(window, 'PointerEvent', { value: MouseEvent, configurable: true })
  })

  it('previews a global shortcut screenshot before opening the bug form', async () => {
    const screenshot = new File(['shot'], 'bug-screenshot-global.png', { type: 'image/png' })
    vi.mocked(captureScreenAsPngFile).mockResolvedValue(screenshot)

    renderShortcut()
    fireEvent.keyDown(window, { key: 'Z', shiftKey: true })
    await dragScreenshotSelection()

    expect(await screen.findByRole('dialog', { name: '截图预览' })).toBeInTheDocument()
    expect(captureScreenAsPngFile).toHaveBeenCalledWith({ x: 20, y: 30, width: 180, height: 120 })
    expect(screen.getByAltText('Bug截图预览')).toHaveAttribute('src', 'blob:bug-screenshot')

    fireEvent.click(screen.getByRole('button', { name: '是' }))

    expect(await screen.findByText('bug-screenshot-global.png')).toBeInTheDocument()
    expect(revokeObjectUrlMock).toHaveBeenCalledWith('blob:bug-screenshot')
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/feature-wishes')
    })
  })

  it('closes the preview without creating a bug form when declined', async () => {
    const screenshot = new File(['shot'], 'bug-screenshot-declined.png', { type: 'image/png' })
    vi.mocked(captureScreenAsPngFile).mockResolvedValue(screenshot)

    renderShortcut()
    fireEvent.keyDown(window, { key: 'Z', shiftKey: true })
    await dragScreenshotSelection()
    await screen.findByRole('dialog', { name: '截图预览' })
    fireEvent.click(screen.getByRole('button', { name: '否' }))

    expect(screen.queryByRole('dialog', { name: '截图预览' })).not.toBeInTheDocument()
    expect(screen.queryByText('bug-screenshot-declined.png')).not.toBeInTheDocument()
    expect(revokeObjectUrlMock).toHaveBeenCalledWith('blob:bug-screenshot')
  })

  it('does not capture when shift z is typed into an editable field', () => {
    render(
      <ToastProvider>
        <input aria-label="feedback title" />
        <GlobalBugScreenshotShortcut />
      </ToastProvider>,
    )

    fireEvent.keyDown(screen.getByLabelText('feedback title'), { key: 'Z', shiftKey: true })

    expect(screen.queryByRole('dialog', { name: '选择截图区域' })).not.toBeInTheDocument()
    expect(captureScreenAsPngFile).not.toHaveBeenCalled()
  })

  it('cancels the selection overlay with escape before capturing', async () => {
    renderShortcut()

    fireEvent.keyDown(window, { key: 'Z', shiftKey: true })
    expect(await screen.findByRole('dialog', { name: '选择截图区域' })).toBeInTheDocument()
    fireEvent.keyDown(window, { key: 'Escape' })

    expect(screen.queryByRole('dialog', { name: '选择截图区域' })).not.toBeInTheDocument()
    expect(captureScreenAsPngFile).not.toHaveBeenCalled()
  })
})
