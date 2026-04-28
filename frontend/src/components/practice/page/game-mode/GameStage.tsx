import { useCallback, useState } from 'react'
import { useSpeechRecognition } from '../../../../hooks/useSpeechRecognition'
import type { GameCampaignNode, GameCampaignWord, GameLevelKind } from '../../../../lib'
import PracticePronunciationButton from '../PracticePronunciationButton'
import { BattleTopHud, BossTopHud, ObjectivePanel, ThreatRoute } from './GameBattleHud'
import { prdMobileSceneBackdrop, prdSceneBackdropForKind } from './GamePrdUi'
import { GameTemplateDebugLayer } from './GameTemplateDebugLayer'
import { gameAsset } from './gameAssets'
import { type GameTemplateLayoutId, layoutSlotStyle, responsiveLayoutSlotStyle } from './gameTemplateLayout'
import {
  LEVEL_KIND_LABELS,
  NODE_STATUS_LABELS,
  NODE_TYPE_LABELS,
  buildDefinitionChoices,
  buildExampleChallenge,
  buildListeningWordChoices,
  getLevelKind,
  getWaveNumber,
  normalizeAnswer,
  playGameWordAudio,
} from './gameData'

type AttemptMeta = {
  inputMode?: string
  hintUsed?: boolean
  boostType?: string
}

const WORD_DIMENSION_ITEMS: Array<{ kind: GameLevelKind; dimension: keyof GameCampaignWord['dimension_states'] }> = [
  { kind: 'speaking', dimension: 'recognition' },
  { kind: 'definition', dimension: 'meaning' },
  { kind: 'spelling', dimension: 'dictation' },
  { kind: 'pronunciation', dimension: 'speaking' },
  { kind: 'example', dimension: 'listening' },
]

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

function DimensionDefenseStrip({
  word,
  activeKind,
}: {
  word: GameCampaignWord
  activeKind: GameLevelKind
}) {
  const completedCount = WORD_DIMENSION_ITEMS.filter(item => (
    (word.dimension_states[item.dimension]?.pass_streak ?? 0) >= 1
  )).length

  return (
    <section className="practice-game-mode__dimension-defense" aria-label="当前词五维防线">
      <div className="practice-game-mode__dimension-defense-head">
        <span>当前词五维防线</span>
        <strong>{completedCount}/5</strong>
      </div>
      <div className="practice-game-mode__dimension-defense-row">
        {WORD_DIMENSION_ITEMS.map(item => {
          const passStreak = word.dimension_states[item.dimension]?.pass_streak ?? 0
          const statusKey = item.kind === activeKind ? 'active' : passStreak >= 1 ? 'passed' : 'locked'
          const status = statusKey === 'active' ? '当前' : statusKey === 'passed' ? '已过' : '待解锁'
          return (
            <span key={item.kind} className={`practice-game-mode__dimension-chip is-${statusKey}`}>
              <span className="practice-game-mode__dimension-chip-core" aria-hidden="true" />
              <strong>{LEVEL_KIND_LABELS[item.kind]}</strong>
              <small>{status}</small>
            </span>
          )
        })}
      </div>
    </section>
  )
}

function sceneAssetForLevel(levelKind: GameLevelKind, variant: 'mission' | 'refill' = 'mission') { return prdSceneBackdropForKind(levelKind, variant) }

const MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT: Record<string, string> = {
  'mission.hud': 'mobileMission.hud', 'mission.route': 'mobileMission.route',
  'mission.objective': 'mobileMission.objective', 'mission.answerPanel': 'mobileMission.answerPanel',
  'refill.hud': 'mobileMission.hud', 'refill.list': 'mobileMission.route',
  'refill.objective': 'mobileMission.objective', 'refill.answerPanel': 'mobileMission.answerPanel',
}

function missionSlotStyle(layoutId: GameTemplateLayoutId, slotId: string) {
  const mobileSlotId = MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT[slotId]
  if (!mobileSlotId) return layoutSlotStyle(layoutId, slotId)
  return responsiveLayoutSlotStyle(layoutId, slotId, 'mobileWordMission', mobileSlotId)
}

function WordScene({
  node,
  word,
  levelKind,
  layoutId,
  sceneVariant = 'mission',
  onExitToMap,
}: {
  node: GameCampaignNode
  word: GameCampaignWord
  levelKind: GameLevelKind
  layoutId: Extract<GameTemplateLayoutId, 'wordMission' | 'refillState'>
  sceneVariant?: 'mission' | 'refill'
  onExitToMap?: () => void
}) {
  const image = word.image
  const showSceneImage = image.status === 'ready' && Boolean(image.url)
  const [hudSlot, routeSlot, objectiveSlot] = layoutId === 'refillState'
    ? ['refill.hud', 'refill.list', 'refill.objective']
    : ['mission.hud', 'mission.route', 'mission.objective']

  return (
    <div className={`practice-game-mode__scene practice-game-mode__scene--${levelKind} is-${image.status}`}>
      <picture aria-hidden="true">
        <source media="(max-width: 640px)" srcSet={prdMobileSceneBackdrop()} />
        <img src={sceneAssetForLevel(levelKind, sceneVariant)} alt="" className="practice-game-mode__scene-backdrop" />
      </picture>
      <GameTemplateDebugLayer layoutId={layoutId} mobileLayoutId="mobileWordMission" />
      {showSceneImage ? <img src={image.url ?? undefined} alt={image.alt} className="practice-game-mode__scene-image" /> : null}
      <div className="practice-game-mode__scene-overlay" />
      <BattleTopHud
        node={node}
        word={word}
        levelKind={levelKind}
        onExitToMap={onExitToMap}
        slotId={hudSlot}
        mobileSlotId={MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT[hudSlot]}
        slotStyle={missionSlotStyle(layoutId, hudSlot)}
      />
      <ThreatRoute
        slotId={routeSlot}
        mobileSlotId={MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT[routeSlot]}
        slotStyle={missionSlotStyle(layoutId, routeSlot)}
      />
      <ObjectivePanel
        word={word}
        levelKind={levelKind}
        slotId={objectiveSlot}
        mobileSlotId={MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT[objectiveSlot]}
        slotStyle={missionSlotStyle(layoutId, objectiveSlot)}
      />
      <div className="practice-game-mode__coach-line">
        <img src={gameAsset.character.robot} alt="" aria-hidden="true" />
        <span>{image.status === 'ready' ? '图像情报已同步。' : image.status === 'failed' ? '图像情报缺失，使用基础战场。' : '图像情报生成中，先守住当前波。'}</span>
      </div>
      <div className="practice-game-mode__scene-caption">
        <strong>{word.definition}</strong>
        <span>{word.pos || 'IELTS vocabulary'} · {LEVEL_KIND_LABELS[levelKind]}</span>
      </div>
    </div>
  )
}

function SpeakingRecorder({
  targetWord,
  prompt,
  disabled,
  onEvaluated,
}: {
  targetWord: string
  prompt: string
  disabled: boolean
  onEvaluated: (passed: boolean, transcript: string) => void
}) {
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)
  const {
    isConnected,
    isRecording,
    isProcessing,
    startRecording,
    stopRecording,
  } = useSpeechRecognition({
    enabled: true,
    language: 'en',
    enableVad: true,
    autoStop: true,
    onPartial: text => {
      setTranscript(text)
      setError(null)
    },
    onResult: text => {
      const normalizedTranscript = normalizeAnswer(text)
      setTranscript(text)
      onEvaluated(
        normalizedTranscript.includes(normalizeAnswer(targetWord)),
        normalizedTranscript,
      )
    },
    onError: message => setError(message),
  })

  const lowerError = String(error || '').toLowerCase()
  const micIcon = error
    ? (lowerError.includes('permission') || error.includes('权限')
      ? gameAsset.mic.permissionFail
      : gameAsset.mic.disconnected)
    : isProcessing
      ? gameAsset.mic.recognizing
      : isRecording
        ? gameAsset.mic.recording
        : !isConnected
          ? gameAsset.mic.disconnected
          : gameAsset.mic.idle

  const handleToggle = useCallback(async () => {
    if (disabled || isProcessing) return
    if (isRecording) {
      stopRecording()
      return
    }
    setTranscript('')
    setError(null)
    await startRecording()
  }, [disabled, isProcessing, isRecording, startRecording, stopRecording])

  return (
    <div className="practice-game-speaking">
      <div className="practice-game-speaking__status">
        <img src={micIcon} alt="" aria-hidden="true" className="practice-game-speaking__icon" />
        <strong>{isProcessing ? '识别中' : isRecording ? '录音中' : error ? '录音异常' : !isConnected ? '语音未连接' : '准备录音'}</strong>
      </div>
      <p>{prompt}</p>
      <div className="practice-game-speaking__transcript">
        {transcript || '点击录音后，说一句包含目标词的英文短句。'}
      </div>
      {error ? <div className="practice-game-mode__error">{error}</div> : null}
      <button
        type="button"
        className={`practice-game-mode__action${isRecording ? ' is-recording' : ''}`}
        onClick={() => void handleToggle()}
        disabled={disabled || (!isConnected && !isRecording) || isProcessing}
      >
        {isProcessing ? '识别中...' : isRecording ? '结束录音' : '开始录音'}
      </button>
      {!isConnected && !isRecording ? <small>语音服务未连接，暂时不能录音。</small> : null}
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
  forceRefillLayout = false,
  onAnswerChange,
  onSelectChoice,
  onSubmitAttempt,
  onRefreshAfterSpeaking,
  onExitToMap,
}: {
  node: GameCampaignNode
  bookId: string | null
  chapterId: string | null
  answerInput: string
  selectedChoice: string | null
  isSubmitting: boolean
  banner: { tone: 'success' | 'warning'; message: string } | null
  error: string | null
  forceRefillLayout?: boolean
  onAnswerChange: (value: string) => void
  onSelectChoice: (value: string | null) => void
  onSubmitAttempt: (passed: boolean, meta?: AttemptMeta) => Promise<void>
  onRefreshAfterSpeaking: (passed: boolean) => void
  onExitToMap?: () => void
}) {
  const word = node.word
  if (!word) return null
  const levelKind = getLevelKind(node)
  const definitionChoices = buildDefinitionChoices(word)
  const listeningChoices = buildListeningWordChoices(word)
  const exampleChallenge = buildExampleChallenge(word)
  const selectedDefinition = definitionChoices.find(choice => choice.key === selectedChoice)
  const selectedListening = listeningChoices.find(choice => choice.key === selectedChoice)
  const selectedExample = exampleChallenge.choices.find(choice => choice.key === selectedChoice)
  const useRefillLayout = forceRefillLayout || banner?.tone === 'warning' || Boolean(error)
  const layoutId = useRefillLayout ? 'refillState' : 'wordMission'
  const answerSlot = layoutId === 'refillState' ? 'refill.answerPanel' : 'mission.answerPanel'

  return (
    <section className="practice-game-mode__battle-screen">
      <WordScene
        node={node}
        word={word}
        levelKind={levelKind}
        layoutId={layoutId}
        sceneVariant={useRefillLayout ? 'refill' : 'mission'}
        onExitToMap={onExitToMap}
      />
      <div
        className="practice-game-mode__sheet practice-template-slot"
        data-layout-slot={answerSlot}
        data-mobile-layout-slot={MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT[answerSlot]}
        style={missionSlotStyle(layoutId, answerSlot)}
      >
        <DimensionDefenseStrip word={word} activeKind={levelKind} />

        <div className="practice-game-mode__sheet-head">
          <div>
            <span className="practice-game-mode__sheet-eyebrow">{LEVEL_KIND_LABELS[levelKind]}</span>
            <strong>{LEVEL_KIND_LABELS[levelKind]}</strong>
          </div>
          <span className="practice-game-mode__sheet-wave">第 {getWaveNumber(word)}/4 波</span>
        </div>

        {levelKind === 'spelling' ? (
          <div className="practice-game-mode__task is-spelling">
            <button type="button" className="practice-game-mode__action is-secondary" onClick={() => playGameWordAudio(word.word)}>播放单词</button>
            <div className="practice-game-mode__input-row">
              <input
                value={answerInput}
                onChange={event => onAnswerChange(event.target.value)}
                placeholder="输入完整拼写"
                disabled={isSubmitting}
                className="practice-game-mode__input"
              />
              <button type="button" className="practice-game-mode__action" onClick={() => void onSubmitAttempt(normalizeAnswer(answerInput) === normalizeAnswer(word.word), { inputMode: 'typing' })} disabled={isSubmitting || !answerInput.trim()}>
                检查
              </button>
            </div>
          </div>
        ) : null}

        {levelKind === 'pronunciation' ? (
          <div className="practice-game-mode__task is-pronunciation">
            <PracticePronunciationButton
              bookId={bookId}
              chapterId={chapterId}
              targetWord={word.word}
              targetPhonetic={word.phonetic}
              onEvaluated={result => onRefreshAfterSpeaking(result.passed)}
            />
          </div>
        ) : null}

        {levelKind === 'definition' ? (
          <div className="practice-game-mode__task">
            <ChoiceGrid choices={definitionChoices} selectedChoice={selectedChoice} onSelectChoice={value => onSelectChoice(value)} />
            <button type="button" className="practice-game-mode__action" onClick={() => void onSubmitAttempt(Boolean(selectedDefinition?.correct), { inputMode: 'choice' })} disabled={isSubmitting || !selectedDefinition}>
              检查
            </button>
          </div>
        ) : null}

        {levelKind === 'speaking' ? (
          <div className="practice-game-mode__task">
            <button type="button" className="practice-game-mode__action is-secondary" onClick={() => playGameWordAudio(word.word)}>播放单词</button>
            <ChoiceGrid choices={listeningChoices} selectedChoice={selectedChoice} onSelectChoice={value => onSelectChoice(value)} />
            <button type="button" className="practice-game-mode__action" onClick={() => void onSubmitAttempt(Boolean(selectedListening?.correct), { inputMode: 'choice' })} disabled={isSubmitting || !selectedListening}>
              检查
            </button>
          </div>
        ) : null}

        {levelKind === 'example' ? (
          <div className="practice-game-mode__task">
            <div className="practice-game-mode__example-sentence">{exampleChallenge.sentence}</div>
            {exampleChallenge.translation ? <small>{exampleChallenge.translation}</small> : null}
            <ChoiceGrid choices={exampleChallenge.choices} selectedChoice={selectedChoice} onSelectChoice={value => onSelectChoice(value)} />
            <button type="button" className="practice-game-mode__action" onClick={() => void onSubmitAttempt(Boolean(selectedExample?.correct), { inputMode: 'choice', boostType: 'application' })} disabled={isSubmitting || !selectedExample}>
              检查
            </button>
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
  onExitToMap,
}: {
  node: GameCampaignNode
  isSubmitting: boolean
  banner: { tone: 'success' | 'warning'; message: string } | null
  error: string | null
  onSubmitNode: (passed: boolean, meta?: AttemptMeta) => Promise<void>
  onExitToMap?: () => void
}) {
  const targetWord = node.targetWords[0] ?? ''
  const isBoss = node.nodeType === 'speaking_boss'
  const layoutId = 'wordMission'

  return (
    <section className="practice-game-mode__battle-screen">
      <div className={`practice-game-mode__scene practice-game-mode__scene--boss${isBoss ? ' is-boss' : ''}`}>
        <picture aria-hidden="true">
          <source media="(max-width: 640px)" srcSet={prdMobileSceneBackdrop()} />
          <img src={prdSceneBackdropForKind('speaking')} alt="" className="practice-game-mode__scene-backdrop" />
        </picture>
        <GameTemplateDebugLayer layoutId={layoutId} mobileLayoutId="mobileWordMission" />
        <div className="practice-game-mode__scene-overlay" />
        <BossTopHud
          node={node}
          isBoss={isBoss}
          onExitToMap={onExitToMap}
          slotId="mission.hud"
          mobileSlotId={MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT['mission.hud']}
          slotStyle={missionSlotStyle(layoutId, 'mission.hud')}
        />
        <div className="practice-game-mode__scene-head">
          <span>{NODE_TYPE_LABELS[node.nodeType]}</span>
          <span>{isBoss ? `重打 ${node.bossFailures} 次` : `失手 ${node.rewardFailures} 次`}</span>
          <span>{NODE_STATUS_LABELS[node.status]}</span>
        </div>
        <div className="practice-game-mode__scene-coach is-large">
          <img src={gameAsset.character.teacher} alt="" aria-hidden="true" />
          <span>{isBoss ? '段末结算战' : '奖励口语关'}</span>
          <strong>{node.title}</strong>
          <small>{node.subtitle}</small>
        </div>
        {node.targetWords.length > 0 ? (
          <div className="practice-game-mode__token-row">
            {node.targetWords.map(word => (
              <span key={word} className="practice-game-mode__token-chip">{word}</span>
            ))}
          </div>
        ) : null}
      </div>

      <div
        className="practice-game-mode__sheet practice-template-slot"
        data-layout-slot="mission.answerPanel"
        data-mobile-layout-slot={MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT['mission.answerPanel']}
        style={missionSlotStyle(layoutId, 'mission.answerPanel')}
      >
        <div className="practice-game-mode__sheet-head">
          <div>
            <span className="practice-game-mode__sheet-eyebrow">{NODE_TYPE_LABELS[node.nodeType]}</span>
            <strong>{node.promptText || '围绕目标词完成口语试炼。'}</strong>
          </div>
          <span className="practice-game-mode__sheet-wave">{NODE_STATUS_LABELS[node.status]}</span>
        </div>

        {targetWord ? (
          <SpeakingRecorder
            targetWord={targetWord}
            prompt={node.promptText || `围绕 ${targetWord} 说一句英文。`}
            disabled={isSubmitting}
            onEvaluated={passed => void onSubmitNode(passed, { inputMode: 'speech' })}
          />
        ) : null}
        <button type="button" className="practice-game-mode__action is-secondary" onClick={() => void onSubmitNode(false, { inputMode: 'skip' })} disabled={isSubmitting}>
          稍后重打
        </button>

        {banner ? <BattleBanner tone={banner.tone} message={banner.message} /> : null}
        {error ? <div className="practice-game-mode__error">{error}</div> : null}
      </div>
    </section>
  )
}
