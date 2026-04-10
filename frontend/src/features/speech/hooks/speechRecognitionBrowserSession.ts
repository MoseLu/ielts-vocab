import {
  createBrowserSpeechRecognition,
  type BrowserSpeechRecognitionInstance,
  type BrowserSpeechRecognitionResultEvent,
} from './speechRecognitionUtils'

interface StartBrowserRecognitionSessionOptions {
  language: string
  onEnd?: (recognition: BrowserSpeechRecognitionInstance) => void
  onFinal?: (text: string) => void
  onPartial?: (text: string) => void
}

function extractBrowserRecognitionText(event: BrowserSpeechRecognitionResultEvent) {
  const chunks: string[] = []
  let isFinal = false

  for (let index = event.resultIndex; index < event.results.length; index += 1) {
    const result = event.results[index]
    const transcript = result?.[0]?.transcript?.trim()
    if (transcript) chunks.push(transcript)
    isFinal = Boolean(result?.isFinal) || isFinal
  }

  return {
    isFinal,
    text: chunks.join(' ').trim(),
  }
}

export function startBrowserRecognitionSession(
  windowObject: Window & typeof globalThis,
  {
    language,
    onEnd,
    onFinal,
    onPartial,
  }: StartBrowserRecognitionSessionOptions,
) {
  const recognition = createBrowserSpeechRecognition(windowObject, language)
  if (!recognition) return null

  recognition.onresult = event => {
    const { text, isFinal } = extractBrowserRecognitionText(event)
    if (!text) return
    if (isFinal) onFinal?.(text)
    else onPartial?.(text)
  }
  recognition.onend = () => {
    onEnd?.(recognition)
  }

  try {
    recognition.start()
    return recognition
  } catch {
    return null
  }
}
