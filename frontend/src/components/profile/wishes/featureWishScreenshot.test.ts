import { beforeEach, describe, expect, it, vi } from 'vitest'
import { canCaptureScreen, captureScreenAsPngFile } from './featureWishScreenshot'

const createObjectUrlMock = vi.fn()
const revokeObjectUrlMock = vi.fn()
const getDisplayMediaMock = vi.fn()
const drawImageMock = vi.fn()

class MockImage {
  onload: (() => void) | null = null
  onerror: (() => void) | null = null

  set src(_value: string) {
    window.setTimeout(() => this.onload?.(), 0)
  }
}

describe('featureWishScreenshot', () => {
  beforeEach(() => {
    document.body.innerHTML = '<main><h1>Bug page</h1><input value="typed title" /><img alt="logo" src="https://example.com/logo.png" /></main>'
    vi.restoreAllMocks()
    createObjectUrlMock.mockReset()
    revokeObjectUrlMock.mockReset()
    getDisplayMediaMock.mockReset()
    drawImageMock.mockReset()
    createObjectUrlMock.mockReturnValue('blob:page-snapshot')
    Object.defineProperty(URL, 'createObjectURL', { value: createObjectUrlMock, configurable: true })
    Object.defineProperty(URL, 'revokeObjectURL', { value: revokeObjectUrlMock, configurable: true })
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getDisplayMedia: getDisplayMediaMock },
      configurable: true,
    })
    vi.stubGlobal('Image', MockImage)
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
      drawImage: drawImageMock,
    } as unknown as CanvasRenderingContext2D)
    Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
      value(callback: BlobCallback) {
        callback(new Blob(['png'], { type: 'image/png' }))
      },
      configurable: true,
    })
  })

  it('captures the current app page without opening the browser screen picker', async () => {
    expect(canCaptureScreen()).toBe(true)

    const file = await captureScreenAsPngFile()

    expect(file.name).toMatch(/^bug-page-screenshot-\d+\.png$/)
    expect(file.type).toBe('image/png')
    expect(getDisplayMediaMock).not.toHaveBeenCalled()
    expect(drawImageMock).toHaveBeenCalled()
    expect(revokeObjectUrlMock).toHaveBeenCalledWith('blob:page-snapshot')
  })
})
