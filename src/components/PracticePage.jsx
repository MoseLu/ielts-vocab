import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function PracticePage({ user, currentDay, mode, onComplete, onBack, showToast, onDayChange }) {
  const navigate = useNavigate()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [vocabulary, setVocabulary] = useState([])
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [showResult, setShowResult] = useState(false)

  useEffect(() => {
    // 如果没有选择日期，返回首页
    if (!currentDay) {
      navigate('/')
      return
    }

    // Load vocabulary for current day
    fetch(`/api/vocabulary/day/${currentDay}`)
      .then(res => res.json())
      .then(data => setVocabulary(data.words || []))
      .catch(() => showToast('加载词汇失败', 'error'))
  }, [currentDay, navigate])

  const handleAnswer = (answer) => {
    setSelectedAnswer(answer)
    setShowResult(true)

    setTimeout(() => {
      if (currentIndex < vocabulary.length - 1) {
        setCurrentIndex(currentIndex + 1)
        setSelectedAnswer(null)
        setShowResult(false)
      } else {
        navigate('/')
      }
    }, 1500)
  }

  const currentWord = vocabulary[currentIndex]

  if (!currentWord) {
    return <div className="loading">加载中...</div>
  }

  return (
    <div className="practice-container">
      <div className="practice-header">
        <button className="back-btn" onClick={() => navigate('/')}>返回</button>
        <div className="progress">
          {currentIndex + 1} / {vocabulary.length}
        </div>
      </div>

      <div className="practice-content">
        <div className="word-card">
          <h2 className="word">{currentWord.word}</h2>
          {mode === 'listening' && (
            <button className="play-btn" onClick={() => {
              const utterance = new SpeechSynthesisUtterance(currentWord.word)
              speechSynthesis.speak(utterance)
            }}>
              🔊 播放发音
            </button>
          )}
        </div>

        <div className="options">
          {currentWord.options?.map((option, index) => (
            <button
              key={index}
              className={`option-btn ${selectedAnswer === index ? 'selected' : ''} ${showResult ? (index === currentWord.correct ? 'correct' : 'wrong') : ''}`}
              onClick={() => !showResult && handleAnswer(index)}
              disabled={showResult}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default PracticePage