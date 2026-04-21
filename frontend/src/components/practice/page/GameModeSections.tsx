import PracticePronunciationButton from './PracticePronunciationButton'
import { DEFAULT_SETTINGS } from '../../../constants'
import { readAppSettingsFromStorage } from '../../../lib/appSettings'
import { playWordAudio as playPracticeWordAudio } from '../utils.audio'
import type {
  GameCampaignDimension,
  GameCampaignNode,
  GameCampaignWord,
  Word,
} from '../../../lib'

export const DIMENSION_LABELS: Record<GameCampaignDimension, string> = {
  recognition: '认词',
  meaning: '释义',
  listening: '听辨',
  speaking: '口语',
  dictation: '拼写',
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

const DIMENSION_ORDER: GameCampaignDimension[] = ['recognition', 'meaning', 'listening', 'speaking', 'dictation']

function normalizeAnswer(value: string): string {
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

function buildMeaningChoices(word: GameCampaignWord) {
  return buildCandidatePool(word).map(candidate => ({
    key: normalizeAnswer(candidate.word),
    label: candidate.definition,
    meta: candidate.pos,
    correct: normalizeAnswer(candidate.word) === normalizeAnswer(word.word),
  }))
}

function buildListeningChoices(word: GameCampaignWord) {
  return buildCandidatePool(word).map(candidate => ({
    key: normalizeAnswer(candidate.word),
    label: candidate.word,
    meta: candidate.phonetic || candidate.definition,
    correct: normalizeAnswer(candidate.word) === normalizeAnswer(word.word),
  }))
}

function playWordAudio(word: string) {
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

function getWaveNumber(word: GameCampaignWord) {
  return Math.min(word.current_round + 1, 4)
}

function getDimensionSummary(word: GameCampaignWord) {
  return DIMENSION_ORDER.map(itemDimension => {
    const dimensionState = word.dimension_states[itemDimension]
    return {
      key: itemDimension,
      label: DIMENSION_LABELS[itemDimension],
      passStreak: dimensionState?.pass_streak ?? 0,
      passed: (dimensionState?.pass_streak ?? 0) >= 4,
    }
  })
}

function getSceneCaption(dimension: GameCampaignDimension) {
  if (dimension === 'meaning') return '把场景和词义绑定在一起，再做判断。'
  if (dimension === 'listening') return '先听，再从候选里锁定正确词形。'
  if (dimension === 'speaking') return '先开口，通过后这一维直接点亮。'
  if (dimension === 'dictation') return '听到后把单词完整拼出来。'
  return '先认出这个词，再推进后续维度。'
}

function getSceneStatusLabel(image: GameCampaignWord['image']) {
  if (image.status === 'ready') return '场景已解锁'
  if (image.status === 'queued') return '排队生成'
  if (image.status === 'generating') return '生成中'
  return '场景暂缺'
}

function getSceneStatusHelp(image: GameCampaignWord['image']) {
  if (image.status === 'queued' || image.status === 'generating') {
    return '场景构建中，稍后会补上更贴词义的画面。'
  }
  if (image.status === 'failed') return '当前词的场景卡暂缺，不影响继续战役。'
  return '用画面先锁定义项，再推进后续关卡。'
}

function getSceneKicker(node: GameCampaignNode) {
  if (node.nodeType !== 'word' || !node.dimension) return NODE_TYPE_LABELS[node.nodeType]
  return `${getChallengeStep(node)}/5 ${DIMENSION_LABELS[node.dimension]}挑战`
}

function getStagePrompt(node: GameCampaignNode) {
  if (node.dimension === 'meaning') return '根据场景与单词，选出正确的中文释义'
  if (node.dimension === 'listening') return '播放单词后，选出正确的英文词形'
  if (node.dimension === 'dictation') return '播放单词后，完整拼写这个单词'
  if (node.dimension === 'speaking') return '点击下方开始跟读，只检查当前单词发音'
  return '看到这个词时，你能立刻认出它吗？'
}

function getResultText(correct: boolean, mode: 'word' | 'boss') {
  return correct
    ? (mode === 'boss' ? '非常棒，Boss 已结算，战役继续。' : '非常棒，当前关已结算，继续推进。')
    : (mode === 'boss' ? '这关已回流到 Boss 队列，稍后重打。' : '这关已记入回流区，稍后还会再出现。')
}

function getSceneTone(node: GameCampaignNode) {
  if (node.nodeType !== 'word') return 'studio'
  if (node.dimension === 'meaning') return 'meaning'
  if (node.dimension === 'listening') return 'listening'
  if (node.dimension === 'speaking') return 'speaking'
  if (node.dimension === 'dictation') return 'dictation'
  return 'recognition'
}

export function getChallengeStep(node: GameCampaignNode) {
  if (node.nodeType !== 'word' || !node.dimension) return DIMENSION_ORDER.length
  return DIMENSION_ORDER.indexOf(node.dimension) + 1
}

export function buildGameScope({
  bookId,
  chapterId,
  day,
}: {
  bookId: string | null
  chapterId: string | null
  day?: number
}) {
  return {
    bookId,
    chapterId: bookId ? null : chapterId,
    day,
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

function WordScene({
  node,
  word,
}: {
  node: GameCampaignNode
  word: GameCampaignWord
}) {
  const image = word.image
  const tone = getSceneTone(node)
  const showSceneImage = image.status === 'ready' && Boolean(image.url)
  const showWordBubble = node.dimension !== 'listening' && node.dimension !== 'dictation'

  return (
    <div className={`practice-game-mode__scene practice-game-mode__scene--${tone} is-${image.status}`}>
      {showSceneImage ? <img src={image.url ?? undefined} alt={image.alt} className="practice-game-mode__scene-image" /> : null}
      <div className="practice-game-mode__scene-overlay" />

      <div className="practice-game-mode__scene-head">
        <span>{getSceneKicker(node)}</span>
        <span>{getSceneStatusLabel(image)}</span>
        <span>第 {getWaveNumber(word)}/4 波</span>
      </div>

      {showWordBubble ? (
        <div className="practice-game-mode__scene-bubble">
          <strong>{word.word}</strong>
          {word.phonetic ? <span>{word.phonetic}</span> : null}
        </div>
      ) : null}

      {node.dimension === 'listening' ? (
        <button type="button" className="practice-game-mode__scene-audio" onClick={() => playWordAudio(word.word)}>
          播放单词
        </button>
      ) : null}

      {(node.dimension === 'speaking' || node.dimension === 'dictation' || image.status !== 'ready') ? (
        <div className="practice-game-mode__scene-coach">
          <span>{node.dimension === 'dictation' ? '拼写训练' : node.dimension === 'speaking' ? '口语试炼' : '场景扫描中'}</span>
          <strong>{node.dimension === 'dictation' ? word.definition : word.word.slice(0, 2).toUpperCase()}</strong>
          <small>{image.status === 'ready' ? word.pos : image.status === 'failed' ? '雷达暂未捕获场景' : '雷达扫描中'}</small>
        </div>
      ) : null}

      <div className="practice-game-mode__scene-caption">
        <strong>{word.definition}</strong>
        <span>{getSceneStatusHelp(image)}</span>
        <span>{getSceneCaption(node.dimension ?? 'recognition')}</span>
      </div>
    </div>
  )
}

function BattleBanner({
  tone,
  message,
}: {
  tone: 'success' | 'warning'
  message: string
}) {
  return <div className={`practice-game-mode__banner is-${tone}`}>{message}</div>
}
function ChoiceGrid({
  choices,
  selectedChoice,
  onSelectChoice,
}: {
  choices: Array<{ key: string; label: string; meta: string; correct: boolean }>
  selectedChoice: string | null
  onSelectChoice: (value: string) => void
}) {
  return (
    <div className="practice-game-mode__choice-grid">
      {choices.map(choice => (
        <button
          key={choice.key}
          type="button"
          className={`practice-game-mode__choice${selectedChoice === choice.key ? ' is-selected' : ''}`}
          onClick={() => onSelectChoice(choice.key)}
        >
          <strong>{choice.label}</strong>
          <span>{choice.meta}</span>
        </button>
      ))}
    </div>
  )
}

export function WordMissionScreen({
  node,
  bookId,
  chapterId,
  answerInput,
  selectedChoice,
  isSubmitting,
  banner,
  error,
  onAnswerChange,
  onSelectChoice,
  onSubmitAttempt,
  onRefreshAfterSpeaking,
}: {
  node: GameCampaignNode
  bookId: string | null
  chapterId: string | null
  answerInput: string
  selectedChoice: string | null
  isSubmitting: boolean
  banner: { tone: 'success' | 'warning'; message: string } | null
  error: string | null
  onAnswerChange: (value: string) => void
  onSelectChoice: (value: string | null) => void
  onSubmitAttempt: (passed: boolean) => Promise<void>
  onRefreshAfterSpeaking: (passed: boolean) => void
}) {
  const word = node.word
  const dimension = node.dimension
  if (!word || !dimension) return null

  const dimensionSummary = getDimensionSummary(word)
  const meaningChoices = buildMeaningChoices(word)
  const listeningChoices = buildListeningChoices(word)
  const selectedMeaning = meaningChoices.find(choice => choice.key === selectedChoice)
  const selectedListening = listeningChoices.find(choice => choice.key === selectedChoice)

  return (
    <section className="practice-game-mode__battle-screen">
      <WordScene node={node} word={word} />

      <div className="practice-game-mode__sheet">
        <div className="practice-game-mode__sheet-head">
          <div>
            <span className="practice-game-mode__sheet-eyebrow">{DIMENSION_LABELS[dimension]}关</span>
            <strong>{getStagePrompt(node)}</strong>
          </div>
          <span className="practice-game-mode__sheet-wave">第 {getWaveNumber(word)}/4 波</span>
        </div>

        <div className="practice-game-mode__dimension-row">
          {dimensionSummary.map(item => (
            <div
              key={item.key}
              className={`practice-game-mode__dimension-chip${item.key === dimension ? ' is-active' : ''}${item.passed ? ' is-passed' : ''}`}
            >
              <span>{item.label}</span>
              <strong>{item.passStreak}/4</strong>
            </div>
          ))}
        </div>

        {dimension === 'recognition' ? (
          <div className="practice-game-mode__task">
            <div className="practice-game-mode__callout">{word.word}</div>
            <div className="practice-game-mode__button-row">
              <button type="button" className="practice-game-mode__action" onClick={() => void onSubmitAttempt(true)} disabled={isSubmitting}>命中</button>
              <button type="button" className="practice-game-mode__action is-secondary" onClick={() => void onSubmitAttempt(false)} disabled={isSubmitting}>失手</button>
            </div>
          </div>
        ) : null}

        {dimension === 'meaning' ? (
          <div className="practice-game-mode__task">
            <ChoiceGrid choices={meaningChoices} selectedChoice={selectedChoice} onSelectChoice={value => onSelectChoice(value)} />
            <button
              type="button"
              className="practice-game-mode__action"
              onClick={() => void onSubmitAttempt(Boolean(selectedMeaning?.correct))}
              disabled={isSubmitting || !selectedMeaning}
            >
              检查
            </button>
          </div>
        ) : null}

        {dimension === 'listening' ? (
          <div className="practice-game-mode__task">
            <ChoiceGrid choices={listeningChoices} selectedChoice={selectedChoice} onSelectChoice={value => onSelectChoice(value)} />
            <button
              type="button"
              className="practice-game-mode__action"
              onClick={() => void onSubmitAttempt(Boolean(selectedListening?.correct))}
              disabled={isSubmitting || !selectedListening}
            >
              检查
            </button>
          </div>
        ) : null}

        {dimension === 'speaking' ? (
          <div className="practice-game-mode__task">
            <PracticePronunciationButton
              bookId={bookId}
              chapterId={chapterId}
              targetWord={word.word}
              targetPhonetic={word.phonetic}
              onEvaluated={result => {
                onRefreshAfterSpeaking(result.passed)
              }}
            />
          </div>
        ) : null}

        {dimension === 'dictation' ? (
          <div className="practice-game-mode__task">
            <div className="practice-game-mode__button-row">
              <button type="button" className="practice-game-mode__action is-secondary" onClick={() => playWordAudio(word.word)}>播放单词</button>
            </div>
            <div className="practice-game-mode__input-row">
              <input
                value={answerInput}
                onChange={event => onAnswerChange(event.target.value)}
                placeholder="输入拼写"
                disabled={isSubmitting}
                className="practice-game-mode__input"
              />
              <button
                type="button"
                className="practice-game-mode__action"
                onClick={() => void onSubmitAttempt(normalizeAnswer(answerInput) === normalizeAnswer(word.word))}
                disabled={isSubmitting || !answerInput.trim()}
              >
                检查
              </button>
            </div>
          </div>
        ) : null}

        {banner ? <BattleBanner tone={banner.tone} message={banner.message} /> : null}
        {error ? <div className="practice-game-mode__error">{error}</div> : null}
      </div>
    </section>
  )
}

export function SpeakingMissionScreen({
  node,
  isSubmitting,
  banner,
  error,
  onSubmitNode,
}: {
  node: GameCampaignNode
  isSubmitting: boolean
  banner: { tone: 'success' | 'warning'; message: string } | null
  error: string | null
  onSubmitNode: (passed: boolean) => Promise<void>
}) {
  const isBoss = node.nodeType === 'speaking_boss'

  return (
    <section className="practice-game-mode__battle-screen">
      <div className={`practice-game-mode__scene practice-game-mode__scene--boss${isBoss ? ' is-boss' : ''}`}>
        <div className="practice-game-mode__scene-overlay" />
        <div className="practice-game-mode__scene-head">
          <span>{NODE_TYPE_LABELS[node.nodeType]}</span>
          <span>{isBoss ? `重打 ${node.bossFailures} 次` : `失手 ${node.rewardFailures} 次`}</span>
        </div>
        <div className="practice-game-mode__scene-coach is-large">
          <span>{isBoss ? '段末结算战' : '奖励口语关'}</span>
          <strong>{node.title}</strong>
          <small>{node.subtitle ?? getResultText(false, 'boss')}</small>
        </div>
        {node.targetWords.length > 0 ? (
          <div className="practice-game-mode__token-row">
            {node.targetWords.map(word => (
              <span key={word} className="practice-game-mode__token-chip">{word}</span>
            ))}
          </div>
        ) : null}
      </div>

      <div className="practice-game-mode__sheet">
        <div className="practice-game-mode__sheet-head">
          <div>
            <span className="practice-game-mode__sheet-eyebrow">{NODE_TYPE_LABELS[node.nodeType]}</span>
            <strong>{node.promptText || '围绕目标词完成口语试炼。'}</strong>
          </div>
          <span className="practice-game-mode__sheet-wave">{NODE_STATUS_LABELS[node.status]}</span>
        </div>

        {node.targetWords[0] ? (
          <PracticePronunciationButton
            bookId={null}
            chapterId={null}
            targetWord={node.targetWords[0]}
            onEvaluated={() => {}}
          />
        ) : null}

        <div className="practice-game-mode__button-row">
          <button type="button" className="practice-game-mode__action" onClick={() => void onSubmitNode(true)} disabled={isSubmitting}>{isBoss ? '闯过 Boss' : '领取奖励'}</button>
          <button type="button" className="practice-game-mode__action is-secondary" onClick={() => void onSubmitNode(false)} disabled={isSubmitting}>{isBoss ? '稍后重打' : '先跳过'}</button>
        </div>

        {banner ? <BattleBanner tone={banner.tone} message={banner.message} /> : null}
        {error ? <div className="practice-game-mode__error">{error}</div> : null}
      </div>
    </section>
  )
}
