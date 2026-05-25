import html2canvas from 'html2canvas'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { canCaptureScreen, captureScreenAsPngFile } from './featureWishScreenshot'

const getDisplayMediaMock = vi.fn()

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
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getDisplayMedia: getDisplayMediaMock },
      configurable: true,
    })
  })

  it('captures the current app page without opening the browser screen picker', async () => {
    expect(canCaptureScreen()).toBe(true)

    const file = await captureScreenAsPngFile()

    expect(file.name).toMatch(/^bug-page-screenshot-\d+\.png$/)
    expect(file.type).toBe('image/png')
    expect(getDisplayMediaMock).not.toHaveBeenCalled()
    expect(html2canvas).toHaveBeenCalledWith(document.body, expect.objectContaining({
      allowTaint: false,
      height: expect.any(Number),
      useCORS: true,
      width: expect.any(Number),
    }))
  })

  it('captures only the selected viewport rectangle when provided', async () => {
    const file = await captureScreenAsPngFile({ x: 10, y: 20, width: 120, height: 90 })

    expect(file.name).toMatch(/^bug-page-screenshot-\d+\.png$/)
    expect(html2canvas).toHaveBeenCalledWith(document.body, expect.objectContaining({
      height: 90,
      width: 120,
      x: 10,
      y: 20,
    }))
    expect(getDisplayMediaMock).not.toHaveBeenCalled()
  })

  it('removes screenshot overlays from the cloned document before rendering', async () => {
    const file = await captureScreenAsPngFile()
    const options = vi.mocked(html2canvas).mock.calls[0]?.[1]
    const clonedDocument = document.implementation.createHTMLDocument()
    clonedDocument.body.innerHTML = '<div class="bug-screenshot-selector-overlay"></div><section class="bug-screenshot-tray"></section><main><input /></main>'

    options?.onclone?.(clonedDocument)

    expect(file.type).toBe('image/png')
    expect(clonedDocument.body.querySelector('.bug-screenshot-selector-overlay')).toBeNull()
    expect(clonedDocument.body.querySelector('.bug-screenshot-tray')).toBeNull()
  })
})
