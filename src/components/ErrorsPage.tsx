import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWrongWords } from '../features/vocabulary/hooks'
import type { SmartDimension } from '../lib/smartMode'
import { Page, PageContent, PageHeader } from './layout'
import { EmptyState, SegmentedControl, UnderlineTabs } from './ui'

type ActiveTab = 'words' | 'real'
type DimFilter = 'all' | SmartDimension

const DIM_LABEL: Record<SmartDimension, string> = {
  listening: '听音',
  meaning: '释义',
  dictation: '听写',
}

const DIMS: SmartDimension[] = ['listening', 'meaning', 'dictation']

export default function ErrorsPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<ActiveTab>('words')
  const [dimFilter, setDimFilter] = useState<DimFilter>('all')
  const { words, removeWord, clearAll } = useWrongWords()

  const dimCounts: Record<SmartDimension, number> = {
    listening: words.filter(w => (w.listening_wrong ?? 0) > 0).length,
    meaning: words.filter(w => (w.meaning_wrong ?? 0) > 0).length,
    dictation: words.filter(w => (w.dictation_wrong ?? 0) > 0).length,
  }

  const filteredWords = [...words]
    .filter(w => {
      if (dimFilter === 'all') return true
      return (((w[`${dimFilter}_wrong` as keyof typeof w] as number) ?? 0) > 0)
    })
    .sort((a, b) => {
      if (dimFilter !== 'all') {
        const aw = ((a[`${dimFilter}_wrong` as keyof typeof a] as number) ?? 0)
        const bw = ((b[`${dimFilter}_wrong` as keyof typeof b] as number) ?? 0)
        if (bw !== aw) return bw - aw
      }
      return (b.wrong_count ?? 0) - (a.wrong_count ?? 0)
    })

  const practiceQuery = dimFilter === 'all' ? '/practice?mode=errors' : `/practice?mode=errors&dim=${dimFilter}`

  const toolbar = (
    <div className="errors-toolbar">
      <UnderlineTabs
        className="errors-tabs"
        ariaLabel="错词本导航"
        value={activeTab}
        onChange={setActiveTab}
        options={[
          { value: 'words', label: '错词', badge: words.length > 0 ? words.length : undefined },
          { value: 'real', label: '真题' },
        ]}
      />

      {words.length > 0 && activeTab === 'words' && (
        <div className="errors-actions">
          <button className="errors-practice-btn" onClick={() => navigate(practiceQuery)}>
            复习（{filteredWords.length}词）
          </button>
          <button className="errors-clear-btn" onClick={clearAll}>
            清空
          </button>
        </div>
      )}
    </div>
  )

  return (
    <Page className="errors-page">
      <PageHeader className="errors-page-toolbar">{toolbar}</PageHeader>
      <PageContent className="errors-page-body">
            {activeTab === 'real' ? (
              <EmptyState
                page
                className="errors-empty"
                icon={(
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M9 9h6M9 13h6M9 17h4" />
                  </svg>
                )}
                title="真题错题功能"
                description="敬请期待"
              />
            ) : words.length === 0 ? (
              <EmptyState
                page
                className="errors-empty"
                icon={(
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="9" y1="13" x2="15" y2="13" />
                    <line x1="9" y1="17" x2="15" y2="17" />
                  </svg>
                )}
                title="暂无错词"
                description='学习过程中标记为"不知道"的单词会出现在这里'
                action={<button className="errors-go-practice" onClick={() => navigate('/plan')}>去练习 →</button>}
              />
            ) : (
              <div className="errors-content-scroll">
                <SegmentedControl
                  className="errors-dim-filter"
                  ariaLabel="错词维度筛选"
                  value={dimFilter}
                  onChange={setDimFilter}
                  options={[
                    { value: 'all', label: '全部', badge: words.length },
                    ...DIMS.map(dim => ({
                      value: dim,
                      label: DIM_LABEL[dim],
                      badge: dimCounts[dim] > 0 ? dimCounts[dim] : undefined,
                      disabled: dimCounts[dim] === 0,
                    })),
                  ]}
                />

                {filteredWords.length === 0 ? (
                  <EmptyState
                    page
                    className="errors-empty"
                    title="该模式暂无错词"
                    description="继续练习，错词会自动收录"
                  />
                ) : (
                  <div className="errors-list">
                    {filteredWords.map(word => {
                      const dims = DIMS.filter(dim => {
                        const c = ((word[`${dim}_correct` as keyof typeof word] as number) ?? 0)
                        const w = ((word[`${dim}_wrong` as keyof typeof word] as number) ?? 0)
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
                            {word.phonetic && <div className="errors-item-phonetic">{word.phonetic}</div>}
                            <div className="errors-item-definition">
                              {word.pos && <span className="word-pos-tag">{word.pos}</span>}
                              {word.definition}
                            </div>
                            {dims.length > 0 ? (
                              <div className="errors-item-dims">
                                {dims.map(dim => {
                                  const correct = ((word[`${dim}_correct` as keyof typeof word] as number) ?? 0)
                                  const wrong = ((word[`${dim}_wrong` as keyof typeof word] as number) ?? 0)
                                  const variant = wrong === 0 ? 'ok' : correct === 0 ? 'error' : 'mixed'
                                  const highlighted = dimFilter === dim
                                  return (
                                    <span
                                      key={dim}
                                      className={`errors-dim-badge errors-dim-${variant}${highlighted ? ' errors-dim-highlight' : ''}`}
                                    >
                                      {DIM_LABEL[dim]}
                                      {wrong > 0 && <span className="errors-dim-wrong">×{wrong}</span>}
                                      {correct > 0 && wrong > 0 && <span className="errors-dim-correct"> ✓{correct}</span>}
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
                            onClick={() => removeWord(word.word)}
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
              </div>
            )}
      </PageContent>
    </Page>
  )
}
