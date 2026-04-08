import { useState } from 'react'
import { WRONG_WORD_PENDING_REVIEW_TARGET } from '../../../features/vocabulary/wrongWordsStore'
import { Card } from '../../ui'

interface ErrorsFAQItem {
  key: string
  question: string
  answer: string
}

const FAQ_ITEMS: ErrorsFAQItem[] = [
  {
    key: 'scope',
    question: '待清错词和累计错词有什么区别？',
    answer: `答错过就会留在累计错词里；某一类问题还没连续答对 ${WRONG_WORD_PENDING_REVIEW_TARGET} 次之前，也会继续留在待清错词。`,
  },
  {
    key: 'selection',
    question: '勾选后会把错词移出列表吗？',
    answer: '不会。勾选只会把这些词加入本次复习，错词记录本身会继续保留。',
  },
  {
    key: 'dimensions',
    question: '为什么问题类型数量会重复？',
    answer: '因为一个词可以同时属于多个问题类型，所以标签数是按问题项累计，不是把单词互斥拆开。',
  },
  {
    key: 'filters',
    question: '怎么更快缩小范围？',
    answer: '优先用日期快捷、错次区间和搜索词；需要翻页时，直接用待清错词和累计错词右侧的上一页、下一页。',
  },
]

export function ErrorsFAQCard() {
  const [openKey, setOpenKey] = useState<string | null>(null)

  return (
    <Card className="errors-faq-card" padding="md">
      <div className="errors-faq-list">
        {FAQ_ITEMS.map(item => {
          const isOpen = openKey === item.key

          return (
            <section key={item.key} className={`errors-faq-item${isOpen ? ' is-open' : ''}`}>
              <button
                type="button"
                className="errors-faq-question"
                aria-expanded={isOpen}
                onClick={() => setOpenKey(current => (current === item.key ? null : item.key))}
              >
                <span className="errors-faq-question-mark">Q</span>
                <span className="errors-faq-question-text">{item.question}</span>
                <span className="errors-faq-toggle">{isOpen ? '收起' : '展开'}</span>
              </button>

              {isOpen && (
                <div className="errors-faq-answer">
                  <span className="errors-faq-answer-mark">A</span>
                  <p>{item.answer}</p>
                </div>
              )}
            </section>
          )
        })}
      </div>
    </Card>
  )
}
