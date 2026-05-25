import { type CSSProperties, type PointerEvent as ReactPointerEvent, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useToast } from '../../../contexts'
import FeatureWishPoolModal from './FeatureWishPoolModal'
import { captureScreenAsPngFile, type ScreenshotCaptureRect } from './featureWishScreenshot'

const MIN_SELECTION_SIZE = 8
const MAX_SCREENSHOTS = 3
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

export default function GlobalBugScreenshotShortcut() {
  const { showToast } = useToast()
  const [screenshots, setScreenshots] = useState<ScreenshotItem[]>([])
  const screenshotsRef = useRef<ScreenshotItem[]>([])
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const [feedbackInitialFiles, setFeedbackInitialFiles] = useState<File[]>([])
  const [feedbackKey, setFeedbackKey] = useState(0)
  const [capturing, setCapturing] = useState(false)
  const [selecting, setSelecting] = useState(false)
  const [selectionDrag, setSelectionDrag] = useState<SelectionDrag | null>(null)

  useEffect(() => {
    screenshotsRef.current = screenshots
  }, [screenshots])

  useEffect(() => {
    return () => revokeScreenshots(screenshotsRef.current)
  }, [])

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
  }

  const clearScreenshots = () => {
    setScreenshots(current => {
      revokeScreenshots(current)
      return []
    })
  }

  const openFeedback = () => {
    if (screenshots.length === 0) return
    setFeedbackInitialFiles(screenshots.map(item => item.file))
    setFeedbackKey(key => key + 1)
    setFeedbackOpen(true)
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
      {screenshots.length > 0 && !feedbackOpen && createPortal(
        <section className="bug-screenshot-tray" role="region" aria-label="截图篮">
          <div className="bug-screenshot-tray__header">
            <strong>截图 {screenshots.length}/{MAX_SCREENSHOTS}</strong>
            <button type="button" onClick={clearScreenshots}>清空</button>
          </div>
          <div className="bug-screenshot-tray__thumbs">
            {screenshots.map((item, index) => (
              <div key={item.id} className="bug-screenshot-tray__thumb">
                <img src={item.url} alt={`截图 ${index + 1}`} />
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
