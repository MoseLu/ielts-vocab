import {
  GameCampaignAttemptResponseSchema,
  GameCampaignStartResponseSchema,
  GameCampaignStateSchema,
  GameThemeCatalogSchema,
  apiFetch,
  safeParse,
  type GameCampaignAttemptResponse,
  type GameCampaignDimension,
  type GameCampaignStartResponse,
  type GameCampaignState,
  type GameThemeCatalog,
  type GameLevelKind,
  type GameNodeType,
  type Word,
} from './index'

interface GamePracticeScope {
  bookId?: string | null
  chapterId?: string | null
  day?: number | null
  themeId?: string | null
  themeChapterId?: string | null
  task?: string | null
  taskDimension?: GameCampaignDimension | null
}

interface SubmitWordMasteryAttemptInput extends GamePracticeScope {
  word?: string | null
  dimension?: GameCampaignDimension | null
  passed: boolean
  nodeType?: GameNodeType | null
  segmentIndex?: number | null
  promptText?: string | null
  sourceMode?: string | null
  entry?: string | null
  clientAttemptId?: string | null
  wordPayload?: Partial<Word> | null
  levelKind?: GameLevelKind | null
  hintUsed?: boolean | null
  inputMode?: string | null
  boostType?: string | null
}

function buildScopeParams(scope: GamePracticeScope): URLSearchParams {
  const params = new URLSearchParams()
  if (scope.bookId) params.set('bookId', scope.bookId)
  if (scope.chapterId) params.set('chapterId', scope.chapterId)
  if (typeof scope.day === 'number') params.set('day', String(scope.day))
  if (scope.themeId) params.set('themeId', scope.themeId)
  if (scope.themeChapterId) params.set('themeChapterId', scope.themeChapterId)
  if (scope.task) params.set('task', scope.task)
  if (scope.taskDimension) params.set('dimension', scope.taskDimension)
  return params
}

export async function fetchGameThemeCatalog(scope: Pick<GamePracticeScope, 'themeId'> & { page?: number | null } = {}): Promise<GameThemeCatalog> {
  const params = new URLSearchParams()
  if (scope.themeId) params.set('themeId', scope.themeId)
  if (typeof scope.page === 'number') params.set('page', String(scope.page))
  const query = params.toString()
  const raw = await apiFetch(`/api/ai/practice/game/themes${query ? `?${query}` : ''}`)
  const parsed = safeParse(GameThemeCatalogSchema, raw)
  if (!parsed.success) {
    throw new Error('主题地图响应格式错误')
  }
  return parsed.data
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

export async function startGamePracticeSession(scope: GamePracticeScope): Promise<GameCampaignStartResponse> {
  const raw = await apiFetch('/api/ai/practice/game/session/start', {
    method: 'POST',
    body: JSON.stringify({
      bookId: scope.bookId ?? undefined,
      chapterId: scope.chapterId ?? undefined,
      day: scope.day ?? undefined,
      themeId: scope.themeId ?? undefined,
      themeChapterId: scope.themeChapterId ?? undefined,
      task: scope.task ?? undefined,
      taskDimension: scope.taskDimension ?? undefined,
    }),
  })
  const parsed = safeParse(GameCampaignStartResponseSchema, raw)
  if (!parsed.success) {
    throw new Error('五维闯关启动响应格式错误')
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
      entry: input.entry ?? undefined,
      clientAttemptId: input.clientAttemptId ?? undefined,
      bookId: input.bookId ?? undefined,
      chapterId: input.chapterId ?? undefined,
      day: input.day ?? undefined,
      themeId: input.themeId ?? undefined,
      themeChapterId: input.themeChapterId ?? undefined,
      task: input.task ?? undefined,
      taskDimension: input.taskDimension ?? undefined,
      wordPayload: input.wordPayload ?? undefined,
      levelKind: input.levelKind ?? undefined,
      hintUsed: input.hintUsed ?? undefined,
      inputMode: input.inputMode ?? undefined,
      boostType: input.boostType ?? undefined,
    }),
  })
  const parsed = safeParse(GameCampaignAttemptResponseSchema, raw)
  if (!parsed.success) {
    throw new Error('五维闯关提交响应格式错误')
  }
  return parsed.data
}
