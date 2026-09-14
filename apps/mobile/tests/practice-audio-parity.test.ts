import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'

const mobileRoot = new URL('..', import.meta.url).pathname
const workspaceRoot = join(mobileRoot, '..', '..')

function read(relativePath: string): string {
  return readFileSync(join(workspaceRoot, relativePath), 'utf8')
}

describe('mobile audio practice parity contract', () => {
  it('keeps listening and dictation replay wired through a shared audio-mode hook', () => {
    const screenSource = read('apps/mobile/src/screens/PracticeScreen.tsx')
    const hookSource = read('apps/mobile/src/features/practice/runtime/usePracticeAudioModes.ts')

    assert.match(screenSource, /usePracticeAudioModes\(/)
    assert.match(screenSource, /testID="practice\.audio\.replay"/)
    assert.match(hookSource, /AUTO_REPLAY_DELAY_MS/)
    assert.match(hookSource, /isAutoReplayMode\(mode\)/)
    assert.match(hookSource, /playWord\('auto'\)/)
    assert.match(hookSource, /requestIdRef\.current \+= 1/)
  })

  it('shows explicit dictation spelling feedback and replays after a wrong spelling', () => {
    const screenSource = read('apps/mobile/src/screens/PracticeScreen.tsx')
    const feedbackSource = read('apps/mobile/src/features/practice/runtime/practiceFeedback.ts')
    const answerSubmissionSource = read('apps/mobile/src/features/practice/runtime/usePracticeAnswerSubmission.ts')

    assert.match(feedbackSource, /buildDictationFeedback/)
    assert.match(feedbackSource, /拼写不一致/)
    assert.match(answerSubmissionSource, /params\.activeMode === 'dictation' && !result\.correct/)
    assert.match(answerSubmissionSource, /buildDictationFeedback\(value, result\.expected\)/)
    assert.match(answerSubmissionSource, /void params\.playWord\('auto'\)/)
    assert.match(screenSource, /usePracticeAnswerSubmission\(/)
  })

  it('gates follow completion on recognized speech text instead of a hardcoded success token', () => {
    const screenSource = read('apps/mobile/src/screens/PracticeScreen.tsx')
    const coreSource = read('packages/app-core/src/practiceEngine.ts')

    assert.match(screenSource, /const followTranscript = \(speechState\.finalText \|\| speechState\.partialText \|\| ''\)\.trim\(\)/)
    assert.match(screenSource, /disabled=\{!followTranscript\}/)
    assert.match(screenSource, /submit\(followTranscript\)/)
    assert.equal(screenSource.includes("submit('followed')"), false)
    assert.match(coreSource, /还没有识别到跟读内容/)
  })

  it('adds radio play-pause-next progression and visible interaction recording', () => {
    const screenSource = read('apps/mobile/src/screens/PracticeScreen.tsx')
    const hookSource = read('apps/mobile/src/features/practice/runtime/usePracticeAudioModes.ts')

    assert.match(screenSource, /testID="practice\.radio\.toggle"/)
    assert.match(screenSource, /testID="practice\.radio\.next"/)
    assert.match(screenSource, /radioInteractionCount/)
    assert.match(hookSource, /RADIO_NEXT_DELAY_MS/)
    assert.match(hookSource, /recordRadioInteraction/)
    assert.match(hookSource, /scheduleRadioAdvance/)
    assert.match(hookSource, /onRadioAdvanceRef\.current\(\)/)
  })
})
