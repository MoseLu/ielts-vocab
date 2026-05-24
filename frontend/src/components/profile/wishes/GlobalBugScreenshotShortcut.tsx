import { type CSSProperties, type PointerEvent as ReactPointerEvent, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useToast } from '../../../contexts'
import FeatureWishPoolModal from './FeatureWishPoolModal'
import { captureScreenAsPngFile, type ScreenshotCaptureRect } from './featureWishScreenshot'

const MIN_SELECTION_SIZE = 8

interface ScreenshotPreview {
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

export default function GlobalBugScreenshotShortcut() {
  const { showToast } = useToast()
  const [preview, setPreview] = useState<ScreenshotPreview | null>(null)
  const [bugFile, setBugFile] = useState<File | null>(null)
  const [capturing, setCapturing] = useState(false)
  const [selecting, setSelecting] = useState(false)
  const [selectionDrag, setSelectionDrag] = useState<SelectionDrag | null>(null)

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (selecting && event.key === 'Escape') {
        event.preventDefault()
        event.stopImmediatePropagation()
        setSelecting(false)
        setSelectionDrag(null)
        return
      }
      if (event.repeat || capturing || preview || bugFile || selecting) return
      if (!isBugScreenshotShortcut(event)) return

      event.preventDefault()
      event.stopImmediatePropagation()
      setSelecting(true)
    }

    window.addEventListener('keydown', handleKeyDown, true)
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [bugFile, capturing, preview, selecting])

  const captureSelection = (rect: ScreenshotCaptureRect) => {
    setCapturing(true)
    void captureScreenAsPngFile(rect)
      .then(file => {
        setPreview({ file, url: URL.createObjectURL(file) })
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

  const closePreview = () => {
    if (preview) URL.revokeObjectURL(preview.url)
    setPreview(null)
  }

  const confirmCreateBug = () => {
    if (!preview) return
    const file = preview.file
    closePreview()
    setBugFile(file)
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
      {preview && createPortal(
        <div className="bug-screenshot-preview-overlay" role="dialog" aria-modal="true" aria-label="截图预览">
          <div className="bug-screenshot-preview">
            <div className="bug-screenshot-preview__header">
              <strong>截图预览</strong>
              <span>是否新建 bug 提交条目？</span>
            </div>
            <img className="bug-screenshot-preview__image" src={preview.url} alt="Bug截图预览" />
            <div className="bug-screenshot-preview__actions">
              <button type="button" onClick={closePreview}>否</button>
              <button type="button" onClick={confirmCreateBug}>是</button>
            </div>
          </div>
        </div>,
        document.body,
      )}
      {bugFile && (
        <FeatureWishPoolModal
          key={`${bugFile.name}-${bugFile.lastModified}`}
          initialDraftFiles={[bugFile]}
          onClose={() => setBugFile(null)}
        />
      )}
    </>
  )
}
