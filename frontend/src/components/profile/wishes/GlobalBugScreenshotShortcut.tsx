import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useToast } from '../../../contexts'
import FeatureWishPoolModal from './FeatureWishPoolModal'
import { captureScreenAsPngFile } from './featureWishScreenshot'

interface ScreenshotPreview {
  file: File
  url: string
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

export default function GlobalBugScreenshotShortcut() {
  const { showToast } = useToast()
  const [preview, setPreview] = useState<ScreenshotPreview | null>(null)
  const [bugFile, setBugFile] = useState<File | null>(null)
  const [capturing, setCapturing] = useState(false)

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.repeat || capturing || preview || bugFile) return
      if (!isBugScreenshotShortcut(event)) return

      event.preventDefault()
      event.stopImmediatePropagation()
      setCapturing(true)
      void captureScreenAsPngFile()
        .then(file => {
          setPreview({ file, url: URL.createObjectURL(file) })
        })
        .catch(err => {
          showToast(err instanceof Error ? err.message : '截图失败，请稍后重试', 'error')
        })
        .finally(() => setCapturing(false))
    }

    window.addEventListener('keydown', handleKeyDown, true)
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [bugFile, capturing, preview, showToast])

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

  return (
    <>
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
