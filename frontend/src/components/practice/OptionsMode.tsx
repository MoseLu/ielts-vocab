// ── Options Mode Component (Listening / Meaning / Smart) ───────────────────────

import type { OptionsModeProps } from './types'
import { playExampleAudio } from './utils'
import {
  BottomBar,
  ListeningExamplePrompt,
  MeaningRecallInput,
  OptionsGrid,
  PrevWordBlock,
  SmartDictation,
  SmartDimBadge,
  WordDisplay,
} from './options/OptionsModeParts'

interface OptionsModePropsExtended extends OptionsModeProps {
  queueIndex: number
}

export default function OptionsMode({
  currentWord,
  previousWord,
  lastState,
  mode,
  smartDimension = 'meaning',
  options,
  optionsLoading = false,
  selectedAnswer,
  wrongSelections = [],
  showResult,
  correctIndex,
  spellingInput,
  spellingResult,
  speechConnected,
  speechRecording,
  settings,
  progressValue,
  total,
  queueIndex,
  favoriteSlot,
  onOptionSelect,
  onSkip,
  onGoBack,
  onSpellingSubmit,
  onSpellingInputChange,
  onStartRecording,
  onStopRecording,
  onPlayWord,
}: OptionsModePropsExtended) {
  const displayMode: 'audio' | 'definition' = mode === 'smart'
    ? (smartDimension === 'meaning' ? 'definition' : 'audio')
    : (mode === 'meaning' ? 'definition' : 'audio')
  const isSmartDictation = mode === 'smart' && smartDimension === 'dictation'
  const isMeaningRecall = mode === 'meaning' || (mode === 'smart' && smartDimension === 'meaning')
  const isChoiceLayout = !isSmartDictation && !isMeaningRecall
  const hasChoiceActionHeader = isChoiceLayout && mode !== 'smart' && Boolean(favoriteSlot)
  const listeningExample = currentWord.examples?.[0]?.en ?? ''
  const showListeningExample = displayMode === 'audio'
    && !optionsLoading
    && Boolean(listeningExample)
  const handlePlayExample = () => {
    if (!listeningExample) return
    playExampleAudio(listeningExample, currentWord.word, settings)
  }

  return (
    <div className={`practice-page${isChoiceLayout ? ' practice-page--choice' : ''}`}>
      <PrevWordBlock
        previousWord={previousWord}
        lastState={lastState}
        onGoBack={onGoBack}
        className={isChoiceLayout ? 'prev-word-inline--choice' : undefined}
      />

      <div className="practice-main">
        {(mode === 'smart' || favoriteSlot) && (
          <div className={`practice-main-header${hasChoiceActionHeader ? ' practice-main-header--choice-action' : ''}`}>
            <div className="practice-main-header__meta">
              {mode === 'smart' && <SmartDimBadge dimension={smartDimension} />}
            </div>
            {favoriteSlot ? (
              <div className="practice-main-header__action">{favoriteSlot}</div>
            ) : null}
          </div>
        )}

        {displayMode === 'definition' && (
          <WordDisplay
            currentWord={currentWord}
            displayMode={displayMode}
            onPlayWord={onPlayWord}
          />
        )}

        {showListeningExample && (
          <ListeningExamplePrompt
            sentence={listeningExample}
            targetWord={currentWord.word}
            onPlayAudio={handlePlayExample}
          />
        )}

        {isSmartDictation ? (
          <SmartDictation
            currentWord={currentWord}
            spellingInput={spellingInput}
            spellingResult={spellingResult}
            speechConnected={speechConnected}
            speechRecording={speechRecording}
            onSpellingInputChange={onSpellingInputChange}
            onSpellingSubmit={onSpellingSubmit}
            onStartRecording={onStartRecording}
            onStopRecording={onStopRecording}
            onPlayWord={onPlayWord}
          />
        ) : isMeaningRecall ? (
          <MeaningRecallInput
            currentWord={currentWord}
            spellingInput={spellingInput}
            spellingResult={spellingResult}
            speechConnected={speechConnected}
            speechRecording={speechRecording}
            onSpellingInputChange={onSpellingInputChange}
            onSpellingSubmit={onSpellingSubmit}
            onStartRecording={onStartRecording}
            onStopRecording={onStopRecording}
            onSkip={onSkip}
          />
        ) : (
          <>
            <OptionsGrid
              options={options}
              optionsLoading={optionsLoading}
              selectedAnswer={selectedAnswer}
              wrongSelections={wrongSelections}
              showResult={showResult}
              correctIndex={correctIndex}
              onOptionSelect={onOptionSelect}
            />

            <div className="options-footer">
              <button className="skip-btn" onClick={onSkip}>
                不知道 <span className="shortcut-hint">快捷键: 5</span>
              </button>
              <button
                className="replay-btn"
                onClick={() => onPlayWord(currentWord.word)}
                title="再读一遍，快捷键 Tab"
                aria-label="再读一遍，快捷键 Tab"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                </svg>
              </button>
            </div>
          </>
        )}

        <BottomBar progressValue={progressValue} total={total} queueIndex={queueIndex} />
      </div>
    </div>
  )
}
