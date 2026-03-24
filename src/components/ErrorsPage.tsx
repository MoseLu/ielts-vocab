import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWrongWords } from '../features/vocabulary/hooks'
import type { SmartDimension } from '../lib/smartMode'

type ActiveTab = 'words' | 'real'
type DimFilter = 'all' | SmartDimension

const DIM_LABEL: Record<SmartDimension, string> = {
  listening: '听音',
  meaning: '看义',
  dictation: '听写',
}

const DIMS: SmartDimension[] = ['listening', 'meaning', 'dictation']

function ErrorsPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<ActiveTab>('words')
  const [dimFilter, setDimFilter] = useState<DimFilter>('all')
  const { words, removeWord, clearAll } = useWrongWords()

  // Count words with errors per dimension
  const dimCounts: Record<SmartDimension, number> = {
    listening: words.filter(w => (w.listening_wrong ?? 0) > 0).length,
    meaning:   words.filter(w => (w.meaning_wrong   ?? 0) > 0).length,
    dictation: words.filter(w => (w.dictation_wrong ?? 0) > 0).length,
  }

  // Filter by selected dimension, then sort by that dimension's wrong count (or total)
  const filteredWords = [...words]
    .filter(w => {
      if (dimFilter === 'all') return true
      return (w[`${dimFilter}_wrong` as keyof typeof w] as number ?? 0) > 0
    })
    .sort((a, b) => {
      if (dimFilter !== 'all') {
        const aw = a[`${dimFilter}_wrong` as keyof typeof a] as number ?? 0
        const bw = b[`${dimFilter}_wrong` as keyof typeof b] as number ?? 0
        if (bw !== aw) return bw - aw
      }
      return (b.wrong_count ?? 0) - (a.wrong_count ?? 0)
    })

  const handleRemoveWord = (word: string) => removeWord(word)
  const handleClearAll = () => clearAll()
  const practiceQuery = dimFilter === 'all' ? '/practice?mode=errors' : `/practice?mode=errors&dim=${dimFilter}`
  const handlePractice = () => navigate(practiceQuery)

  return (
    <div className="errors-page">
      <div className="page-content">
      {words.length > 0 && (
        <div className="errors-header">
          <div className="errors-actions">
            <button className="errors-practice-btn" onClick={handlePractice}>
              复习 ({filteredWords.length}词)
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
          {/* Dimension filter */}
          <div className="errors-dim-filter">
            <button
              className={`errors-dim-pill ${dimFilter === 'all' ? 'active' : ''}`}
              onClick={() => setDimFilter('all')}
            >
              全部
              <span className="errors-dim-pill-count">{words.length}</span>
            </button>
            {DIMS.map(dim => (
              <button
                key={dim}
                className={`errors-dim-pill ${dimFilter === dim ? 'active' : ''}`}
                onClick={() => setDimFilter(dim)}
                disabled={dimCounts[dim] === 0}
              >
                {DIM_LABEL[dim]}
                {dimCounts[dim] > 0 && (
                  <span className="errors-dim-pill-count">{dimCounts[dim]}</span>
                )}
              </button>
            ))}
          </div>

          {filteredWords.length === 0 ? (
            <div className="errors-empty">
              <p>该模式暂无错词</p>
              <span>继续练习，错词会自动收录</span>
            </div>
          ) : (
            <div className="errors-list">
              {filteredWords.map((word) => {
                // Show all dims with data; highlight the active filter dim
                const dims = DIMS.filter(dim => {
                  const c = word[`${dim}_correct` as keyof typeof word] as number ?? 0
                  const w = word[`${dim}_wrong` as keyof typeof word] as number ?? 0
                  return c + w > 0
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
                      {dims.length > 0 ? (
                        <div className="errors-item-dims">
                          {dims.map(dim => {
                            const correct = word[`${dim}_correct` as keyof typeof word] as number ?? 0
                            const wrong   = word[`${dim}_wrong`   as keyof typeof word] as number ?? 0
                            const variant = wrong === 0 ? 'ok' : correct === 0 ? 'error' : 'mixed'
                            const highlighted = dimFilter === dim
                            return (
                              <span
                                key={dim}
                                className={`errors-dim-badge errors-dim-${variant}${highlighted ? ' errors-dim-highlight' : ''}`}
                              >
                                {DIM_LABEL[dim]}
                                {wrong > 0 && <span className="errors-dim-wrong">×{wrong}</span>}
                                {correct > 0 && wrong > 0 && (
                                  <span className="errors-dim-correct"> ✓{correct}</span>
                                )}
                              </span>
                            )
                          })}
                        </div>
                      ) : (
                        <div className="errors-item-dims">
                          <span className="errors-dim-badge errors-dim-unknown">暂无维度数据</span>
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
          )}
        </>
      )}
      </div>
    </div>
  )
}

export default ErrorsPage
