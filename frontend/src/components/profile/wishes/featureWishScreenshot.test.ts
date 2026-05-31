import html2canvas from 'html2canvas'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { canCaptureScreen, captureScreenAsPngFile } from './featureWishScreenshot'

const getDisplayMediaMock = vi.fn()
const canvasDrawImageMock = vi.fn()

vi.mock('html2canvas', () => ({
  default: vi.fn(),
}))

function createMockCanvas() {
  const canvas = document.createElement('canvas')
  Object.defineProperty(canvas, 'toBlob', {
    value(callback: BlobCallback) {
      callback(new Blob(['png'], { type: 'image/png' }))
    },
    configurable: true,
  })
  return canvas
}

describe('featureWishScreenshot', () => {
  beforeEach(() => {
    document.body.innerHTML = '<main><h1>Bug page</h1><input value="typed title" /><img alt="logo" src="https://example.com/logo.png" /></main>'
    vi.mocked(html2canvas).mockReset()
    vi.mocked(html2canvas).mockResolvedValue(createMockCanvas())
    getDisplayMediaMock.mockReset()
    canvasDrawImageMock.mockReset()
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      value: () => ({ drawImage: canvasDrawImageMock }),
      configurable: true,
    })
    Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
      value(callback: BlobCallback) {
        callback(new Blob(['png'], { type: 'image/png' }))
      },
      configurable: true,
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getDisplayMedia: getDisplayMediaMock },
      configurable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('captures the current app page without opening the browser screen picker', async () => {
    expect(canCaptureScreen()).toBe(true)

    const file = await captureScreenAsPngFile()

    expect(file.name).toMatch(/^bug-page-screenshot-\d+\.png$/)
    expect(file.type).toBe('image/png')
    expect(getDisplayMediaMock).not.toHaveBeenCalled()
    expect(html2canvas).toHaveBeenCalledWith(document.body, expect.objectContaining({
      allowTaint: false,
      backgroundColor: expect.any(String),
      foreignObjectRendering: true,
      height: expect.any(Number),
      useCORS: true,
      width: expect.any(Number),
      x: 0,
      y: 0,
    }))
  })

  it('captures only the selected viewport rectangle when provided', async () => {
    const renderedCanvas = createMockCanvas()
    renderedCanvas.width = 2048
    renderedCanvas.height = 1536
    vi.mocked(html2canvas).mockResolvedValueOnce(renderedCanvas)

    const file = await captureScreenAsPngFile({ x: 10, y: 20, width: 120, height: 90 })
    const options = vi.mocked(html2canvas).mock.calls[0]?.[1]
    const scaleX = renderedCanvas.width / Number(options?.width)
    const scaleY = renderedCanvas.height / Number(options?.height)
    const cropWidth = Math.round(120 * scaleX)
    const cropHeight = Math.round(90 * scaleY)

    expect(file.name).toMatch(/^bug-page-screenshot-\d+\.png$/)
    expect(html2canvas).toHaveBeenCalledWith(document.body, expect.objectContaining({
      foreignObjectRendering: true,
      x: 0,
      y: 0,
    }))
    expect(canvasDrawImageMock).toHaveBeenCalledWith(
      renderedCanvas,
      Math.round(11 * scaleX),
      Math.round(21 * scaleY),
      cropWidth,
      cropHeight,
      0,
      0,
      cropWidth,
      cropHeight,
    )
    expect(getDisplayMediaMock).not.toHaveBeenCalled()
  })

  it('falls back from unsupported modern computed background colors', async () => {
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      backgroundColor: 'color(srgb 1 1 1)',
    } as CSSStyleDeclaration)

    await captureScreenAsPngFile()

    expect(html2canvas).toHaveBeenCalledWith(document.body, expect.objectContaining({
      backgroundColor: '#ffffff',
    }))
  })

  it('removes screenshot overlays from the cloned document before rendering', async () => {
    const file = await captureScreenAsPngFile()
    const options = vi.mocked(html2canvas).mock.calls[0]?.[1]
    const clonedDocument = document.implementation.createHTMLDocument()
    clonedDocument.body.innerHTML = '<header class="header"></header><div class="bug-screenshot-selector-overlay"></div><section class="bug-screenshot-tray"></section><main><input /></main>'

    options?.onclone?.(clonedDocument)

    expect(file.type).toBe('image/png')
    expect(clonedDocument.body.querySelector('.bug-screenshot-selector-overlay')).toBeNull()
    expect(clonedDocument.body.querySelector('.bug-screenshot-tray')).toBeNull()
    expect(clonedDocument.body.querySelector<HTMLElement>('.header')?.style.boxShadow).toBe('none')
  })
})
