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

// ── Syllabification helpers ─────────────────────────────────────────────────
// IPA vowel characters (excluding stress/length markers)
const IPA_VOWELS = 'aeiouəɪʊʌæɒɔɑɛɜɐøœɨɯɵ'

function countPhoneticSyllables(phonetic) {
  const ipa = phonetic.replace(/[/[\]ˈˌ.ː]/g, '')
  let count = 0
  let i = 0
  while (i < ipa.length) {
    if (IPA_VOWELS.includes(ipa[i])) {
      count++
      i++
      // skip remainder of diphthong/triphthong
      while (i < ipa.length && IPA_VOWELS.includes(ipa[i])) i++
    } else i++
  }
  return Math.max(1, count)
}

const VALID_ONSET2 = new Set([
  'bl','br','ch','cl','cr','dr','dw','fl','fr','gl','gr','kl','kn',
  'ph','pl','pr','sc','sh','sk','sl','sm','sn','sp','st','sw','th','tr','tw','wh','wr',
])
const VALID_ONSET3 = new Set(['str','scr','spr','spl','squ','thr','chr'])

function syllabifyWord(word, phonetic) {
  const n = countPhoneticSyllables(phonetic)
  if (n <= 1 || word.length <= 2) return [word]

  const lower = word.toLowerCase()
  const isVowel = (ch, i) => {
    if ('aeiou'.includes(ch)) return true
    if (ch === 'y' && i > 0 && !'aeiou'.includes(lower[i - 1])) return true
    return false
  }

  // Collect vowel groups
  const vg = []
  for (let i = 0; i < lower.length; ) {
    if (isVowel(lower[i], i)) {
      let j = i
      while (j < lower.length && isVowel(lower[j], j)) j++
      vg.push({ start: i, end: j })
      i = j
    } else i++
  }

  if (vg.length <= 1) return [word]

  // Find potential split points between adjacent vowel groups
  const potentialSplits = []
  for (let g = 0; g < vg.length - 1; g++) {
    const v1End = vg[g].end
    const v2Start = vg[g + 1].start
    const gap = v2Start - v1End
    const cons = lower.slice(v1End, v2Start)
    let sp
    if (gap <= 1) sp = v1End                                          // V·CV
    else if (gap === 2) sp = VALID_ONSET2.has(cons) ? v1End : v1End + 1  // VC·CV unless valid onset
    else sp = (VALID_ONSET3.has(cons) || VALID_ONSET2.has(cons.slice(1))) ? v1End + 1 : v1End + 1
    potentialSplits.push(sp)
  }

  const splits = potentialSplits.slice(0, n - 1)
  const parts = []
  let prev = 0
  for (const s of splits) {
    if (s > prev) parts.push(word.slice(prev, s))
    prev = s
  }
  if (prev < word.length) parts.push(word.slice(prev))
  return parts.filter(p => p.length > 0)
}
// ────────────────────────────────────────────────────────────────────────────

function generateOptions(currentWord, allWords) {
  const correctDef = currentWord.definition
  const others = allWords
    .filter(w => w.definition !== correctDef)
    .map(w => ({ definition: w.definition, pos: w.pos }))
  const distractors = shuffleArray(others).slice(0, 3)
  const correct = { definition: correctDef, pos: currentWord.pos }
  const allOpts = shuffleArray([correct, ...distractors])
  return { options: allOpts, correctIndex: allOpts.findIndex(o => o.definition === correctDef) }
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
  const [lastState, setLastState] = useState(null)
  const [spellingInput, setSpellingInput] = useState('')
  const [spellingResult, setSpellingResult] = useState(null)
  // Radio mode state
  const [radioIndex, setRadioIndex] = useState(0)
  const [radioPaused, setRadioPaused] = useState(false)
  const [radioStopped, setRadioStopped] = useState(false)
  const [radioHovered, setRadioHovered] = useState(false)
  // Voice recording state
  const [isRecording, setIsRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)

  const spellingRef = useRef(null)
  const radioActiveRef = useRef(false)
  const radioTimerRef = useRef(null)
  const radioIndexRef = useRef(0)
  const queueRef = useRef([])
  const vocabRef = useRef([])
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

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
        vocabRef.current = words
        const indices = Array.from({ length: words.length }, (_, i) => i)
        const q = settings.shuffle !== false ? shuffleArray(indices) : indices
        setQueue(q)
        queueRef.current = q
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

  // ── Radio mode playback ──────────────────────────────────────────────────
  const radioPlayFrom = useCallback((idx) => {
    const q = queueRef.current
    const vocab = vocabRef.current
    if (idx >= q.length) { radioActiveRef.current = false; return }
    radioIndexRef.current = idx
    setRadioIndex(idx)
    const word = vocab[q[idx]]
    if (!word) { radioPlayFrom(idx + 1); return }
    speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(word.word)
    u.rate = parseFloat(settings.playbackSpeed || '1.0')
    u.volume = parseFloat(settings.volume || '100') / 100
    u.onend = () => {
      if (!radioActiveRef.current) return
      radioTimerRef.current = setTimeout(() => {
        if (radioActiveRef.current) radioPlayFrom(radioIndexRef.current + 1)
      }, parseFloat(settings.interval || '2') * 1000)
    }
    speechSynthesis.speak(u)
  }, [settings.playbackSpeed, settings.volume, settings.interval])

  useEffect(() => {
    if (mode !== 'radio' || !vocabulary.length) return
    radioActiveRef.current = true
    radioIndexRef.current = 0
    setRadioPaused(false)
    setRadioStopped(false)
    radioPlayFrom(0)
    return () => {
      radioActiveRef.current = false
      clearTimeout(radioTimerRef.current)
      speechSynthesis.cancel()
    }
  }, [mode, vocabulary.length])

  const radioPause = () => {
    radioActiveRef.current = false
    clearTimeout(radioTimerRef.current)
    speechSynthesis.cancel()
    setRadioPaused(true)
  }
  const radioResume = () => {
    radioActiveRef.current = true
    setRadioPaused(false)
    radioPlayFrom(radioIndexRef.current)
  }
  const radioStop = () => {
    radioActiveRef.current = false
    clearTimeout(radioTimerRef.current)
    speechSynthesis.cancel()
    setRadioStopped(true)
    setRadioPaused(false)
  }
  const radioRestart = () => {
    radioActiveRef.current = true
    radioIndexRef.current = 0
    setRadioPaused(false)
    setRadioStopped(false)
    radioPlayFrom(0)
  }
  const radioSkipPrev = () => {
    clearTimeout(radioTimerRef.current)
    speechSynthesis.cancel()
    const idx = Math.max(0, radioIndexRef.current - 1)
    radioIndexRef.current = idx
    setRadioIndex(idx)
    if (!radioPaused && !radioStopped) { radioActiveRef.current = true; radioPlayFrom(idx) }
  }
  const radioSkipNext = () => {
    clearTimeout(radioTimerRef.current)
    speechSynthesis.cancel()
    const idx = Math.min(queueRef.current.length - 1, radioIndexRef.current + 1)
    radioIndexRef.current = idx
    setRadioIndex(idx)
    if (!radioPaused && !radioStopped) { radioActiveRef.current = true; radioPlayFrom(idx) }
  }
  // ────────────────────────────────────────────────────────────────────────

  const playWord = (word) => {
    speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(word)
    u.rate = parseFloat(settings.playbackSpeed || '1.0')
    u.volume = parseFloat(settings.volume || '100') / 100
    speechSynthesis.speak(u)
  }

  // ── Voice recording for dictation ────────────────────────────────────────
  const startRecording = async () => {
    // Use Web Speech API for speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

    if (!SpeechRecognition) {
      showToast?.('您的浏览器不支持语音识别，请使用 Chrome 或 Edge 浏览器', 'error')
      return
    }

    try {
      const recognition = new SpeechRecognition()
      recognition.lang = 'en-US' // English for spelling words
      recognition.interimResults = false
      recognition.maxAlternatives = 1

      recognition.onstart = () => {
        setIsRecording(true)
        showToast?.('正在录音，请说出单词...', 'info')
      }

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        console.log('Recognized:', transcript)
        setSpellingInput(transcript.trim())
        spellingRef.current?.focus()
        showToast?.('识别成功！', 'success')
      }

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error)
        setIsRecording(false)
        if (event.error === 'no-speech') {
          showToast?.('未检测到语音，请重试', 'error')
        } else if (event.error === 'audio-capture') {
          showToast?.('麦克风访问失败，请检查权限', 'error')
        } else if (event.error === 'not-allowed') {
          showToast?.('麦克风权限被拒绝，请在浏览器设置中允许访问麦克风', 'error')
        } else {
          showToast?.('语音识别失败: ' + event.error, 'error')
        }
      }

      recognition.onend = () => {
        setIsRecording(false)
      }

      recognition.start()
      mediaRecorderRef.current = { stop: () => recognition.stop() }

    } catch (error) {
      console.error('Speech recognition error:', error)
      showToast?.('语音识别初始化失败: ' + error.message, 'error')
      setIsRecording(false)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current?.stop) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }
  // ────────────────────────────────────────────────────────────────────────

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
    setQueueIndex(lastState.qi); setCorrectCount(lastState.cc); setWrongCount(lastState.wc); setPreviousWord(lastState.prevWord); setLastState(null)
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
        if (e.key === 'Tab') { e.preventDefault(); playWord(currentWord?.word) }
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

  const PrevWordBlock = () => previousWord ? (
    <div className="prev-word-inline">
      <button className="prev-back-btn" onClick={goBack} disabled={!lastState} title="返回上一个词">←</button>
      <div className="prev-word-info">
        <div className="prev-word-text">{previousWord.word}</div>
        <div className="prev-word-phonetic">{previousWord.phonetic}</div>
        <div className="prev-word-def"><span className="word-pos-tag">{previousWord.pos}</span>{previousWord.definition}</div>
      </div>
    </div>
  ) : null

  // Progress bar only — no correct/wrong counts shown
  const BottomBar = ({ progressValue, total }) => (
    <div className="practice-bottom-bar">
      <div className="bottom-progress-track">
        <div className="bottom-progress-fill" style={{ width: `${progressValue * 100}%` }}>
          <div className="bottom-progress-dot"></div>
        </div>
      </div>
      <span className="bottom-progress-count">{queueIndex + 1}/{total}</span>
    </div>
  )

  // ── RADIO MODE ────────────────────────────────────────────────────────────
  if (mode === 'radio') {
    const radioWord = vocabulary[queue[radioIndex]] || currentWord
    const syllables = radioWord ? syllabifyWord(radioWord.word, radioWord.phonetic) : []
    const isPlaying = !radioPaused && !radioStopped

    return (
      <div className="practice-page radio-mode">
        {/* Word info — hidden by default, revealed on hover */}
        <div
          className="radio-card"
          onMouseEnter={() => setRadioHovered(true)}
          onMouseLeave={() => setRadioHovered(false)}
        >
          {/* Row 1: word (dots style) or blank line */}
          <div className={`radio-row radio-row-word ${radioHovered ? 'revealed' : ''}`}>
            {radioHovered ? (
              <div className="radio-word-syllables">
                {syllables.map((syl, i) => (
                  <React.Fragment key={i}>
                    {i > 0 && <span className="radio-syl-dot">·</span>}
                    <span>{syl}</span>
                  </React.Fragment>
                ))}
              </div>
            ) : (
              <div className="radio-word-blank">
                <span className="radio-blank-line" style={{ width: `${Math.min(Math.max(radioWord?.word?.length * 18, 80), 300)}px` }} />
              </div>
            )}
          </div>

          {/* Row 2: phonetic or stars */}
          <div className={`radio-row radio-row-phonetic ${radioHovered ? 'revealed' : ''}`}>
            {radioHovered ? radioWord?.phonetic : '★ ★ ★'}
          </div>

          {/* Row 3: pos + definition or stars */}
          <div className={`radio-row radio-row-def ${radioHovered ? 'revealed' : ''}`}>
            {radioHovered
              ? <><span className="word-pos-tag">{radioWord?.pos}</span>{radioWord?.definition}</>
              : '★ ★ ★'
            }
          </div>
        </div>

        {/* Controls: prev | play/pause | next | stop */}
        <div className="radio-controls">
          <button className="radio-ctrl-btn" onClick={radioSkipPrev} title="上一个">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="19 20 9 12 19 4 19 20"></polygon>
              <line x1="5" y1="19" x2="5" y2="5"></line>
            </svg>
          </button>

          {radioPaused || radioStopped ? (
            <button className="radio-ctrl-btn radio-play-btn" onClick={radioStopped ? radioRestart : radioResume} title="继续">
              <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
            </button>
          ) : (
            <button className="radio-ctrl-btn radio-play-btn" onClick={radioPause} title="暂停">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16"></rect>
                <rect x="14" y="4" width="4" height="16"></rect>
              </svg>
            </button>
          )}

          <button className="radio-ctrl-btn" onClick={radioSkipNext} title="下一个">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5 4 15 12 5 20 5 4"></polygon>
              <line x1="19" y1="5" x2="19" y2="19"></line>
            </svg>
          </button>

          {/* Star bookmark (decorative / future favorites feature) */}
          <button className="radio-ctrl-btn radio-star-btn" title="收藏">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
          </button>
        </div>

        <div className="radio-progress-bar">
          <div className="radio-progress-fill" style={{ width: `${(radioIndex / Math.max(queue.length - 1, 1)) * 100}%` }} />
        </div>
        <div className="radio-progress-label">{radioIndex + 1} / {queue.length}</div>

        <div className="radio-bottom-btns">
          <button className="radio-stop-btn" onClick={radioStop}>停止</button>
          <button className="radio-home-btn" onClick={() => { radioStop(); navigate('/') }}>返回主页</button>
        </div>
      </div>
    )
  }

  // ── DICTATION MODE ────────────────────────────────────────────────────────
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
          <div className="dictation-letter-hint">
            {currentWord.word.split('').map((ch, i) => (
              ch === ' ' ? <span key={i} className="letter-hint-space" /> : <span key={i} className="letter-hint-blank">_</span>
            ))}
          </div>
          {spellingResult === 'wrong' && (
            <div className="spelling-answer">正确答案：<strong>{currentWord.word}</strong></div>
          )}
          <div className={`spelling-input-wrapper ${spellingResult || ''}`}>
            <input ref={spellingRef} type="text" className="spelling-input" value={spellingInput}
              onChange={e => setSpellingInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSpellingSubmit() }}
              placeholder="输入你听到的单词..." disabled={!!spellingResult || transcribing}
              autoComplete="off" spellCheck={false} />
            {/* Mic button */}
            {!spellingResult && (
              <button
                className={`mic-btn ${isRecording ? 'recording' : ''} ${transcribing ? 'transcribing' : ''}`}
                onClick={isRecording ? stopRecording : startRecording}
                disabled={transcribing}
                title={isRecording ? '停止录音' : '语音输入'}
              >
                {transcribing ? (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="spin">
                    <circle cx="12" cy="12" r="10" strokeDasharray="30 10"></circle>
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="9" y="2" width="6" height="11" rx="3"></rect>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="23"></line>
                    <line x1="8" y1="23" x2="16" y2="23"></line>
                  </svg>
                )}
              </button>
            )}
            {!spellingResult && <button className="spelling-submit-btn" onClick={handleSpellingSubmit}>确认</button>}
          </div>
        </div>
        <button className="skip-btn" onClick={handleSkip}>不知道 <span className="shortcut-hint">(5)</span></button>
        <BottomBar progressValue={progress} total={vocabulary.length} />
      </div>
    )
  }

  // ── LISTENING / MEANING / SMART MODE ─────────────────────────────────────
  // Build syllabified word for meaning mode display
  const wordDisplay = showWord
    ? syllabifyWord(currentWord.word, currentWord.phonetic).join(' ')
    : currentWord.word

  return (
    <div className="practice-page">
      <PrevWordBlock />

      <div className="practice-main">
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
              <div className="word-text">{wordDisplay}</div>
              <div className="word-phonetic-row">
                <span className="word-phonetic">{currentWord.phonetic}</span>
                {mode === 'meaning' && (
                  <button className="play-btn-mini" onClick={() => playWord(currentWord.word)} title="播放发音">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                      <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                    </svg>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Options grid */}
        <div className="options-grid">
          {options.map((option, idx) => {
            let cls = 'option-btn'
            if (showResult) {
              if (idx === correctIndex) cls += ' correct'
              else if (idx === selectedAnswer) cls += ' wrong'
            } else if (selectedAnswer === idx) cls += ' selected'
            return (
              <button key={idx} className={cls} onClick={() => handleOptionSelect(idx)} disabled={showResult}>
                <div className="option-header">
                  <span className="option-pos">{option.pos}</span>
                  <span className="option-key">快捷键: {idx + 1}</span>
                </div>
                <span className="option-text">{option.definition}</span>
              </button>
            )
          })}
        </div>

        {/* Skip row + replay button */}
        <div className="options-footer">
          <button className="skip-btn" onClick={handleSkip}>
            不知道 <span className="shortcut-hint">快捷键: 5</span>
          </button>
          <button
            className="replay-btn"
            onClick={() => playWord(currentWord?.word)}
            title="再读一遍，快捷键 Tab"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
            </svg>
          </button>
        </div>
      </div>

      <BottomBar progressValue={progress} total={vocabulary.length} />
    </div>
  )
}

export default PracticePage
