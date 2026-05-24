const SVG_NAMESPACE = 'http://www.w3.org/2000/svg'
const XHTML_NAMESPACE = 'http://www.w3.org/1999/xhtml'

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

function collectStyleText() {
  return Array.from(document.styleSheets)
    .map(sheet => {
      try {
        return Array.from(sheet.cssRules).map(rule => rule.cssText).join('\n')
      } catch {
        return ''
      }
    })
    .join('\n')
    .replace(/url\((?!['"]?data:)[^)]+\)/g, 'none')
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

function replaceUnsafeMedia(root: ParentNode) {
  root.querySelectorAll('img, video, iframe, canvas').forEach(element => {
    const box = element.getBoundingClientRect()
    const placeholder = document.createElement('div')
    placeholder.className = 'bug-screenshot-media-placeholder'
    placeholder.textContent = element instanceof HTMLImageElement ? element.alt : ''
    placeholder.style.width = `${Math.max(1, Math.round(box.width))}px`
    placeholder.style.height = `${Math.max(1, Math.round(box.height))}px`
    element.replaceWith(placeholder)
  })
}

function createSnapshotNode(width: number, height: number) {
  const bodyClone = document.body.cloneNode(true) as HTMLElement
  bodyClone.querySelectorAll('.bug-screenshot-preview-overlay').forEach(node => node.remove())
  copyFormValues(document.body, bodyClone)
  replaceUnsafeMedia(bodyClone)

  const wrapper = document.createElement('div')
  wrapper.setAttribute('xmlns', XHTML_NAMESPACE)
  wrapper.style.width = `${width}px`
  wrapper.style.height = `${height}px`
  wrapper.style.overflow = 'hidden'
  wrapper.style.background = getComputedStyle(document.body).backgroundColor || '#ffffff'
  wrapper.style.position = 'relative'

  const style = document.createElement('style')
  style.textContent = `
${collectStyleText()}
.bug-screenshot-media-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.45);
  background: rgba(241, 245, 249, 0.82);
  color: rgba(71, 85, 105, 0.72);
  font: 12px sans-serif;
}
`

  const viewport = document.createElement('div')
  viewport.style.position = 'absolute'
  viewport.style.left = '0'
  viewport.style.top = '0'
  viewport.style.width = `${Math.max(document.documentElement.scrollWidth, width)}px`
  viewport.style.minHeight = `${Math.max(document.documentElement.scrollHeight, height)}px`
  viewport.style.transform = `translate(${-window.scrollX}px, ${-window.scrollY}px)`
  viewport.style.transformOrigin = 'top left'
  viewport.append(bodyClone)

  wrapper.append(style, viewport)
  return wrapper
}

function loadSvgImage(svg: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const blobUrl = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }))
    const image = new Image()
    image.onload = () => {
      URL.revokeObjectURL(blobUrl)
      resolve(image)
    }
    image.onerror = () => {
      URL.revokeObjectURL(blobUrl)
      reject(new Error('页面截图渲染失败，请继续上传图片'))
    }
    image.src = blobUrl
  })
}

export function canCaptureScreen() {
  return typeof document !== 'undefined'
    && typeof XMLSerializer !== 'undefined'
    && typeof HTMLCanvasElement !== 'undefined'
}

export async function captureScreenAsPngFile() {
  if (!canCaptureScreen()) {
    throw new Error('当前浏览器不支持页面截图，请继续上传图片')
  }

  const width = Math.max(1, Math.round(window.innerWidth || document.documentElement.clientWidth))
  const height = Math.max(1, Math.round(window.innerHeight || document.documentElement.clientHeight))
  const snapshotNode = createSnapshotNode(width, height)
  const serialized = new XMLSerializer().serializeToString(snapshotNode)
  const svg = `<svg xmlns="${SVG_NAMESPACE}" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><foreignObject width="100%" height="100%">${serialized}</foreignObject></svg>`
  const image = await loadSvgImage(svg)

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  if (!context) throw new Error('截图画布不可用')
  context.drawImage(image, 0, 0, width, height)

  const blob = await canvasToPngBlob(canvas)
  return new File([blob], `bug-page-screenshot-${Date.now()}.png`, { type: 'image/png' })
}
