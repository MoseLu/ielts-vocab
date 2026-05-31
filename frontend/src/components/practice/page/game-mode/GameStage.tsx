import type { GameCampaignNode } from '../../../../lib'
import PracticePronunciationButton from '../PracticePronunciationButton'
import { BossTopHud } from './GameBattleHud'
import { prdMobileSceneBackdrop, prdSceneBackdropForKind } from './GamePrdUi'
import { GameTemplateDebugLayer } from './GameTemplateDebugLayer'
import { SpeakingRecorder } from './GameSpeakingRecorder'
import {
  BattleBanner,
  ChoiceGrid,
  DimensionDefenseStrip,
  MOBILE_MISSION_SLOT_BY_DESKTOP_SLOT,
  WordMissionWave,
  WordScene,
  missionSlotStyle,
} from './GameWordMissionParts'
import { gameAsset } from './gameAssets'
import {
  LEVEL_KIND_LABELS,
  NODE_STATUS_LABELS,
  NODE_TYPE_LABELS,
  buildDefinitionChoices,
  buildExampleChallenge,
  buildListeningWordChoices,
  getLevelKind,
  normalizeAnswer,
  playGameWordAudio,
} from '../../../../features/practice/gameMode/gameData'

type AttemptMeta = {
  inputMode?: string
  hintUsed?: boolean
  boostType?: string
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
          <WordMissionWave word={word} />
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
