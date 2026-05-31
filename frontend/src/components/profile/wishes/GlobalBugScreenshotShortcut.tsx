import { type CSSProperties, type PointerEvent as ReactPointerEvent, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useToast } from '../../../contexts'
import FeatureWishPoolModal from './FeatureWishPoolModal'
import { captureScreenAsPngFile, type ScreenshotCaptureRect } from './featureWishScreenshot'

const MIN_SELECTION_SIZE = 8
const MAX_SCREENSHOTS = 3
const TRAY_EDGE_MARGIN = 8
const PREVIEW_MAX_WIDTH = 960
const PREVIEW_HEADER_RESERVED_HEIGHT = 64
const PREVIEW_VIEWPORT_RATIO = 0.92
const PREVIEW_MAX_UPSCALE = 2
let screenshotIdCounter = 0

interface ScreenshotItem {
  id: string
  file: File
  url: string
}

interface SelectionDrag {
  startX: number
  startY: number
  currentX: number
  currentY: number
}

interface TrayPosition {
  left: number
  top: number
}

interface TrayDrag {
  pointerId: number
  offsetX: number
  offsetY: number
  width: number
  height: number
}

interface PreviewImageSize {
  width: number
  height: number
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tagName = target.tagName
  return tagName === 'INPUT' || tagName === 'TEXTAREA' || target.isContentEditable
}

function isBugScreenshotShortcut(event: KeyboardEvent) {
  return event.shiftKey
    && !event.ctrlKey
    && !event.metaKey
    && !event.altKey
    && event.key.toLowerCase() === 'z'
    && !isEditableTarget(event.target)
}

function rectFromDrag(drag: SelectionDrag): ScreenshotCaptureRect {
  const x = Math.min(drag.startX, drag.currentX)
  const y = Math.min(drag.startY, drag.currentY)
  return {
    x,
    y,
    width: Math.abs(drag.currentX - drag.startX),
    height: Math.abs(drag.currentY - drag.startY),
  }
}

function revokeScreenshots(items: ScreenshotItem[]) {
  items.forEach(item => URL.revokeObjectURL(item.url))
}

function constrainTrayPosition(position: TrayPosition, size: Pick<TrayDrag, 'width' | 'height'>): TrayPosition {
  const viewportWidth = Math.max(1, window.innerWidth || document.documentElement.clientWidth)
  const viewportHeight = Math.max(1, window.innerHeight || document.documentElement.clientHeight)
  const maxLeft = Math.max(TRAY_EDGE_MARGIN, viewportWidth - size.width - TRAY_EDGE_MARGIN)
  const maxTop = Math.max(TRAY_EDGE_MARGIN, viewportHeight - size.height - TRAY_EDGE_MARGIN)

  return {
    left: Math.min(Math.max(TRAY_EDGE_MARGIN, Math.round(position.left)), maxLeft),
    top: Math.min(Math.max(TRAY_EDGE_MARGIN, Math.round(position.top)), maxTop),
  }
}

function fitPreviewImageSize(size: PreviewImageSize): PreviewImageSize {
  const maxWidth = Math.min(window.innerWidth * PREVIEW_VIEWPORT_RATIO, PREVIEW_MAX_WIDTH)
  const maxHeight = Math.max(1, window.innerHeight * PREVIEW_VIEWPORT_RATIO - PREVIEW_HEADER_RESERVED_HEIGHT)
  const scale = Math.min(PREVIEW_MAX_UPSCALE, maxWidth / size.width, maxHeight / size.height)
  return {
    width: Math.max(1, Math.round(size.width * scale)),
    height: Math.max(1, Math.round(size.height * scale)),
  }
}

export default function GlobalBugScreenshotShortcut() {
  const { showToast } = useToast()
  const [screenshots, setScreenshots] = useState<ScreenshotItem[]>([])
  const screenshotsRef = useRef<ScreenshotItem[]>([])
  const trayRef = useRef<HTMLElement | null>(null)
  const trayDragRef = useRef<TrayDrag | null>(null)
  const trayDragCleanupRef = useRef<(() => void) | null>(null)
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const [feedbackInitialFiles, setFeedbackInitialFiles] = useState<File[]>([])
  const [feedbackKey, setFeedbackKey] = useState(0)
  const [previewScreenshot, setPreviewScreenshot] = useState<ScreenshotItem | null>(null)
  const [previewNaturalSize, setPreviewNaturalSize] = useState<PreviewImageSize | null>(null)
  const [capturing, setCapturing] = useState(false)
  const [selecting, setSelecting] = useState(false)
  const [selectionDrag, setSelectionDrag] = useState<SelectionDrag | null>(null)
  const [trayPosition, setTrayPosition] = useState<TrayPosition | null>(null)

  useEffect(() => {
    screenshotsRef.current = screenshots
  }, [screenshots])

  useEffect(() => {
    return () => {
      trayDragCleanupRef.current?.()
      revokeScreenshots(screenshotsRef.current)
    }
  }, [])

  useEffect(() => {
    const handleResize = () => {
      setTrayPosition(current => {
        if (!current) return current
        const rect = trayRef.current?.getBoundingClientRect()
        if (!rect) return current
        return constrainTrayPosition(current, rect)
      })
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    if (!previewScreenshot) return undefined

    const handlePreviewKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setPreviewScreenshot(null)
      }
    }

    window.addEventListener('keydown', handlePreviewKeyDown, true)
    return () => window.removeEventListener('keydown', handlePreviewKeyDown, true)
  }, [previewScreenshot])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (selecting && event.key === 'Escape') {
        event.preventDefault()
        event.stopImmediatePropagation()
        setSelecting(false)
        setSelectionDrag(null)
        return
      }
      if (event.repeat || capturing || selecting) return
      if (!isBugScreenshotShortcut(event)) return

      event.preventDefault()
      event.stopImmediatePropagation()
      if (screenshotsRef.current.length >= MAX_SCREENSHOTS) {
        showToast('最多添加 3 张截图', 'info')
        return
      }
      setSelecting(true)
    }

    window.addEventListener('keydown', handleKeyDown, true)
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [capturing, selecting, showToast])

  const captureSelection = (rect: ScreenshotCaptureRect) => {
    if (screenshotsRef.current.length >= MAX_SCREENSHOTS) {
      showToast('最多添加 3 张截图', 'info')
      return
    }
    setCapturing(true)
    void captureScreenAsPngFile(rect)
      .then(file => {
        const item = {
          id: `${Date.now()}-${screenshotIdCounter++}-${file.name}-${file.size}`,
          file,
          url: URL.createObjectURL(file),
        }
        setScreenshots(current => {
          if (current.length >= MAX_SCREENSHOTS) {
            URL.revokeObjectURL(item.url)
            return current
          }
          return [...current, item]
        })
      })
      .catch(err => {
        showToast(err instanceof Error ? err.message : '截图失败，请稍后重试', 'error')
      })
      .finally(() => setCapturing(false))
  }

  const cancelSelection = () => {
    setSelecting(false)
    setSelectionDrag(null)
  }

  const updateTrayPosition = (clientX: number, clientY: number, pointerId: number) => {
    const drag = trayDragRef.current
    if (!drag || drag.pointerId !== pointerId) return
    setTrayPosition(constrainTrayPosition({
      left: clientX - drag.offsetX,
      top: clientY - drag.offsetY,
    }, drag))
  }

  const stopTrayDrag = () => {
    trayDragCleanupRef.current?.()
    trayDragCleanupRef.current = null
    trayDragRef.current = null
  }

  const handleTrayPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || !trayRef.current) return
    stopTrayDrag()
    const rect = trayRef.current.getBoundingClientRect()
    trayDragRef.current = {
      pointerId: event.pointerId,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
      width: rect.width,
      height: rect.height,
    }
    event.preventDefault()
    event.currentTarget.setPointerCapture?.(event.pointerId)
    const handleDocumentPointerMove = (pointerEvent: PointerEvent) => {
      if (pointerEvent.pointerId !== event.pointerId) return
      pointerEvent.preventDefault()
      updateTrayPosition(pointerEvent.clientX, pointerEvent.clientY, pointerEvent.pointerId)
    }
    const handleDocumentPointerUp = (pointerEvent: PointerEvent) => {
      if (pointerEvent.pointerId !== event.pointerId) return
      stopTrayDrag()
    }
    document.addEventListener('pointermove', handleDocumentPointerMove, true)
    document.addEventListener('pointerup', handleDocumentPointerUp, true)
    document.addEventListener('pointercancel', handleDocumentPointerUp, true)
    trayDragCleanupRef.current = () => {
      document.removeEventListener('pointermove', handleDocumentPointerMove, true)
      document.removeEventListener('pointerup', handleDocumentPointerUp, true)
      document.removeEventListener('pointercancel', handleDocumentPointerUp, true)
    }
    setTrayPosition(constrainTrayPosition({ left: rect.left, top: rect.top }, rect))
  }

  const handleTrayPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!trayDragRef.current || trayDragRef.current.pointerId !== event.pointerId) return
    event.preventDefault()
    updateTrayPosition(event.clientX, event.clientY, event.pointerId)
  }

  const finishTrayDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = trayDragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    event.currentTarget.releasePointerCapture?.(event.pointerId)
    stopTrayDrag()
  }

  const handleSelectorPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (capturing || event.target !== event.currentTarget) return
    event.preventDefault()
    event.currentTarget.setPointerCapture?.(event.pointerId)
    setSelectionDrag({
      startX: event.clientX,
      startY: event.clientY,
      currentX: event.clientX,
      currentY: event.clientY,
    })
  }

  const handleSelectorPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!selectionDrag) return
    event.preventDefault()
    setSelectionDrag({
      ...selectionDrag,
      currentX: event.clientX,
      currentY: event.clientY,
    })
  }

  const handleSelectorPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!selectionDrag) return
    event.preventDefault()
    const rect = rectFromDrag({
      ...selectionDrag,
      currentX: event.clientX,
      currentY: event.clientY,
    })
    setSelectionDrag(null)
    if (rect.width < MIN_SELECTION_SIZE || rect.height < MIN_SELECTION_SIZE) return
    setSelecting(false)
    captureSelection(rect)
  }

  const startSelection = () => {
    if (capturing) return
    if (screenshots.length >= MAX_SCREENSHOTS) {
      showToast('最多添加 3 张截图', 'info')
      return
    }
    setSelecting(true)
  }

  const removeScreenshot = (id: string) => {
    setScreenshots(current => {
      const target = current.find(item => item.id === id)
      if (target) URL.revokeObjectURL(target.url)
      return current.filter(item => item.id !== id)
    })
    setPreviewScreenshot(current => (current?.id === id ? null : current))
  }

  const clearScreenshots = () => {
    setScreenshots(current => {
      revokeScreenshots(current)
      return []
    })
    setPreviewScreenshot(null)
  }

  const openFeedback = () => {
    if (screenshots.length === 0) return
    setFeedbackInitialFiles(screenshots.map(item => item.file))
    setFeedbackKey(key => key + 1)
    setPreviewScreenshot(null)
    setFeedbackOpen(true)
  }

  const openPreview = (screenshot: ScreenshotItem) => {
    setPreviewNaturalSize(null)
    setPreviewScreenshot(screenshot)
  }

  const handleDraftSubmitSuccess = () => {
    clearScreenshots()
  }

  const selectionRect = selectionDrag ? rectFromDrag(selectionDrag) : null
  const selectionStyle = selectionRect
    ? ({
        left: selectionRect.x,
        top: selectionRect.y,
        width: selectionRect.width,
        height: selectionRect.height,
      } satisfies CSSProperties)
    : undefined

  const trayStyle = trayPosition
    ? ({
        left: trayPosition.left,
        top: trayPosition.top,
        right: 'auto',
        bottom: 'auto',
      } satisfies CSSProperties)
    : undefined
  const showScreenshotTray = screenshots.length > 0 && !feedbackOpen && !selecting && !capturing
  const previewImageSize = previewNaturalSize ? fitPreviewImageSize(previewNaturalSize) : null
  const previewPanelStyle = previewImageSize ? ({ width: previewImageSize.width } satisfies CSSProperties) : undefined
  const previewImageStyle = previewImageSize ? ({ width: previewImageSize.width, height: previewImageSize.height } satisfies CSSProperties) : undefined

  return (
    <>
      {selecting && createPortal(
        <div
          className="bug-screenshot-selector-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="选择截图区域"
          onPointerDown={handleSelectorPointerDown}
          onPointerMove={handleSelectorPointerMove}
          onPointerUp={handleSelectorPointerUp}
        >
          <button
            type="button"
            className="bug-screenshot-selector__cancel"
            aria-label="取消截图"
            onClick={cancelSelection}
            onPointerDown={event => event.stopPropagation()}
          >
            ×
          </button>
          {selectionRect && (
            <div className="bug-screenshot-selector__box" style={selectionStyle} aria-hidden="true" />
          )}
        </div>,
        document.body,
      )}
      {showScreenshotTray && createPortal(
        <section ref={trayRef} className="bug-screenshot-tray" role="region" aria-label="截图篮" style={trayStyle}>
          <div
            className="bug-screenshot-tray__header"
            aria-label="拖拽移动截图篮"
            title="拖拽移动截图篮"
            onPointerDown={handleTrayPointerDown}
            onPointerMove={handleTrayPointerMove}
            onPointerUp={finishTrayDrag}
            onPointerCancel={finishTrayDrag}
          >
            <strong>截图 {screenshots.length}/{MAX_SCREENSHOTS}</strong>
            <button type="button" onClick={clearScreenshots} onPointerDown={event => event.stopPropagation()}>清空</button>
          </div>
          <div className="bug-screenshot-tray__thumbs">
            {screenshots.map((item, index) => (
              <div key={item.id} className="bug-screenshot-tray__thumb">
                <button
                  type="button"
                  className="bug-screenshot-tray__preview"
                  aria-label={`预览截图：${item.file.name}`}
                  onClick={() => openPreview(item)}
                >
                  <img src={item.url} alt={`截图 ${index + 1}`} />
                </button>
                <button
                  type="button"
                  aria-label={`删除截图：${item.file.name}`}
                  onClick={() => removeScreenshot(item.id)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <div className="bug-screenshot-tray__actions">
            <button type="button" onClick={startSelection} disabled={capturing || screenshots.length >= MAX_SCREENSHOTS}>
              {screenshots.length >= MAX_SCREENSHOTS ? '已满' : '继续截图'}
            </button>
            <button type="button" onClick={openFeedback}>
              提交反馈
            </button>
          </div>
        </section>,
        document.body,
      )}
      {previewScreenshot && createPortal(
        <div
          className="bug-screenshot-preview-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="截图预览"
          onClick={event => event.target === event.currentTarget && setPreviewScreenshot(null)}
        >
          <div className="bug-screenshot-preview" style={previewPanelStyle}>
            <div className="bug-screenshot-preview__header">
              <strong>{previewScreenshot.file.name}</strong>
              <button type="button" aria-label="关闭截图预览" onClick={() => setPreviewScreenshot(null)}>×</button>
            </div>
            <div className="bug-screenshot-preview__image-stage">
              <img
                src={previewScreenshot.url}
                alt={`截图预览：${previewScreenshot.file.name}`}
                style={previewImageStyle}
                onLoad={event => setPreviewNaturalSize({
                  width: event.currentTarget.naturalWidth,
                  height: event.currentTarget.naturalHeight,
                })}
              />
            </div>
          </div>
        </div>,
        document.body,
      )}
      {feedbackOpen && (
        <FeatureWishPoolModal
          key={feedbackKey}
          initialDraftFiles={feedbackInitialFiles}
          onDraftSubmitSuccess={handleDraftSubmitSuccess}
          onClose={() => setFeedbackOpen(false)}
        />
      )}
    </>
  )
}
