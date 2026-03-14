import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

function shuffleArray(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function generateOptions(currentWord, allWords) {
  const correct = currentWord.definition
  const others = allWords.filter(w => w.definition !== correct).map(w => w.definition)
  const distractors = shuffleArray(others).slice(0, 3)
  const options = shuffleArray([correct, ...distractors])
  return { options, correctIndex: options.indexOf(correct) }
}

function PracticePage({ user, currentDay, mode, showToast }) {
  const navigate = useNavigate()
  const [vocabulary, setVocabulary] = useState([])
  const [queue, setQueue] = useState([])
  const [queueIndex, setQueueIndex] = useState(0)
  const [options, setOptions] = useState([])
  const [correctIndex, setCorrectIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [showResult, setShowResult] = useState(false)
  const [correctCount, setCorrectCount] = useState(0)
  const [wrongCount, setWrongCount] = useState(0)
  const [previousWord, setPreviousWord] = useState(null)
  // lastState enables single-level undo (back arrow)
  const [lastState, setLastState] = useState(null)
  const [spellingInput, setSpellingInput] = useState('')
  const [spellingResult, setSpellingResult] = useState(null)
  const [radioIndex, setRadioIndex] = useState(0)
  const spellingRef = useRef(null)
  const settings = (() => {
    try { return JSON.parse(localStorage.getItem('app_settings') || '{}') } catch { return {} }
  })()

  useEffect(() => {
    if (!currentDay) { navigate('/'); return }
    fetch(`/api/vocabulary/day/${currentDay}`)
      .then(res => res.json())
      .then(data => {
        const words = data.vocabulary || data.words || []
        setVocabulary(words)
        const indices = Array.from({ length: words.length }, (_, i) => i)
        setQueue(settings.shuffle !== false ? shuffleArray(indices) : indices)
        setQueueIndex(0); setCorrectCount(0); setWrongCount(0); setPreviousWord(null); setLastState(null)
      })
      .catch(() => showToast?.('加载词汇失败', 'error'))
  }, [currentDay])

  const currentWord = vocabulary[queue[queueIndex]]

  useEffect(() => {
    if (!currentWord || !vocabulary.length) return
    if (['listening', 'meaning', 'smart'].includes(mode)) {
      const { options: opts, correctIndex: ci } = generateOptions(currentWord, vocabulary)
      setOptions(opts); setCorrectIndex(ci)
    }
    setSelectedAnswer(null); setShowResult(false); setSpellingInput(''); setSpellingResult(null)
    if (['listening', 'dictation', 'radio'].includes(mode)) setTimeout(() => playWord(currentWord.word), 300)
    if (mode === 'dictation') setTimeout(() => spellingRef.current?.focus(), 400)
  }, [queueIndex, currentWord?.word, mode])

  // Radio mode sequential playback
  useEffect(() => {
    if (mode !== 'radio' || !vocabulary.length) return
    let cancelled = false
    ;(async () => {
      for (let i = 0; i < queue.length; i++) {
        if (cancelled) break
        setRadioIndex(i)
        const word = vocabulary[queue[i]]
        if (word) await new Promise(resolve => {
          const u = new SpeechSynthesisUtterance(word.word)
          u.rate = parseFloat(settings.playbackSpeed || '1.0')
          u.volume = parseFloat(settings.volume || '100') / 100
          u.onend = () => setTimeout(resolve, parseFloat(settings.interval || '2') * 1000)
          speechSynthesis.speak(u)
        })
      }
    })()
    return () => { cancelled = true; speechSynthesis.cancel() }
  }, [mode, vocabulary.length])

  const playWord = (word) => {
    speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(word)
    u.rate = parseFloat(settings.playbackSpeed || '1.0')
    u.volume = parseFloat(settings.volume || '100') / 100
    speechSynthesis.speak(u)
  }

  const saveProgress = useCallback((correct, wrong) => {
    const dayProgress = JSON.parse(localStorage.getItem('day_progress') || '{}')
    dayProgress[currentDay] = { correctCount: correct, wrongCount: wrong, completed: correct + wrong >= vocabulary.length, updatedAt: new Date().toISOString() }
    localStorage.setItem('day_progress', JSON.stringify(dayProgress))
    const token = localStorage.getItem('auth_token')
    if (token) fetch('/api/progress', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify({ day: currentDay, current_index: queueIndex, correct_count: correct, wrong_count: wrong }) }).catch(() => {})
  }, [currentDay, vocabulary.length, queueIndex])

  const saveWrongWord = (word) => {
    const existing = JSON.parse(localStorage.getItem('wrong_words') || '[]')
    if (!existing.find(w => w.word === word.word)) { existing.push(word); localStorage.setItem('wrong_words', JSON.stringify(existing)) }
  }

  const goNext = (wasCorrect) => {
    // Save state for undo
    setLastState({ qi: queueIndex, cc: correctCount, wc: wrongCount, prevWord: previousWord })
    setPreviousWord(currentWord)
    if (!wasCorrect && settings.repeatWrong !== false) {
      setQueue(prev => { const c = [...prev]; c.push(queue[queueIndex]); return c })
    }
    if (queueIndex + 1 >= queue.length) navigate('/')
    else setQueueIndex(prev => prev + 1)
  }

  const goBack = () => {
    if (!lastState) return
    setQueueIndex(lastState.qi)
    setCorrectCount(lastState.cc)
    setWrongCount(lastState.wc)
    setPreviousWord(lastState.prevWord)
    setLastState(null)
    setSelectedAnswer(null); setShowResult(false); setSpellingInput(''); setSpellingResult(null)
  }

  const handleOptionSelect = (idx) => {
    if (showResult) return
    setSelectedAnswer(idx); setShowResult(true)
    const isCorrect = idx === correctIndex
    const nc = isCorrect ? correctCount + 1 : correctCount
    const nw = isCorrect ? wrongCount : wrongCount + 1
    setCorrectCount(nc); setWrongCount(nw)
    if (!isCorrect) saveWrongWord(currentWord)
    saveProgress(nc, nw)
    setTimeout(() => goNext(isCorrect), 1200)
  }

  const handleSpellingSubmit = () => {
    if (spellingResult) return
    const isCorrect = spellingInput.trim().toLowerCase() === currentWord.word.toLowerCase()
    setSpellingResult(isCorrect ? 'correct' : 'wrong')
    const nc = isCorrect ? correctCount + 1 : correctCount
    const nw = isCorrect ? wrongCount : wrongCount + 1
    setCorrectCount(nc); setWrongCount(nw)
    if (!isCorrect) saveWrongWord(currentWord)
    saveProgress(nc, nw)
    setTimeout(() => goNext(isCorrect), 1500)
  }

  const handleSkip = () => {
    saveWrongWord(currentWord)
    const nw = wrongCount + 1
    setWrongCount(nw); saveProgress(correctCount, nw); goNext(false)
  }

  useEffect(() => {
    const handleKey = (e) => {
      if (e.target.tagName === 'INPUT') return
      if (showResult || spellingResult) return
      if (['listening', 'meaning', 'smart'].includes(mode)) {
        if (e.key >= '1' && e.key <= '4') { const idx = parseInt(e.key) - 1; if (idx < options.length) handleOptionSelect(idx) }
        if (e.key === '5') handleSkip()
        if (e.key === ' ') { e.preventDefault(); playWord(currentWord?.word) }
      }
      if (e.key === 'Escape') navigate('/')
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [showResult, spellingResult, options, mode, queueIndex])

  if (!vocabulary.length) {
    return <div className="practice-loading"><div className="loading-spinner"></div><p>加载词汇中...</p></div>
  }

  if (!currentWord) {
    return (
      <div className="practice-complete">
        <div className="complete-emoji">🎉</div>
        <h2>Day {currentDay} 完成！</h2>
        <div className="complete-stats-row">
          <span className="stat-correct">✓ 正确 {correctCount}</span>
          <span className="stat-wrong">✗ 错误 {wrongCount}</span>
        </div>
        <button className="complete-btn" onClick={() => navigate('/')}>返回主页</button>
      </div>
    )
  }

  const progress = queueIndex / Math.max(vocabulary.length, 1)
  const showWord = mode === 'meaning' || mode === 'smart'
  const showAudio = mode === 'listening' || mode === 'smart'

  // Previous word inline block (shared across modes)
  const PrevWordBlock = () => previousWord ? (
    <div className="prev-word-inline">
      <button className="prev-back-btn" onClick={goBack} disabled={!lastState} title="返回上一个词">
        ←
      </button>
      <div className="prev-word-info">
        <div className="prev-word-text">{previousWord.word}</div>
        <div className="prev-word-phonetic">{previousWord.phonetic}</div>
        <div className="prev-word-def">
          <span className="word-pos-tag">{previousWord.pos}</span>
          {previousWord.definition}
        </div>
      </div>
    </div>
  ) : null

  // Bottom bar with stats + progress (shared)
  const BottomBar = ({ progressValue, total }) => (
    <div className="practice-bottom-bar">
      <span className="bottom-stat-correct">✓ {correctCount}</span>
      <div className="bottom-progress-track">
        <div className="bottom-progress-fill" style={{ width: `${progressValue * 100}%` }}>
          <div className="bottom-progress-dot"></div>
        </div>
      </div>
      <span className="bottom-progress-count">{queueIndex + 1}/{total}</span>
      <span className="bottom-stat-wrong">✗ {wrongCount}</span>
    </div>
  )

  // RADIO MODE
  if (mode === 'radio') {
    const radioWord = vocabulary[queue[radioIndex]] || currentWord
    return (
      <div className="practice-page radio-mode">
        <PrevWordBlock />
        <div className="radio-container">
          <div className="radio-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="2"></circle>
              <path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"></path>
            </svg>
          </div>
          <div className="radio-word">{radioWord.word}</div>
          <div className="radio-phonetic">{radioWord.phonetic}</div>
          <div className="radio-definition"><span className="word-pos-tag">{radioWord.pos}</span>{radioWord.definition}</div>
        </div>
        <BottomBar progressValue={radioIndex / queue.length} total={queue.length} />
        <button className="radio-stop-btn" onClick={() => { speechSynthesis.cancel(); navigate('/') }}>停止播放</button>
      </div>
    )
  }

  // DICTATION MODE
  if (mode === 'dictation') {
    return (
      <div className="practice-page">
        <PrevWordBlock />
        <div className="dictation-container">
          <div className="dictation-play-area">
            <button className="play-btn-large" onClick={() => playWord(currentWord.word)}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
              </svg>
            </button>
            <p className="dictation-hint">听发音，拼写单词</p>
          </div>
          {spellingResult === 'wrong' && (
            <div className="spelling-answer">正确答案：<strong>{currentWord.word}</strong></div>
          )}
          <div className={`spelling-input-wrapper ${spellingResult || ''}`}>
            <input ref={spellingRef} type="text" className="spelling-input" value={spellingInput}
              onChange={e => setSpellingInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSpellingSubmit() }}
              placeholder="输入你听到的单词..." disabled={!!spellingResult}
              autoComplete="off" spellCheck={false} />
            {!spellingResult && <button className="spelling-submit-btn" onClick={handleSpellingSubmit}>确认</button>}
          </div>
          <div className="dictation-definition">
            <span className="word-pos-tag">{currentWord.pos}</span>{currentWord.definition}
          </div>
        </div>
        <button className="skip-btn" onClick={handleSkip}>不知道 <span className="shortcut-hint">(5)</span></button>
        <BottomBar progressValue={progress} total={vocabulary.length} />
      </div>
    )
  }

  // LISTENING / MEANING / SMART MODE
  return (
    <div className="practice-page">
      <PrevWordBlock />

      {/* Main practice area */}
      <div className="practice-main">
        {/* Word / Audio */}
        <div className="word-display-area">
          {showAudio && (
            <button className="play-btn-large" onClick={() => playWord(currentWord.word)}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
              </svg>
            </button>
          )}
          {showWord && (
            <div className="word-display">
              <div className="word-text">{currentWord.word}</div>
              <div className="word-phonetic">{currentWord.phonetic}</div>
            </div>
          )}
        </div>

        {/* Options */}
        <div className="options-grid">
          {options.map((option, idx) => {
            let cls = 'option-btn'
            if (showResult) {
              if (idx === correctIndex) cls += ' correct'
              else if (idx === selectedAnswer) cls += ' wrong'
            } else if (selectedAnswer === idx) cls += ' selected'
            return (
              <button key={idx} className={cls} onClick={() => handleOptionSelect(idx)} disabled={showResult}>
                <span className="option-key">{idx + 1}</span>
                <span className="option-text">{option}</span>
              </button>
            )
          })}
        </div>

        <button className="skip-btn" onClick={handleSkip}>
          不知道 <span className="shortcut-hint">(5)</span>
        </button>
      </div>

      <BottomBar progressValue={progress} total={vocabulary.length} />
    </div>
  )
}

export default PracticePage
