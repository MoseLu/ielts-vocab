import {
  GamePracticeAttemptResponseSchema,
  GamePracticeStateSchema,
  apiFetch,
  safeParse,
  type GamePracticeAttemptResponse,
  type GamePracticeState,
  type Word,
} from './index'

interface GamePracticeScope {
  bookId?: string | null
  chapterId?: string | null
  day?: number | null
}

interface SubmitWordMasteryAttemptInput extends GamePracticeScope {
  word: string
  dimension: 'recognition' | 'meaning' | 'listening' | 'speaking' | 'dictation'
  passed: boolean
  sourceMode?: string | null
  wordPayload?: Partial<Word> | null
}

function buildScopeParams(scope: GamePracticeScope): URLSearchParams {
  const params = new URLSearchParams()
  if (scope.bookId) params.set('bookId', scope.bookId)
  if (scope.chapterId) params.set('chapterId', scope.chapterId)
  if (typeof scope.day === 'number') params.set('day', String(scope.day))
  return params
}

export async function fetchGamePracticeState(scope: GamePracticeScope): Promise<GamePracticeState> {
  const query = buildScopeParams(scope).toString()
  const raw = await apiFetch(`/api/ai/practice/game/state${query ? `?${query}` : ''}`)
  const parsed = safeParse(GamePracticeStateSchema, raw)
  if (!parsed.success) {
    throw new Error('五维闯关状态响应格式错误')
  }
  return parsed.data
}

export async function submitWordMasteryAttempt(
  input: SubmitWordMasteryAttemptInput,
): Promise<GamePracticeAttemptResponse> {
  const raw = await apiFetch('/api/ai/practice/game/attempt', {
    method: 'POST',
    body: JSON.stringify({
      word: input.word,
      dimension: input.dimension,
      passed: input.passed,
      sourceMode: input.sourceMode ?? 'game',
      bookId: input.bookId ?? undefined,
      chapterId: input.chapterId ?? undefined,
      day: input.day ?? undefined,
      wordPayload: input.wordPayload ?? undefined,
    }),
  })
  const parsed = safeParse(GamePracticeAttemptResponseSchema, raw)
  if (!parsed.success) {
    throw new Error('五维闯关提交响应格式错误')
  }
  return parsed.data
}
