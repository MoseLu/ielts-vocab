import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function ErrorsPage() {
  const navigate = useNavigate()
  const [wrongWords, setWrongWords] = useState([])

  useEffect(() => {
    const saved = localStorage.getItem('wrong_words')
    if (saved) {
      try {
        setWrongWords(JSON.parse(saved))
      } catch (e) {
        setWrongWords([])
      }
    }
  }, [])

  const handleRemoveWord = (index) => {
    const newList = wrongWords.filter((_, i) => i !== index)
    setWrongWords(newList)
    localStorage.setItem('wrong_words', JSON.stringify(newList))
  }

  const handleClearAll = () => {
    setWrongWords([])
    localStorage.setItem('wrong_words', JSON.stringify([]))
  }

  const handlePractice = () => {
    // TODO: 跳转到错词练习模式
    navigate('/practice?mode=errors')
  }

  return (
    <div className="errors-page">
      <div className="errors-header">
        <h1 className="errors-title">错词本</h1>
        {wrongWords.length > 0 && (
          <div className="errors-actions">
            <button className="errors-practice-btn" onClick={handlePractice}>
              开始复习
            </button>
            <button className="errors-clear-btn" onClick={handleClearAll}>
              清空
            </button>
          </div>
        )}
      </div>

      {wrongWords.length === 0 ? (
        <div className="errors-empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="9" y1="13" x2="15" y2="13" />
            <line x1="9" y1="17" x2="15" y2="17" />
          </svg>
          <p>暂无错词</p>
          <span>学习过程中标记为"不知道"的单词会出现在这里</span>
        </div>
      ) : (
        <div className="errors-list">
          {wrongWords.map((word, index) => (
            <div key={index} className="errors-item">
              <div className="errors-item-word">{word.word}</div>
              <div className="errors-item-phonetic">{word.phonetic}</div>
              <div className="errors-item-definition">{word.definition}</div>
              <button
                className="errors-item-remove"
                onClick={() => handleRemoveWord(index)}
                title="移除"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ErrorsPage