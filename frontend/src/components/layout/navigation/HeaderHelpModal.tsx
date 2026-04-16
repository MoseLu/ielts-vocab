import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import type { PracticeMode } from './Header.types'
import { type HeaderHelpFaqItem, usePlanHelpFaqItems } from './helpContentRegistry'

const HELP_SHORTCUTS: ReadonlyArray<{ key: string; description: string }> = [
  { key: 'Shift + Q', description: '打开单词搜索' },
  { key: '1 - 4', description: '选择答案选项' },
  { key: '5', description: '不知道（跳过）' },
  { key: '空格', description: '重新播放发音' },
  { key: 'Esc', description: '退出练习或关闭弹窗' },
]

function normalizeSearchText(value: string) {
  return value.trim().toLocaleLowerCase()
}

function matchesSearch(fields: Array<string | undefined>, query: string) {
  if (!query) return true

  return fields.some(field => normalizeSearchText(field ?? '').includes(query))
}

function faqMatchesSearch(item: HeaderHelpFaqItem, query: string) {
  return matchesSearch([
    item.eyebrow,
    item.title,
    item.badge,
    item.description,
    ...item.facts,
    ...item.sections.map(section => section.label),
    ...item.sections.flatMap(section => section.items),
  ], query)
}

interface HeaderHelpModalProps {
  modeNames: Record<PracticeMode, string>
  modeDescriptions: Record<PracticeMode, string>
  onClose: () => void
  pathname: string
}

export default function HeaderHelpModal({
  modeNames,
  modeDescriptions,
  onClose,
  pathname,
}: HeaderHelpModalProps) {
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query)
  const normalizedQuery = normalizeSearchText(deferredQuery)
  const [openFaqIds, setOpenFaqIds] = useState<string[]>([])
  const planHelpFaqItems = usePlanHelpFaqItems()

  useEffect(() => {
    const root = document.documentElement
    const body = document.body
    const prevBodyOverflow = body.style.overflow
    const prevBodyPaddingRight = body.style.paddingRight
    const prevRootOverflow = root.style.overflow
    const prevRootPaddingRight = root.style.paddingRight
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth

    if (scrollbarWidth > 0) {
      const compensation = `${scrollbarWidth}px`
      body.style.paddingRight = compensation
      root.style.paddingRight = compensation
    }

    body.style.overflow = 'hidden'
    root.style.overflow = 'hidden'

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      body.style.overflow = prevBodyOverflow
      body.style.paddingRight = prevBodyPaddingRight
      root.style.overflow = prevRootOverflow
      root.style.paddingRight = prevRootPaddingRight
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [onClose])

  const routeFaqItems = pathname === '/plan' ? planHelpFaqItems : []

  useEffect(() => {
    if (!normalizedQuery) return

    setOpenFaqIds(routeFaqItems.filter(item => faqMatchesSearch(item, normalizedQuery)).map(item => item.id))
  }, [normalizedQuery, routeFaqItems])

  const shortcutItems = useMemo(() => {
    return HELP_SHORTCUTS.filter(item => matchesSearch([item.key, item.description], normalizedQuery))
  }, [normalizedQuery])

  const modeItems = useMemo(() => {
    return (Object.entries(modeNames) as [PracticeMode, string][])
      .map(([key, name]) => ({
        key,
        name,
        description: modeDescriptions[key],
      }))
      .filter(item => matchesSearch([item.name, item.description], normalizedQuery))
  }, [modeDescriptions, modeNames, normalizedQuery])

  const faqItems = useMemo(() => {
    return routeFaqItems.filter(item => faqMatchesSearch(item, normalizedQuery))
  }, [normalizedQuery, routeFaqItems])

  const resultCount = shortcutItems.length + modeItems.length + faqItems.length

  const toggleFaq = (faqId: string) => {
    setOpenFaqIds(previousIds => (
      previousIds.includes(faqId)
        ? previousIds.filter(id => id !== faqId)
        : [...previousIds, faqId]
    ))
  }

  if (typeof document === 'undefined') {
    return null
  }

  return createPortal(
    <div className="settings-overlay show" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <div className="settings-modal settings-modal--help">
        <div className="settings-header">
          <h2 className="settings-title">帮助</h2>
          <button className="settings-close" onClick={onClose} aria-label="关闭帮助弹窗">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div className="settings-content settings-content--help">
          <div className="help-modal-search-block">
            <label className="help-modal-search-field" htmlFor="header-help-search">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="11" cy="11" r="8" />
                <path d="M21 21l-4.35-4.35" />
              </svg>
              <input
                id="header-help-search"
                className="help-modal-search-input"
                type="search"
                value={query}
                onChange={event => setQuery(event.target.value)}
                placeholder="搜索快捷键、模式和首页 Q&A"
                aria-label="搜索帮助内容"
              />
            </label>
            <p className="help-modal-search-summary">
              {normalizedQuery
                ? `当前匹配 ${resultCount} 项帮助内容`
                : '可直接搜索快捷键、练习模式或首页学习说明'}
            </p>
          </div>

          {resultCount === 0 ? (
            <div className="help-modal-empty">
              <strong>没有找到匹配项</strong>
              <span>换个关键词试试，例如“错词”“艾宾浩斯”或“Shift + Q”。</span>
            </div>
          ) : (
            <>
              {shortcutItems.length > 0 && (
                <div className="help-modal-section">
                  <h3 className="help-modal-title">键盘快捷键</h3>
                  <div className="help-modal-list">
                    {shortcutItems.map(item => (
                      <div key={item.key} className="help-modal-row">
                        <kbd className="help-modal-kbd">{item.key}</kbd>
                        <span className="help-modal-text">{item.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {modeItems.length > 0 && (
                <div className="help-modal-section">
                  <h3 className="help-modal-title">学习模式说明</h3>
                  <div className="help-modal-list">
                    {modeItems.map(item => (
                      <div key={item.key} className="help-modal-mode">
                        <strong className="help-modal-mode-name">{item.name}</strong> — {item.description}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {faqItems.length > 0 && (
                <div className="help-modal-section">
                  <h3 className="help-modal-title">首页 Q&amp;A</h3>
                  <div className="help-modal-faq-list">
                    {faqItems.map(item => {
                      const isOpen = normalizedQuery.length > 0 || openFaqIds.includes(item.id)

                      return (
                        <article
                          key={item.id}
                          className={`help-modal-faq-item help-modal-faq-item--${item.tone}${isOpen ? ' is-open' : ''}`}
                        >
                          <button
                            type="button"
                            className="help-modal-faq-trigger"
                            onClick={() => toggleFaq(item.id)}
                          >
                            <div className="help-modal-faq-trigger-main">
                              <span className="help-modal-faq-eyebrow">{item.eyebrow}</span>
                              <div className="help-modal-faq-title-row">
                                <strong className="help-modal-faq-title">{item.title}</strong>
                                <span className="help-modal-faq-badge">{item.badge}</span>
                              </div>
                              <span className="help-modal-faq-summary">{item.description}</span>
                            </div>
                            <span className="help-modal-faq-toggle">{isOpen ? '收起' : '展开'}</span>
                          </button>

                          {isOpen && (
                            <div className="help-modal-faq-body">
                              {item.facts.length > 0 && (
                                <div className="help-modal-faq-facts" aria-label={`${item.title}关键信息`}>
                                  {item.facts.map(fact => (
                                    <span key={`${item.id}-${fact}`} className="help-modal-faq-fact">{fact}</span>
                                  ))}
                                </div>
                              )}

                              <div className="help-modal-faq-sections">
                                {item.sections.map(section => (
                                  <section key={`${item.id}-${section.label}`} className="help-modal-faq-section">
                                    <h4 className="help-modal-faq-section-label">{section.label}</h4>
                                    <ul className="help-modal-faq-items">
                                      {section.items.map(sectionItem => (
                                        <li key={`${item.id}-${section.label}-${sectionItem}`}>{sectionItem}</li>
                                      ))}
                                    </ul>
                                  </section>
                                ))}
                              </div>
                            </div>
                          )}
                        </article>
                      )
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
