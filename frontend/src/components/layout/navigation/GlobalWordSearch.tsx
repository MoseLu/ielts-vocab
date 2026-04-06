import GlobalWordSearchDetailPanel from './GlobalWordSearchDetailPanel'
import { useGlobalWordSearch } from '../../../composables/layout/navigation/useGlobalWordSearch'

export default function GlobalWordSearch() {
  const {
    isOpen,
    query,
    submittedQuery,
    results,
    selectedResult,
    error,
    isLoading,
    inputRef,
    showSearchEntry,
    closeSearch,
    runSearch,
    handleQueryChange,
    handleQuickPickWord,
  } = useGlobalWordSearch()

  if (!isOpen) return null

  return (
    <div
      className="global-word-search-overlay"
      onMouseDown={event => {
        if (event.target === event.currentTarget) {
          closeSearch()
        }
      }}
    >
      <div
        className={`global-word-search-panel${selectedResult ? ' global-word-search-panel--with-result' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="全局单词搜索"
      >
        {showSearchEntry && (
          <div className="global-word-search-bar">
            <form
              className="global-word-search-form"
              onSubmit={event => {
                event.preventDefault()
                void runSearch(query)
              }}
            >
              <input
                ref={inputRef}
                type="search"
                value={query}
                className="global-word-search-input"
                aria-label="全局单词搜索"
                placeholder="单词查询（回车搜索）"
                onChange={event => handleQueryChange(event.target.value)}
              />
              <span className="global-word-search-shortcut" aria-hidden="true">
                Shift + Q
              </span>
            </form>
          </div>
        )}

        {showSearchEntry && isLoading && (
          <div className="global-word-search-status">正在搜索“{submittedQuery || query.trim()}”...</div>
        )}

        {showSearchEntry && error && !isLoading && (
          <div className="global-word-search-status global-word-search-status--error">{error}</div>
        )}

        {showSearchEntry && !isLoading && submittedQuery && !error && results.length === 0 && (
          <div className="global-word-search-status">没有找到“{submittedQuery}”的相关结果</div>
        )}

        {!isLoading && results.length > 0 && selectedResult && (
          <div className="global-word-search-result-area">
            <GlobalWordSearchDetailPanel
              query={submittedQuery || query}
              result={selectedResult}
              onPickWord={handleQuickPickWord}
            />
          </div>
        )}
      </div>
    </div>
  )
}
