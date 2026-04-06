import { buildApiUrl } from '../../lib'
import type { LearningContext } from '../../types'

export type AIStreamEvent =
  | { type: 'status'; stage?: string; message?: string; tool?: string }
  | { type: 'text'; delta: string }
  | { type: 'options'; options: string[] }
  | { type: 'done'; reply: string; options?: string[] }
  | { type: 'error'; error?: string }

export function resolveStreamStatusMessage(
  event: Extract<AIStreamEvent, { type: 'status' }>,
): string {
  const explicitMessage = event.message?.trim()
  if (explicitMessage) return explicitMessage

  if (event.stage === 'tool') {
    if (event.tool === 'web_search') return 'AI 正在检索相关资料...'
    if (event.tool === 'remember_user_note') return 'AI 正在记录你的学习信息...'
    if (event.tool === 'get_wrong_words') return 'AI 正在分析你的错词记录...'
    if (event.tool === 'get_chapter_words') return 'AI 正在读取章节词表...'
    if (event.tool === 'get_book_chapters') return 'AI 正在读取词书章节结构...'
    return 'AI 正在处理学习数据...'
  }

  return 'AI 正在思考...'
}

export async function streamAIReply(params: {
  message: string
  context: LearningContext
  onEvent: (event: AIStreamEvent) => void | Promise<void>
}): Promise<void> {
  const response = await fetch(buildApiUrl('/api/ai/ask/stream'), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    signal: AbortSignal.timeout(180_000),
    body: JSON.stringify({
      message: params.message,
      context: params.context,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'AI 服务暂时不可用，请稍后重试' }))
    throw new Error(error.error || 'AI 服务暂时不可用，请稍后重试')
  }

  if (!response.body) {
    throw new Error('AI 响应流不可用')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let receivedDone = false

  const flushBuffer = async (force = false) => {
    while (true) {
      const match = buffer.match(/\r?\n\r?\n/)
      if (!match || match.index == null) break

      const rawEvent = buffer.slice(0, match.index)
      buffer = buffer.slice(match.index + match[0].length)

      const dataText = rawEvent
        .split(/\r?\n/)
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).trimStart())
        .join('\n')

      if (!dataText) continue
      const event = JSON.parse(dataText) as AIStreamEvent
      if (event.type === 'done') receivedDone = true
      await params.onEvent(event)
    }

    if (!force || !buffer.trim()) return

    const dataText = buffer
      .split(/\r?\n/)
      .filter(line => line.startsWith('data:'))
      .map(line => line.slice(5).trimStart())
      .join('\n')

    buffer = ''
    if (!dataText) return

    const event = JSON.parse(dataText) as AIStreamEvent
    if (event.type === 'done') receivedDone = true
    await params.onEvent(event)
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    await flushBuffer()
  }

  buffer += decoder.decode()
  await flushBuffer(true)

  if (!receivedDone) {
    throw new Error('AI 响应中断，请稍后重试')
  }
}
