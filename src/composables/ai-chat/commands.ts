import type { LearningContext } from '../../types'

export interface PronunciationCommandPayload {
  word: string
  transcript: string
  sentence?: string
}

export interface SpeakingCommandPayload {
  part: number
  topic: string
  targetWords: string[]
  responseText?: string
}

export interface PendingPronunciationState {
  word: string
  awaitingInput: boolean
}

export interface PendingSpeakingState {
  part: number
  topic: string
  targetWords: string[]
  awaitingResponse: boolean
}

function normalizeCommandWords(value?: string | string[] | null): string[] {
  const rawValues = Array.isArray(value)
    ? value
    : typeof value === 'string'
      ? value.replace(/[，、]/g, ',').split(',')
      : []

  const seen = new Set<string>()
  const normalized: string[] = []
  for (const item of rawValues) {
    const word = String(item || '').trim()
    const key = word.toLowerCase()
    if (!key || seen.has(key)) continue
    seen.add(key)
    normalized.push(word)
  }
  return normalized
}

function normalizeFieldLabel(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, '')
}

function hasEnglishText(value: string): boolean {
  return /[A-Za-z]/.test(value)
}

function parseLabeledBlocks(text: string): Record<string, string> {
  const lines = text.split(/\r?\n/)
  const fields: Record<string, string> = {}
  let activeKey: string | null = null
  let buffer: string[] = []

  const flush = () => {
    if (!activeKey) return
    fields[activeKey] = buffer.join('\n').trim()
  }

  for (const line of lines) {
    const match = line.match(/^\s*([A-Za-z\u4e00-\u9fa5 ]{1,20})[：:]\s*(.*)$/)
    if (match) {
      flush()
      activeKey = normalizeFieldLabel(match[1])
      buffer = [match[2]]
      continue
    }
    if (activeKey) buffer.push(line)
  }

  flush()
  return fields
}

function getFieldValue(fields: Record<string, string>, labels: string[]): string {
  for (const label of labels) {
    const value = fields[normalizeFieldLabel(label)]
    if (value) return value.trim()
  }
  return ''
}

export function parsePronunciationCommand(
  input: string,
  context: LearningContext,
): PronunciationCommandPayload | null {
  const normalizedInput = input.trim()
  const isSlashCommand = /^\/pronounce\b/i.test(normalizedInput)
  const currentWord = String(context.currentWord || '').trim()

  if (isSlashCommand) {
    const remainder = normalizedInput.replace(/^\/pronounce\b/i, '').trim()
    if (!remainder) return null

    const parts = remainder.split('|').map(part => part.trim())
    if (parts.length === 1) {
      if (!currentWord) return null
      return { word: currentWord, transcript: parts[0] }
    }

    const [rawWord, transcript, sentence] = parts
    const word = rawWord || currentWord
    if (!word || !transcript) return null

    return {
      word,
      transcript,
      sentence: sentence || undefined,
    }
  }

  if (!/^(记录发音|发音记录)/.test(normalizedInput)) {
    return null
  }

  const fields = parseLabeledBlocks(normalizedInput)
  const word = getFieldValue(fields, ['单词', '目标词']) || currentWord
  const transcript = getFieldValue(fields, ['我的跟读', '跟读', '发音', '读音'])
  const sentence = getFieldValue(fields, ['我的例句', '例句', '造句'])
  if (!word) return null
  if (!transcript) return null

  return {
    word,
    transcript,
    sentence: sentence || undefined,
  }
}

export function parseSpeakingCommand(
  input: string,
  context: LearningContext,
): SpeakingCommandPayload {
  const normalizedInput = input.trim()
  const currentWord = String(context.currentWord || '').trim()
  if (/^(开始口语训练|开始口语任务|给我一个口语任务|来一轮口语训练|换一个口语任务|换个口语题|再来一道口语题)$/.test(normalizedInput)) {
    return {
      part: 1,
      topic: 'education',
      targetWords: normalizeCommandWords(currentWord),
    }
  }

  if (/^(记录口语回答|我的口语回答)/.test(normalizedInput)) {
    const fields = parseLabeledBlocks(normalizedInput)
    const partValue = Number(getFieldValue(fields, ['part', 'Part', '部分']))
    const topicValue = getFieldValue(fields, ['主题', 'topic']) || 'education'
    const targetWords = normalizeCommandWords(
      getFieldValue(fields, ['目标词', '关键词']) || currentWord,
    )
    const responseText = getFieldValue(fields, ['我的回答', '回答'])
    return {
      part: [1, 2, 3].includes(partValue) ? partValue : 2,
      topic: topicValue,
      targetWords,
      responseText: responseText || undefined,
    }
  }

  const remainder = normalizedInput.replace(/^\/speaking\b/i, '').trim()
  const [headSegment, ...responseSegments] = remainder.split('|')
  const responseText = responseSegments.join('|').trim()
  let part = 1
  let topic = 'education'
  let targetWords = normalizeCommandWords(currentWord)
  let topicExplicit = false

  const head = headSegment.trim()
  if (head) {
    const looseTokens: string[] = []
    for (const token of head.split(/\s+/)) {
      if (!token) continue
      if (/^[123]$/.test(token)) {
        part = Number(token)
        continue
      }
      if (/^part=/i.test(token)) {
        const value = Number(token.split('=')[1])
        if ([1, 2, 3].includes(value)) part = value
        continue
      }
      if (/^topic=/i.test(token)) {
        const value = token.slice(token.indexOf('=') + 1).trim()
        if (value) {
          topic = value
          topicExplicit = true
        }
        continue
      }
      if (/^words=/i.test(token)) {
        const parsedWords = normalizeCommandWords(token.slice(token.indexOf('=') + 1))
        if (parsedWords.length > 0) targetWords = parsedWords
        continue
      }
      looseTokens.push(token)
    }

    if (!topicExplicit && looseTokens.length > 0) {
      topic = looseTokens.join(' ')
    }
  }

  if (targetWords.length === 0 && currentWord) {
    targetWords = [currentWord]
  }

  return {
    part,
    topic,
    targetWords,
    responseText: responseText || undefined,
  }
}

export function buildPendingPronunciationPayload(
  input: string,
  pendingPronunciation: PendingPronunciationState | null,
): PronunciationCommandPayload | null {
  if (!pendingPronunciation?.awaitingInput) return null
  const normalizedInput = input.trim()
  if (!normalizedInput || !hasEnglishText(normalizedInput)) return null

  const explicitTranscript = normalizedInput.match(/(?:我读的是|我刚读的是|我跟读的是|我念的是)\s*[:：]?\s*([A-Za-z][A-Za-z' -]*)/i)
  const explicitSentence = normalizedInput.match(/(?:例句|句子|我造的句子|造句)(?:是)?\s*[:：]?\s*([\s\S]+)/)

  if (explicitTranscript) {
    return {
      word: pendingPronunciation.word,
      transcript: explicitTranscript[1].trim(),
      sentence: explicitSentence?.[1]?.trim() || undefined,
    }
  }

  if (explicitSentence) {
    return {
      word: pendingPronunciation.word,
      transcript: pendingPronunciation.word,
      sentence: explicitSentence[1].trim(),
    }
  }

  const tokenCount = normalizedInput.split(/\s+/).filter(Boolean).length
  if (tokenCount <= 4 && !/[.!?。！？]/.test(normalizedInput)) {
    return {
      word: pendingPronunciation.word,
      transcript: normalizedInput,
    }
  }

  if (normalizedInput.toLowerCase().includes(pendingPronunciation.word.toLowerCase())) {
    return {
      word: pendingPronunciation.word,
      transcript: pendingPronunciation.word,
      sentence: normalizedInput,
    }
  }

  return {
    word: pendingPronunciation.word,
    transcript: pendingPronunciation.word,
    sentence: normalizedInput,
  }
}

export function buildPendingSpeakingPayload(
  input: string,
  pendingSpeaking: PendingSpeakingState | null,
): SpeakingCommandPayload | null {
  if (!pendingSpeaking?.awaitingResponse) return null
  const responseText = input.trim()
  if (!responseText || !hasEnglishText(responseText) || responseText.length < 8) return null

  return {
    part: pendingSpeaking.part,
    topic: pendingSpeaking.topic,
    targetWords: pendingSpeaking.targetWords,
    responseText,
  }
}
