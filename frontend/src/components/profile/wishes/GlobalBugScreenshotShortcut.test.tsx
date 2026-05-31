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
}

async function captureWithShortcut(file: File) {
  vi.mocked(captureScreenAsPngFile).mockResolvedValueOnce(file)
  fireEvent.keyDown(window, { key: 'Z', shiftKey: true })
  await dragScreenshotSelection()
  await screen.findByRole('region', { name: '截图篮' })
}

describe('GlobalBugScreenshotShortcut', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    apiFetchMock.mockResolvedValue(wishesResponse)
    vi.mocked(captureScreenAsPngFile).mockReset()
    createObjectUrlMock.mockReset()
    revokeObjectUrlMock.mockReset()
    createObjectUrlMock.mockImplementation((file: File) => `blob:${file.name}`)
    Object.defineProperty(URL, 'createObjectURL', { value: createObjectUrlMock, configurable: true })
    Object.defineProperty(URL, 'revokeObjectURL', { value: revokeObjectUrlMock, configurable: true })
    Object.defineProperty(window, 'PointerEvent', { value: MouseEvent, configurable: true })
  })

  it('adds selected screenshots to the tray before opening the bug form', async () => {
    const screenshot = new File(['shot'], 'bug-screenshot-global.png', { type: 'image/png' })

    renderShortcut()
    await captureWithShortcut(screenshot)

    expect(await screen.findByRole('region', { name: '截图篮' })).toBeInTheDocument()
    expect(screen.getByText('截图 1/3')).toBeInTheDocument()
    expect(captureScreenAsPngFile).toHaveBeenCalledWith({ x: 20, y: 30, width: 180, height: 120 })
    expect(screen.getByAltText('截图 1')).toHaveAttribute('src', 'blob:bug-screenshot-global.png')

    fireEvent.click(screen.getByRole('button', { name: '提交反馈' }))

    expect(await screen.findByText('bug-screenshot-global.png')).toBeInTheDocument()
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith('/api/feature-wishes')
    })
  })

  it('keeps appending screenshots to the same tray up to three files', async () => {
    renderShortcut()
    await captureWithShortcut(new File(['one'], 'bug-1.png', { type: 'image/png' }))
    fireEvent.click(screen.getByRole('button', { name: '继续截图' }))
    vi.mocked(captureScreenAsPngFile).mockResolvedValueOnce(new File(['two'], 'bug-2.png', { type: 'image/png' }))
    await dragScreenshotSelection()
    await screen.findByText('截图 2/3')
    fireEvent.click(screen.getByRole('button', { name: '继续截图' }))
    vi.mocked(captureScreenAsPngFile).mockResolvedValueOnce(new File(['three'], 'bug-3.png', { type: 'image/png' }))
    await dragScreenshotSelection()

    await waitFor(() => {
      expect(screen.getByText('截图 3/3')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: '已满' })).toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: '提交反馈' }))

    expect(await screen.findByText('bug-1.png')).toBeInTheDocument()
    expect(screen.getByText('bug-2.png')).toBeInTheDocument()
    expect(screen.getByText('bug-3.png')).toBeInTheDocument()
  })

  it('allows deleting one screenshot and then capturing another', async () => {
    renderShortcut()
    await captureWithShortcut(new File(['one'], 'bug-delete.png', { type: 'image/png' }))

    fireEvent.click(screen.getByRole('button', { name: '删除截图：bug-delete.png' }))

    expect(screen.queryByRole('region', { name: '截图篮' })).not.toBeInTheDocument()
    expect(revokeObjectUrlMock).toHaveBeenCalledWith('blob:bug-delete.png')
    await captureWithShortcut(new File(['next'], 'bug-next.png', { type: 'image/png' }))
    expect(await screen.findByText('截图 1/3')).toBeInTheDocument()
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
