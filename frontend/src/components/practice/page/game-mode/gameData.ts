import { DEFAULT_SETTINGS } from '../../../../constants'
import { readAppSettingsFromStorage } from '../../../../lib/appSettings'
import { playWordAudio as playPracticeWordAudio } from '../../utils.audio'
import type {
  GameCampaignDimension,
  GameCampaignNode,
  GameCampaignWord,
  GameLevelKind,
  Word,
} from '../../../../lib'

export const LEVEL_KIND_LABELS: Record<GameLevelKind, string> = {
  spelling: '会写',
  pronunciation: '会说',
  definition: '会想',
  speaking: '会认',
  example: '语境应用',
}

export const DIMENSION_LABELS: Record<GameCampaignDimension, string> = {
  recognition: '会认',
  meaning: '会想',
  dictation: '会写',
  speaking: '会说',
  listening: '语境应用',
}

export const NODE_TYPE_LABELS = {
  word: '词链关卡',
  speaking_boss: '口语 Boss',
  speaking_reward: '奖励口语关',
} as const

export const NODE_STATUS_LABELS = {
  locked: '未解锁',
  ready: '可挑战',
  pending: '待补强',
  passed: '已通关',
} as const

export const LEVEL_KIND_ORDER: GameLevelKind[] = [
  'speaking',
  'definition',
  'spelling',
  'pronunciation',
  'example',
]

export function getLevelKind(node: GameCampaignNode): GameLevelKind {
  if (node.levelKind) return node.levelKind
  if (node.dimension === 'dictation') return 'spelling'
  if (node.dimension === 'speaking') return node.nodeType === 'word' ? 'pronunciation' : 'speaking'
  if (node.dimension === 'meaning') return 'definition'
  if (node.dimension === 'listening') return 'example'
  return 'speaking'
}

export function getChallengeStep(node: GameCampaignNode) {
  return LEVEL_KIND_ORDER.indexOf(getLevelKind(node)) + 1
}

export function normalizeAnswer(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ')
}

function buildCandidatePool(word: GameCampaignWord) {
  const confusables = Array.isArray(word.listening_confusables)
    ? word.listening_confusables.map(item => ({
        word: item.word,
        definition: item.definition,
        pos: item.pos,
        phonetic: item.phonetic,
      }))
    : []
  const candidates = [
    {
      word: word.word,
      definition: word.definition,
      pos: word.pos,
      phonetic: word.phonetic,
    },
    ...confusables,
  ]
  const deduped = new Map<string, { word: string; definition: string; pos: string; phonetic: string }>()
  for (const candidate of candidates) {
    const key = normalizeAnswer(candidate.word)
    if (!key || deduped.has(key)) continue
    deduped.set(key, candidate)
  }
  return Array.from(deduped.values()).slice(0, 4)
}

export function buildDefinitionChoices(word: GameCampaignWord) {
  return buildCandidatePool(word).map(candidate => ({
    key: normalizeAnswer(candidate.word),
    label: candidate.definition,
    meta: candidate.pos,
    correct: normalizeAnswer(candidate.word) === normalizeAnswer(word.word),
  }))
}

export function buildListeningWordChoices(word: GameCampaignWord) {
  return buildCandidatePool(word).map(candidate => ({
    key: normalizeAnswer(candidate.word),
    label: candidate.word,
    meta: candidate.definition,
    correct: normalizeAnswer(candidate.word) === normalizeAnswer(word.word),
  }))
}

export function buildExampleChallenge(word: GameCampaignWord) {
  const examples = Array.isArray(word.examples) ? word.examples : []
  const example = examples.find(item => item.en) ?? null
  const escapedWord = word.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const sentence = example?.en && new RegExp(escapedWord, 'i').test(example.en)
    ? example.en.replace(new RegExp(escapedWord, 'i'), '____')
    : `The speaker used ____ clearly in context.`
  return {
    sentence,
    translation: example?.zh ?? '',
    choices: buildCandidatePool(word).map(candidate => ({
      key: normalizeAnswer(candidate.word),
      label: candidate.word,
      meta: candidate.definition,
      correct: normalizeAnswer(candidate.word) === normalizeAnswer(word.word),
    })),
  }
}

export function getWaveNumber(word: GameCampaignWord) {
  return Math.min(word.current_round + 1, 4)
}

export function playGameWordAudio(word: string) {
  const settings = typeof window === 'undefined'
    ? DEFAULT_SETTINGS
    : readAppSettingsFromStorage()
  void playPracticeWordAudio(word, {
    playbackSpeed: String(settings.playbackSpeed ?? DEFAULT_SETTINGS.playbackSpeed),
    volume: String(settings.volume ?? DEFAULT_SETTINGS.volume),
  }, undefined, undefined, {
    origin: 'game-mode',
    wordKey: word.trim().toLowerCase(),
  })
}

export function buildGameScope({
  bookId,
  chapterId,
  day,
  themeId,
  themeChapterId,
  task,
  taskDimension,
}: {
  bookId: string | null
  chapterId: string | null
  day?: number
  themeId?: string | null
  themeChapterId?: string | null
  task?: string | null
  taskDimension?: GameCampaignDimension | null
}) {
  return {
    bookId,
    chapterId,
    day,
    themeId,
    themeChapterId,
    task,
    taskDimension,
  }
}

export function buildWordPayload(word: GameCampaignWord | null | undefined) {
  if (!word) return undefined
  return {
    word: word.word,
    phonetic: word.phonetic,
    pos: word.pos,
    definition: word.definition,
    chapter_id: word.chapter_id ?? undefined,
    chapter_title: word.chapter_title ?? undefined,
    listening_confusables: word.listening_confusables,
    examples: word.examples,
  } satisfies Partial<Word>
}
