import { PageSkeleton } from '../../ui'
import { useVocabTestPage } from '../../../composables/vocab-test/page/useVocabTestPage'

function ResultScreen({
  result,
  onRestart,
  onBack,
}: {
  result: NonNullable<ReturnType<typeof useVocabTestPage>['result']>
  onRestart: () => void
  onBack: () => void
}) {
  const pct = result.accuracy
  const ringToneClass = pct >= 80 ? 'result-ring-progress--success' : pct >= 50 ? 'result-ring-progress--accent' : 'result-ring-progress--error'
  const circumference = 2 * Math.PI * 52
  const dashOffset = circumference * (1 - pct / 100)

  return (
    <div className="vocab-test-result">
      <div className="result-ring-wrap">
        <svg width="130" height="130" viewBox="0 0 130 130">
          <circle cx="65" cy="65" r="52" fill="none" stroke="var(--border)" strokeWidth="10" />
          <circle
            cx="65"
            cy="65"
            r="52"
            fill="none"
            className={ringToneClass}
            strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            transform="rotate(-90 65 65)"
          />
        </svg>
        <div className="result-ring-label">
          <div className="result-pct">{pct}%</div>
          <div className="result-score">{result.correct}/{result.total}</div>
        </div>
      </div>

      <div className="result-msg">
        {pct >= 90 ? '太棒了，词汇量很稳。' :
         pct >= 70 ? '表现不错，继续保持。' :
         pct >= 50 ? '还需要加强，继续练习。' :
         '建议多听多读，继续积累词汇。'}
      </div>

      {result.wrongWords.length > 0 && (
        <div className="result-wrong-section">
          <div className="result-wrong-title">需要加强的词汇：</div>
          {result.wrongWords.map(word => (
            <div key={word.word} className="result-wrong-item">
              <span className="result-wrong-word">{word.word}</span>
              <span className="result-wrong-def">{word.definition}</span>
            </div>
          ))}
        </div>
      )}

      <div className="result-actions">
        <button className="result-btn primary" onClick={onRestart}>再测一次</button>
        <button className="result-btn" onClick={onBack}>返回</button>
      </div>
    </div>
  )
}

export default function VocabTestPage() {
  const {
    loading,
    error,
    questions,
    currentQuestion,
    qIndex,
    selected,
    showResult,
    result,
    handleBack,
    handleRestart,
    handleNext,
    handleOptionSelect,
    replayCurrentQuestion,
  } = useVocabTestPage()

  if (loading) {
    return (
      <div className="vocab-test">
        <PageSkeleton variant="quiz" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="vocab-test">
        <div className="vocab-test-error">
          <p>{error}</p>
          <button onClick={handleBack}>返回</button>
        </div>
      </div>
    )
  }

  if (showResult && result) {
    return (
      <div className="vocab-test">
        <div className="vocab-test-header">
          <button className="vocab-test-back" onClick={handleBack}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        </div>
        <ResultScreen
          result={result}
          onRestart={handleRestart}
          onBack={handleBack}
        />
      </div>
    )
  }

  if (!currentQuestion) return null

  return (
    <div className="vocab-test">
      <div className="vocab-test-header">
        <button className="vocab-test-back" onClick={handleBack}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="vocab-test-progress">
          {qIndex + 1} / {questions.length}
        </div>
      </div>

      <div className="vocab-test-card">
        <button className="vocab-test-audio" onClick={replayCurrentQuestion}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
          </svg>
        </button>

        <div className="vocab-test-options">
          {currentQuestion.options.map((option, index) => {
            const isSelected = selected === index
            const isCorrect = option.correct
            const statusClass = selected === null
              ? ''
              : isCorrect
                ? ' correct'
                : isSelected
                  ? ' wrong'
                  : ''

            return (
              <button
                key={`${currentQuestion.word.word}-${option.text}`}
                className={`vocab-test-option${statusClass}`}
                onClick={() => handleOptionSelect(index)}
                disabled={selected !== null}
              >
                <span className="vocab-test-option-index">{index + 1}</span>
                <span>{option.text}</span>
              </button>
            )
          })}
        </div>

        <div className="vocab-test-actions">
          <button className="vocab-test-secondary" onClick={replayCurrentQuestion}>
            再听一遍
          </button>
          <button
            className="vocab-test-primary"
            onClick={handleNext}
            disabled={selected === null}
          >
            {qIndex + 1 >= questions.length ? '查看结果' : '下一题'}
          </button>
        </div>
      </div>
    </div>
  )
}
