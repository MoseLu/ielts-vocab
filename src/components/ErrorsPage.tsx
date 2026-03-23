import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWrongWords } from '../features/vocabulary/hooks'
import { loadSmartStats } from '../lib/smartMode'
import type { SmartDimension } from '../lib/smartMode'

type ActiveTab = 'words' | 'real'

const DIM_LABEL: Record<SmartDimension, string> = {
  listening: '听音',
  meaning: '看义',
  dictation: '听写',
}

function ErrorsPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<ActiveTab>('words')
  const { words, removeWord, clearAll } = useWrongWords()

  // Per-dimension stats stored locally by smartMode
  const smartStats = loadSmartStats()

  // Sort by wrong_count descending so the most-missed words come first
  const sortedWords = [...words].sort((a, b) => (b.wrong_count ?? 0) - (a.wrong_count ?? 0))

  const handleRemoveWord = (word: string) => removeWord(word)
  const handleClearAll = () => clearAll()
  const handlePractice = () => navigate('/practice?mode=errors')

  return (
    <div className="errors-page">
      <div className="page-content">
      {words.length > 0 && (
        <div className="errors-header">
          <div className="errors-actions">
            <button className="errors-practice-btn" onClick={handlePractice}>
              复习 ({words.length}词)
            </button>
            <button className="errors-clear-btn" onClick={handleClearAll}>
              清空
            </button>
          </div>
        </div>
      )}

      {/* Tab bar */}
      <div className="errors-tabs">
        <button
          className={`errors-tab ${activeTab === 'words' ? 'active' : ''}`}
          onClick={() => setActiveTab('words')}
        >
          错词
          {words.length > 0 && (
            <span className="errors-tab-badge">{words.length}</span>
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
      ) : words.length === 0 ? (
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
            <span className="errors-filter-label">共 {words.length} 个错词，按错误次数排序</span>
          </div>
          <div className="errors-list">
            {sortedWords.map((word) => {
              const wordStats = smartStats[word.word]
              const dims = (['listening', 'meaning', 'dictation'] as SmartDimension[]).filter(dim => {
                const s = wordStats?.[dim]
                return s && (s.correct + s.wrong) > 0
              })

              return (
                <div key={word.word} className="errors-item">
                  <div className="errors-item-main">
                    <div className="errors-item-word-row">
                      <span className="errors-item-word">{word.word}</span>
                      {(word.wrong_count ?? 0) > 0 && (
                        <span className="errors-item-total-count">错 {word.wrong_count} 次</span>
                      )}
                    </div>
                    {word.phonetic && (
                      <div className="errors-item-phonetic">{word.phonetic}</div>
                    )}
                    <div className="errors-item-definition">
                      {word.pos && <span className="word-pos-tag">{word.pos}</span>}
                      {word.definition}
                    </div>
                    {dims.length > 0 && (
                      <div className="errors-item-dims">
                        {dims.map(dim => {
                          const s = wordStats![dim]
                          const variant = s.wrong === 0 ? 'ok' : s.correct === 0 ? 'error' : 'mixed'
                          return (
                            <span key={dim} className={`errors-dim-badge errors-dim-${variant}`}>
                              {DIM_LABEL[dim]}
                              {s.wrong > 0 && (
                                <span className="errors-dim-wrong">×{s.wrong}</span>
                              )}
                              {s.correct > 0 && s.wrong > 0 && (
                                <span className="errors-dim-correct"> ✓{s.correct}</span>
                              )}
                            </span>
                          )
                        })}
                      </div>
                    )}
                    {dims.length === 0 && (
                      <div className="errors-item-dims">
                        <span className="errors-dim-badge errors-dim-unknown">未记录维度</span>
                      </div>
                    )}
                  </div>
                  <button
                    className="errors-item-remove"
                    onClick={() => handleRemoveWord(word.word)}
                    title="移除"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              )
            })}
          </div>
        </>
      )}
      </div>
    </div>
  )
}

export default ErrorsPage
