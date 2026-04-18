export const CANONICAL_PRACTICE_MODES = [
  'smart',
  'quickmemory',
  'listening',
  'meaning',
  'dictation',
  'radio',
  'errors',
] as const

export type CanonicalPracticeMode = typeof CANONICAL_PRACTICE_MODES[number]

type PracticeModeMeta = {
  label: string
  description: string
  shortLabel: string
}

const PRACTICE_MODE_META: Record<CanonicalPracticeMode, PracticeModeMeta> = {
  smart: {
    label: '智能模式',
    description: '根据水平自动调整',
    shortLabel: '智',
  },
  quickmemory: {
    label: '速记模式',
    description: '快速判断词义并进入复习链',
    shortLabel: '记',
  },
  listening: {
    label: '听音选义',
    description: '听发音选中文释义',
    shortLabel: '听',
  },
  meaning: {
    label: '默写模式',
    description: '看中文释义，默写英文单词',
    shortLabel: '想',
  },
  dictation: {
    label: '听写模式',
    description: '听发音拼写单词',
    shortLabel: '默',
  },
  radio: {
    label: '随身听',
    description: '连续播放音频',
    shortLabel: '播',
  },
  errors: {
    label: '错词强化',
    description: '集中回刷错词',
    shortLabel: '错',
  },
}

type PracticeModeMetaField = keyof PracticeModeMeta

function buildPracticeModeRecord<
  TModes extends readonly CanonicalPracticeMode[],
  TField extends PracticeModeMetaField,
>(
  modes: TModes,
  field: TField,
): Record<TModes[number], PracticeModeMeta[TField]> {
  return Object.fromEntries(
    modes.map(mode => [mode, PRACTICE_MODE_META[mode][field]]),
  ) as Record<TModes[number], PracticeModeMeta[TField]>
}

export const PRACTICE_MODE_LABELS = buildPracticeModeRecord(CANONICAL_PRACTICE_MODES, 'label')
export const PRACTICE_MODE_DESCRIPTIONS = buildPracticeModeRecord(CANONICAL_PRACTICE_MODES, 'description')
export const PRACTICE_MODE_SHORT_LABELS = buildPracticeModeRecord(CANONICAL_PRACTICE_MODES, 'shortLabel')

export const HEADER_PRACTICE_MODES = [
  'smart',
  'listening',
  'meaning',
  'dictation',
  'radio',
] as const

export const HEADER_PRACTICE_MODE_LABELS = buildPracticeModeRecord(HEADER_PRACTICE_MODES, 'label')
export const HEADER_PRACTICE_MODE_DESCRIPTIONS = buildPracticeModeRecord(HEADER_PRACTICE_MODES, 'description')

export const PRACTICE_CONTROL_MODES = [
  'smart',
  'quickmemory',
  'listening',
  'meaning',
  'dictation',
  'radio',
] as const

export const PRACTICE_CONTROL_MODE_LABELS = buildPracticeModeRecord(PRACTICE_CONTROL_MODES, 'label')

export const STATS_MODE_ORDER = [
  'smart',
  'quickmemory',
  'listening',
  'meaning',
  'dictation',
  'radio',
  'errors',
] as const

export const CHAPTER_PRACTICE_MODES = [
  'quickmemory',
  'listening',
  'meaning',
  'dictation',
  'smart',
] as const

export type ChapterPracticeMode = typeof CHAPTER_PRACTICE_MODES[number]

export const CHAPTER_PRACTICE_MODE_META = Object.fromEntries(
  CHAPTER_PRACTICE_MODES.map(mode => [mode, {
    label: PRACTICE_MODE_SHORT_LABELS[mode],
    title: PRACTICE_MODE_LABELS[mode],
  }]),
) as Record<ChapterPracticeMode, { label: string; title: string }>

export const SPECIAL_BOOK_MODE_META = {
  match: {
    label: '连',
    title: '易混消消乐',
  },
} as const

export const WRONG_WORD_DIMENSIONS = [
  'recognition',
  'meaning',
  'listening',
  'dictation',
] as const

export type WrongWordDimensionKey = typeof WRONG_WORD_DIMENSIONS[number]

export const GAME_CAMPAIGN_DIMENSIONS = [
  'recognition',
  'meaning',
  'listening',
  'speaking',
  'dictation',
] as const

export type GameCampaignDimension = typeof GAME_CAMPAIGN_DIMENSIONS[number]

export const GAME_NODE_TYPES = [
  'word',
  'speaking_boss',
  'speaking_reward',
] as const

export type GameNodeType = typeof GAME_NODE_TYPES[number]

export const GAME_CAMPAIGN_LABEL = '五维闯关'

export const GAME_CAMPAIGN_DIMENSION_LABELS: Record<GameCampaignDimension, string> = {
  recognition: '认词',
  meaning: '释义',
  listening: '听辨',
  speaking: '口语',
  dictation: '拼写',
}

export const WRONG_WORD_DIMENSION_TO_MODE: Record<WrongWordDimensionKey, CanonicalPracticeMode> = {
  recognition: 'quickmemory',
  meaning: 'meaning',
  listening: 'listening',
  dictation: 'dictation',
}

const WRONG_WORD_DIMENSION_TITLES_META: Record<WrongWordDimensionKey, string> = {
  recognition: `${PRACTICE_MODE_LABELS.quickmemory}：看到英文单词时，能不能立刻认出中文意思`,
  meaning: `${PRACTICE_MODE_LABELS.meaning}：看到中文意思时，能不能主动默写出英文单词`,
  listening: `${PRACTICE_MODE_LABELS.listening}：听到发音后，能不能判断它对应的意思`,
  dictation: `${PRACTICE_MODE_LABELS.dictation}：听到发音后，能不能把单词完整拼出来`,
}

export const WRONG_WORD_DIMENSION_LABELS = Object.fromEntries(
  WRONG_WORD_DIMENSIONS.map(dimension => [dimension, PRACTICE_MODE_LABELS[WRONG_WORD_DIMENSION_TO_MODE[dimension]]]),
) as Record<WrongWordDimensionKey, string>

export const WRONG_WORD_DIMENSION_TITLES = Object.fromEntries(
  WRONG_WORD_DIMENSIONS.map(dimension => [dimension, WRONG_WORD_DIMENSION_TITLES_META[dimension]]),
) as Record<WrongWordDimensionKey, string>

const MODE_ALIAS_TO_KEY: Record<string, CanonicalPracticeMode> = {
  smart: 'smart',
  '智能模式': 'smart',
  '智能练习': 'smart',
  '智能学习': 'smart',
  quickmemory: 'quickmemory',
  recognition: 'quickmemory',
  '速记模式': 'quickmemory',
  '速记模式（会认）': 'quickmemory',
  '快速记忆': 'quickmemory',
  '看词认义': 'quickmemory',
  '看词认义（会认）': 'quickmemory',
  listening: 'listening',
  '听音选义': 'listening',
  '听音选义（会辨）': 'listening',
  '听音辨义': 'listening',
  '听音辨义（会辨）': 'listening',
  meaning: 'meaning',
  '默写模式': 'meaning',
  '默写模式（会想）': 'meaning',
  '释义拼词': 'meaning',
  '释义拼词（会想）': 'meaning',
  '中文想英文': 'meaning',
  dictation: 'dictation',
  '听写模式': 'dictation',
  '听写模式（会写）': 'dictation',
  '听音拼写': 'dictation',
  '拼写默写': 'dictation',
  radio: 'radio',
  '随身听': 'radio',
  '随身听模式': 'radio',
  errors: 'errors',
  '错词强化': 'errors',
  '错词复习': 'errors',
}

const GAME_MODE_ALIASES = [
  'game',
  '五维闯关',
  '闯关模式',
] as const

const MODE_COPY_ALIASES = [
  ...Object.keys(MODE_ALIAS_TO_KEY),
  ...GAME_MODE_ALIASES,
].sort((left, right) => right.length - left.length)

function normalizeLookupKey(value: string): string {
  return value.trim().toLowerCase()
}

function getCanonicalMode(value?: string | null): CanonicalPracticeMode | null {
  if (!value) return null
  return MODE_ALIAS_TO_KEY[normalizeLookupKey(value)] ?? MODE_ALIAS_TO_KEY[value.trim()] ?? null
}

export function isWrongWordDimensionKey(value: string | null | undefined): value is WrongWordDimensionKey {
  if (!value) return false
  return value in WRONG_WORD_DIMENSION_TO_MODE
}

export function getPracticeModeLabel(
  mode?: string | null,
  fallbackLabel?: string | null,
): string | null {
  const canonicalMode = getCanonicalMode(mode) ?? getCanonicalMode(fallbackLabel)
  if (canonicalMode) return PRACTICE_MODE_LABELS[canonicalMode]

  const normalizedMode = normalizeLookupKey(mode ?? '')
  if (GAME_MODE_ALIASES.includes(normalizedMode as typeof GAME_MODE_ALIASES[number])) {
    return GAME_CAMPAIGN_LABEL
  }

  const normalizedFallbackLabel = normalizeLookupKey(fallbackLabel ?? '')
  if (GAME_MODE_ALIASES.includes(normalizedFallbackLabel as typeof GAME_MODE_ALIASES[number])) {
    return GAME_CAMPAIGN_LABEL
  }

  const normalizedFallback = fallbackLabel?.trim()
  if (normalizedFallback) return normalizedFallback

  const trimmedMode = mode?.trim()
  return trimmedMode || null
}

export function getWrongWordDimensionModeLabel(
  dimension?: string | null,
  fallbackLabel?: string | null,
): string | null {
  if (isWrongWordDimensionKey(dimension)) {
    return PRACTICE_MODE_LABELS[WRONG_WORD_DIMENSION_TO_MODE[dimension]]
  }

  return getPracticeModeLabel(dimension, fallbackLabel)
}

export function normalizeModeText(text?: string | null): string {
  const normalized = text?.trim()
  if (!normalized) return ''

  return MODE_COPY_ALIASES.reduce((result, alias) => {
    const replacement = alias in MODE_ALIAS_TO_KEY
      ? PRACTICE_MODE_LABELS[MODE_ALIAS_TO_KEY[alias]]
      : GAME_CAMPAIGN_LABEL
    return result.split(alias).join(replacement)
  }, normalized)
}
