import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { act } from 'react'
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

function deferredFile(file: File) {
  let resolveFile: (value: File) => void = () => {}
  const promise = new Promise<File>(resolve => {
    resolveFile = resolve
  })
  return {
    promise,
    resolve: () => resolveFile(file),
  }
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

  it('allows dragging the screenshot tray to a new viewport position', async () => {
    renderShortcut()
    await captureWithShortcut(new File(['one'], 'bug-draggable.png', { type: 'image/png' }))

    const tray = await screen.findByRole('region', { name: '截图篮' })
    Object.defineProperty(tray, 'getBoundingClientRect', {
      value: () => ({
        bottom: 660,
        height: 160,
        left: 600,
        right: 920,
        top: 500,
        width: 320,
        x: 600,
        y: 500,
        toJSON: () => {},
      }),
      configurable: true,
    })

    const dragHandle = screen.getByLabelText('拖拽移动截图篮')
    fireEvent.pointerDown(dragHandle, { button: 0, clientX: 640, clientY: 540, pointerId: 9 })
    fireEvent.pointerMove(document, { clientX: 260, clientY: 210, pointerId: 9 })
    fireEvent.pointerUp(document, { clientX: 260, clientY: 210, pointerId: 9 })

    expect(tray).toHaveStyle({
      bottom: 'auto',
      left: '220px',
      right: 'auto',
      top: '170px',
    })
  })

  it('opens a larger preview from the screenshot thumbnail', async () => {
    renderShortcut()
    await captureWithShortcut(new File(['preview'], 'bug-preview.png', { type: 'image/png' }))

    fireEvent.click(screen.getByRole('button', { name: '预览截图：bug-preview.png' }))

    expect(await screen.findByRole('dialog', { name: '截图预览' })).toBeInTheDocument()
    expect(screen.getByAltText('截图预览：bug-preview.png')).toHaveAttribute('src', 'blob:bug-preview.png')
    expect(document.querySelector('.bug-screenshot-preview__header')).toHaveTextContent('bug-preview.png')
    expect(document.querySelector('.bug-screenshot-preview__image-stage')).toContainElement(screen.getByAltText('截图预览：bug-preview.png'))

    fireEvent.click(screen.getByRole('button', { name: '关闭截图预览' }))

    expect(screen.queryByRole('dialog', { name: '截图预览' })).not.toBeInTheDocument()
  })

  it('hides the screenshot tray while selecting and generating another capture', async () => {
    renderShortcut()
    await captureWithShortcut(new File(['one'], 'bug-first.png', { type: 'image/png' }))

    fireEvent.click(screen.getByRole('button', { name: '继续截图' }))

    expect(screen.queryByRole('region', { name: '截图篮' })).not.toBeInTheDocument()
    expect(await screen.findByRole('dialog', { name: '选择截图区域' })).toBeInTheDocument()

    const pendingCapture = deferredFile(new File(['two'], 'bug-second.png', { type: 'image/png' }))
    vi.mocked(captureScreenAsPngFile).mockReturnValueOnce(pendingCapture.promise)
    await dragScreenshotSelection()

    expect(screen.queryByRole('dialog', { name: '选择截图区域' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: '截图篮' })).not.toBeInTheDocument()

    await act(async () => {
      pendingCapture.resolve()
      await pendingCapture.promise
    })

    expect(await screen.findByText('截图 2/3')).toBeInTheDocument()
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
