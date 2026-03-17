import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function ErrorsPage() {
  const navigate = useNavigate()
  const [wrongWords, setWrongWords] = useState([])
  const [activeTab, setActiveTab] = useState('words')

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
    navigate('/practice?mode=errors')
  }

  return (
    <div className="errors-page">
      <div className="errors-header">
        <h1 className="errors-title">错词本</h1>
        {wrongWords.length > 0 && (
          <div className="errors-actions">
            <button className="errors-practice-btn" onClick={handlePractice}>
              复习 ({wrongWords.length}词)
            </button>
            <button className="errors-clear-btn" onClick={handleClearAll}>
              清空
            </button>
          </div>
        )}
      </div>

      {/* Tab bar */}
      <div className="errors-tabs">
        <button
          className={`errors-tab ${activeTab === 'words' ? 'active' : ''}`}
          onClick={() => setActiveTab('words')}
        >
          错词
          {wrongWords.length > 0 && (
            <span className="errors-tab-badge">{wrongWords.length}</span>
          )}
        </button>
        <button
          className={`errors-tab ${activeTab === 'real' ? 'active' : ''}`}
          onClick={() => setActiveTab('real')}
        >
          真题
        </button>
      </div>

      {activeTab === 'real' ? (
        <div className="errors-empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M9 9h6M9 13h6M9 17h4" />
          </svg>
          <p>真题错题功能</p>
          <span>敬请期待</span>
        </div>
      ) : wrongWords.length === 0 ? (
        <div className="errors-empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="9" y1="13" x2="15" y2="13" />
            <line x1="9" y1="17" x2="15" y2="17" />
          </svg>
          <p>暂无错词</p>
          <span>学习过程中标记为"不知道"的单词会出现在这里</span>
          <button className="errors-go-practice" onClick={() => navigate('/')}>去练习 →</button>
        </div>
      ) : (
        <>
          <div className="errors-filter-bar">
            <span className="errors-filter-label">共 {wrongWords.length} 个错词</span>
          </div>
          <div className="errors-list">
            {wrongWords.map((word, index) => (
              <div key={index} className="errors-item">
                <div className="errors-item-main">
                  <div className="errors-item-word">{word.word}</div>
                  <div className="errors-item-phonetic">{word.phonetic}</div>
                  <div className="errors-item-definition">
                    {word.pos && <span className="word-pos-tag">{word.pos}</span>}
                    {word.definition}
                  </div>
                </div>
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
        </>
      )}
    </div>
  )
}

export default ErrorsPage
