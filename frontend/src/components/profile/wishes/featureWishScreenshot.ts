import html2canvas from 'html2canvas'

const REMOVED_OVERLAYS_SELECTOR = '.bug-screenshot-preview-overlay, .bug-screenshot-selector-overlay'
const UNSUPPORTED_MEDIA_SELECTOR = 'video, iframe, canvas'

export interface ScreenshotCaptureRect {
  x: number
  y: number
  width: number
  height: number
}

function canvasToPngBlob(canvas: HTMLCanvasElement) {
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(blob => {
      if (blob) {
        resolve(blob)
      } else {
        reject(new Error('截图生成失败'))
      }
    }, 'image/png')
  })
}

function copyFormValues(source: ParentNode, target: ParentNode) {
  const sourceFields = Array.from(source.querySelectorAll('input, textarea, select'))
  const targetFields = Array.from(target.querySelectorAll('input, textarea, select'))

  sourceFields.forEach((sourceField, index) => {
    const targetField = targetFields[index]
    if (!targetField) return

    if (sourceField instanceof HTMLInputElement && targetField instanceof HTMLInputElement) {
      targetField.value = sourceField.value
      targetField.checked = sourceField.checked
      return
    }
    if (sourceField instanceof HTMLTextAreaElement && targetField instanceof HTMLTextAreaElement) {
      targetField.value = sourceField.value
      targetField.textContent = sourceField.value
      return
    }
    if (sourceField instanceof HTMLSelectElement && targetField instanceof HTMLSelectElement) {
      targetField.value = sourceField.value
    }
  })
}

function isUnsafeExternalImage(image: HTMLImageElement) {
  const rawSrc = image.currentSrc || image.src
  if (!rawSrc) return false

  try {
    const url = new URL(rawSrc, window.location.href)
    return !['data:', 'blob:'].includes(url.protocol) && url.origin !== window.location.origin
  } catch {
    return true
  }
}

function createMediaPlaceholder(element: Element) {
  const box = element.getBoundingClientRect()
  const placeholder = document.createElement('div')
  placeholder.textContent = element instanceof HTMLImageElement ? element.alt : ''
  placeholder.style.display = 'inline-flex'
  placeholder.style.alignItems = 'center'
  placeholder.style.justifyContent = 'center'
  placeholder.style.overflow = 'hidden'
  placeholder.style.width = `${Math.max(1, Math.round(box.width))}px`
  placeholder.style.height = `${Math.max(1, Math.round(box.height))}px`
  placeholder.style.border = 'var(--size-1) solid var(--border)'
  placeholder.style.background = 'var(--bg-secondary)'
  placeholder.style.color = 'var(--text-tertiary)'
  placeholder.style.font = 'var(--size-12) sans-serif'
  return placeholder
}

function replaceUnsafeMedia(root: ParentNode) {
  root.querySelectorAll(UNSUPPORTED_MEDIA_SELECTOR).forEach(element => {
    element.replaceWith(createMediaPlaceholder(element))
  })
  root.querySelectorAll('img').forEach(image => {
    if (isUnsafeExternalImage(image)) {
      image.replaceWith(createMediaPlaceholder(image))
    }
  })
}

export function canCaptureScreen() {
  return typeof document !== 'undefined'
    && typeof HTMLCanvasElement !== 'undefined'
}

function normalizeCaptureRect(rect?: ScreenshotCaptureRect) {
  if (!rect) {
    return null
  }
  const maxWidth = Math.max(1, Math.round(window.innerWidth || document.documentElement.clientWidth))
  const maxHeight = Math.max(1, Math.round(window.innerHeight || document.documentElement.clientHeight))
  const x = Math.max(0, Math.min(maxWidth - 1, Math.round(rect.x)))
  const y = Math.max(0, Math.min(maxHeight - 1, Math.round(rect.y)))
  const right = Math.max(x + 1, Math.min(maxWidth, Math.round(rect.x + rect.width)))
  const bottom = Math.max(y + 1, Math.min(maxHeight, Math.round(rect.y + rect.height)))
  return {
    x,
    y,
    width: right - x,
    height: bottom - y,
  }
}

export async function captureScreenAsPngFile(rect?: ScreenshotCaptureRect) {
  if (!canCaptureScreen()) {
    throw new Error('当前浏览器不支持页面截图，请继续上传图片')
  }

  const viewportWidth = Math.max(1, Math.round(window.innerWidth || document.documentElement.clientWidth))
  const viewportHeight = Math.max(1, Math.round(window.innerHeight || document.documentElement.clientHeight))
  const normalizedRect = normalizeCaptureRect(rect)
  const width = normalizedRect?.width ?? viewportWidth
  const height = normalizedRect?.height ?? viewportHeight
  const x = window.scrollX + (normalizedRect?.x ?? 0)
  const y = window.scrollY + (normalizedRect?.y ?? 0)
  const canvas = await html2canvas(document.body, {
    allowTaint: false,
    backgroundColor: getComputedStyle(document.body).backgroundColor || null,
    height,
    ignoreElements: element => element.matches(REMOVED_OVERLAYS_SELECTOR),
    logging: false,
    onclone: clonedDocument => {
      clonedDocument.body.querySelectorAll(REMOVED_OVERLAYS_SELECTOR).forEach(node => node.remove())
      copyFormValues(document.body, clonedDocument.body)
      replaceUnsafeMedia(clonedDocument.body)
    },
    scrollX: window.scrollX,
    scrollY: window.scrollY,
    useCORS: true,
    width,
    windowHeight: Math.max(document.documentElement.scrollHeight, viewportHeight),
    windowWidth: Math.max(document.documentElement.scrollWidth, viewportWidth),
    x,
    y,
  })

  const blob = await canvasToPngBlob(canvas)
  return new File([blob], `bug-page-screenshot-${Date.now()}.png`, { type: 'image/png' })
}
