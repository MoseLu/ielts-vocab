import {
  GameCampaignAttemptResponseSchema,
  GameCampaignStateSchema,
  apiFetch,
  safeParse,
  type GameCampaignAttemptResponse,
  type GameCampaignDimension,
  type GameCampaignState,
  type GameNodeType,
  type Word,
} from './index'

interface GamePracticeScope {
  bookId?: string | null
  chapterId?: string | null
  day?: number | null
}

interface SubmitWordMasteryAttemptInput extends GamePracticeScope {
  word?: string | null
  dimension?: GameCampaignDimension | null
  passed: boolean
  nodeType?: GameNodeType | null
  segmentIndex?: number | null
  promptText?: string | null
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

export async function fetchGamePracticeState(scope: GamePracticeScope): Promise<GameCampaignState> {
  const query = buildScopeParams(scope).toString()
  const raw = await apiFetch(`/api/ai/practice/game/state${query ? `?${query}` : ''}`)
  const parsed = safeParse(GameCampaignStateSchema, raw)
  if (!parsed.success) {
    throw new Error('五维闯关状态响应格式错误')
  }
  return parsed.data
}

export async function submitWordMasteryAttempt(
  input: SubmitWordMasteryAttemptInput,
): Promise<GameCampaignAttemptResponse> {
  const raw = await apiFetch('/api/ai/practice/game/attempt', {
    method: 'POST',
    body: JSON.stringify({
      word: input.word ?? undefined,
      dimension: input.dimension ?? undefined,
      passed: input.passed,
      nodeType: input.nodeType ?? undefined,
      segmentIndex: input.segmentIndex ?? undefined,
      promptText: input.promptText ?? undefined,
      sourceMode: input.sourceMode ?? 'game',
      bookId: input.bookId ?? undefined,
      chapterId: input.chapterId ?? undefined,
      day: input.day ?? undefined,
      wordPayload: input.wordPayload ?? undefined,
    }),
  })
  const parsed = safeParse(GameCampaignAttemptResponseSchema, raw)
  if (!parsed.success) {
    throw new Error('五维闯关提交响应格式错误')
  }
  return parsed.data
}
