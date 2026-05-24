const SCREENSHOT_TIMEOUT_MS = 6000

function stopStream(stream: MediaStream) {
  stream.getTracks().forEach(track => track.stop())
}

function waitForVideoReady(video: HTMLVideoElement) {
  if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA && video.videoWidth > 0) {
    return Promise.resolve()
  }
  return new Promise<void>((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error('截图超时，请重试')), SCREENSHOT_TIMEOUT_MS)
    const cleanup = () => {
      window.clearTimeout(timer)
      video.removeEventListener('loadedmetadata', onReady)
      video.removeEventListener('canplay', onReady)
      video.removeEventListener('error', onError)
    }
    const onReady = () => {
      if (video.videoWidth <= 0) return
      cleanup()
      resolve()
    }
    const onError = () => {
      cleanup()
      reject(new Error('截图画面读取失败'))
    }
    video.addEventListener('loadedmetadata', onReady)
    video.addEventListener('canplay', onReady)
    video.addEventListener('error', onError)
  })
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

export function canCaptureScreen() {
  return typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getDisplayMedia)
}

export async function captureScreenAsPngFile() {
  if (!canCaptureScreen()) {
    throw new Error('当前浏览器不支持一键截图，请继续上传图片')
  }

  const stream = await navigator.mediaDevices.getDisplayMedia({
    audio: false,
    video: { displaySurface: 'browser' },
  })
  try {
    const video = document.createElement('video')
    video.srcObject = stream
    video.muted = true
    video.playsInline = true
    await video.play()
    await waitForVideoReady(video)

    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const context = canvas.getContext('2d')
    if (!context) throw new Error('截图画布不可用')
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    const blob = await canvasToPngBlob(canvas)
    return new File([blob], `bug-screenshot-${Date.now()}.png`, { type: 'image/png' })
  } finally {
    stopStream(stream)
  }
}
