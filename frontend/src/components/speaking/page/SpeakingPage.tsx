import { useSearchParams } from 'react-router-dom'

import { Page, PageScroll } from '../../layout/Page'
import {
  SPEAKING_SETS,
  clampSpeakingPromptIndex,
  getSpeakingSet,
  parsePromptIndex,
} from './speakingPageShared'

function getOpeningQuestionText(themeId: string) {
  const set = getSpeakingSet(themeId)
  const firstQuestion = set?.prompts.find(prompt => prompt.kind === 'question')
  return firstQuestion?.text ?? ''
}

function SpeakingPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedSet = getSpeakingSet(searchParams.get('theme'))
  const promptIndex = clampSpeakingPromptIndex(
    parsePromptIndex(searchParams.get('step')),
    selectedSet,
  )
  const activePrompt = selectedSet ? selectedSet.prompts[promptIndex] : null

  const openTheme = (themeId: string) => {
    setSearchParams({ theme: themeId, step: '0' })
  }

  const leaveTheme = () => {
    setSearchParams({})
  }

  const movePrompt = (delta: number) => {
    if (!selectedSet) {
      return
    }

    const nextIndex = clampSpeakingPromptIndex(promptIndex + delta, selectedSet)
    setSearchParams({ theme: selectedSet.id, step: String(nextIndex) })
  }

  if (!selectedSet || !activePrompt) {
    return (
      <Page className="speaking-page">
        <PageScroll>
          <div className="speaking-page__shell">
            <section className="speaking-page__library" aria-label="口语题目选择">
              <div className="speaking-page__library-bar">
                <div className="speaking-page__library-copy">
                  <p className="speaking-page__library-note">选择一个主题，直接进入整套题目流程。</p>
                </div>
                <span className="speaking-page__library-count">{SPEAKING_SETS.length} 套</span>
              </div>

              <div className="speaking-page__topic-list">
                {SPEAKING_SETS.map((item, index) => (
                  <button
                    key={item.id}
                    type="button"
                    className="speaking-page__topic-card"
                    onClick={() => openTheme(item.id)}
                  >
                    <div className="speaking-page__topic-card-top">
                      <span className="speaking-page__topic-index">{String(index + 1).padStart(2, '0')}</span>
                      <span className="speaking-page__topic-count">{item.prompts.length} 道题</span>
                    </div>

                    <div className="speaking-page__topic-card-body">
                      <strong className="speaking-page__topic-title">{item.theme}</strong>
                      <p className="speaking-page__topic-preview">{item.preview}</p>
                      <div className="speaking-page__topic-structure" aria-hidden="true">
                        <span className="speaking-page__topic-chip">快问 5</span>
                        <span className="speaking-page__topic-chip">长答 1</span>
                        <span className="speaking-page__topic-chip">讨论 4</span>
                      </div>
                      <p className="speaking-page__topic-sample">{getOpeningQuestionText(item.id)}</p>
                    </div>

                    <span className="speaking-page__topic-arrow" aria-hidden="true">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M5 12h14" />
                        <path d="M13 5l7 7-7 7" />
                      </svg>
                    </span>
                  </button>
                ))}
              </div>
            </section>
          </div>
        </PageScroll>
      </Page>
    )
  }

  return (
    <Page className="speaking-page">
      <PageScroll>
        <div className="speaking-page__shell">
          <section className="speaking-page__exam" aria-label={`${selectedSet.theme} 口语考试流程`}>
            <div className="speaking-page__toolbar">
              <button
                type="button"
                className="speaking-page__ghost-button"
                onClick={leaveTheme}
              >
                换题目
              </button>

              <div className="speaking-page__toolbar-meta">
                <span className="speaking-page__theme-chip">{selectedSet.theme}</span>
                <span className="speaking-page__step-count">
                  {promptIndex + 1} / {selectedSet.prompts.length}
                </span>
              </div>

              <div className="speaking-page__toolbar-actions">
                <button
                  type="button"
                  className="speaking-page__nav-button"
                  onClick={() => movePrompt(-1)}
                  disabled={promptIndex === 0}
                >
                  上一题
                </button>
                <button
                  type="button"
                  className="speaking-page__nav-button"
                  onClick={() => movePrompt(1)}
                  disabled={promptIndex === selectedSet.prompts.length - 1}
                >
                  下一题
                </button>
              </div>
            </div>

            <article
              key={`${selectedSet.id}-${activePrompt.id}`}
              className={`speaking-page__prompt-frame speaking-page__prompt-frame--${activePrompt.kind}`}
            >
              {activePrompt.kind === 'question' ? (
                <p className="speaking-page__prompt-text">{activePrompt.text}</p>
              ) : (
                <div className="speaking-page__cue-card">
                  <div className="speaking-page__cue-meta">
                    <span>{activePrompt.prepLabel}</span>
                    <span>{activePrompt.answerLabel}</span>
                  </div>
                  <p className="speaking-page__prompt-text">{activePrompt.prompt}</p>
                  <ul className="speaking-page__cue-points">
                    {activePrompt.bullets.map(item => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </article>

            <div className="speaking-page__progress" aria-hidden="true">
              {selectedSet.prompts.map((item, index) => (
                <span
                  key={item.id}
                  className={[
                    'speaking-page__progress-segment',
                    index < promptIndex ? 'is-complete' : '',
                    index === promptIndex ? 'is-active' : '',
                  ].filter(Boolean).join(' ')}
                />
              ))}
            </div>
          </section>
        </div>
      </PageScroll>
    </Page>
  )
}

export default SpeakingPage
