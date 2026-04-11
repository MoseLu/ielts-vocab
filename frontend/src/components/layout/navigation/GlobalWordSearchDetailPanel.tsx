import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import {
  apiFetch,
  safeParse,
  SaveWordDetailNoteResponseSchema,
  WordDetailResponseSchema,
  type WordDetailResponse,
  type WordSearchResult,
} from '../../../lib'
import { DEFAULT_SETTINGS } from '../../../constants'
import { readAppSettingsFromStorage } from '../../../lib/appSettings'
import { useAuth, useToast } from '../../../contexts'
import type { Word } from '../../practice/types'
import { playExampleAudio, stopAudio } from '../../practice/utils'
import { useFavoriteWords } from '../../../features/vocabulary/hooks'
import ExampleAudioIcon from '../../ui/ExampleAudioIcon'
import GlobalWordSearchActionRail from './GlobalWordSearchActionRail'
import WordFeedbackModal from './WordFeedbackModal'
import { WORD_NOTE_LIMIT } from './globalWordSearchDetailUtils'
type DetailTab = 'examples' | 'root' | 'english' | 'derivatives' | 'notes'
type NoteStatus = 'idle' | 'saving' | 'saved' | 'error'
type GlobalWordSearchDetailPanelProps = {
  onPickWord: (word: string) => void
  query: string
  result: WordSearchResult
}
const DETAIL_TABS: Array<{ id: DetailTab; label: string }> = [
  { id: 'examples', label: '例句' },
  { id: 'root', label: '词根' },
  { id: 'english', label: '英义' },
  { id: 'derivatives', label: '派生' },
  { id: 'notes', label: '笔记' },
]

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function renderHighlightedText(text: string, query: string) {
  const trimmedQuery = query.trim()
  if (!trimmedQuery) return text

  const segments = text.split(new RegExp(`(${escapeRegExp(trimmedQuery)})`, 'ig'))
  return segments.map((segment, index) => (
    <Fragment key={`${segment}-${index}`}>
      {segment.toLowerCase() === trimmedQuery.toLowerCase() ? (
        <mark className="global-word-search-highlight">{segment}</mark>
      ) : (
        segment
      )}
    </Fragment>
  ))
}

function speakWord(word: string): void {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(word)
  utterance.lang = 'en-US'
  utterance.rate = 0.9
  window.speechSynthesis.speak(utterance)
}

function buildNoteStatusLabel(status: NoteStatus): string {
  if (status === 'saving') return '自动保存中...'
  if (status === 'saved') return '已保存到账号'
  if (status === 'error') return '保存失败，请稍后重试'
  return '自动保存到当前账号'
}

export default function GlobalWordSearchDetailPanel({
  onPickWord,
  query,
  result,
}: GlobalWordSearchDetailPanelProps) {
  const { user } = useAuth()
  const { showToast } = useToast()
  const [activeTab, setActiveTab] = useState<DetailTab>('examples')
  const [detailData, setDetailData] = useState<WordDetailResponse | null>(null)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)
  const [detailsError, setDetailsError] = useState<string | null>(null)
  const [noteText, setNoteText] = useState('')
  const [noteStatus, setNoteStatus] = useState<NoteStatus>('idle')
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false)
  const detailAbortRef = useRef<AbortController | null>(null)
  const noteAbortRef = useRef<AbortController | null>(null)
  const lastSyncedNoteRef = useRef('')
  const primaryExampleTextRef = useRef('')

  const summaryDefinition = result.definition || '暂无释义'
  const rootDetail = detailData?.root
  const englishDetail = detailData?.english
  const detailExamples = detailData?.examples ?? result.examples ?? []
  const derivativeDetails = detailData?.derivatives ?? []
  const primaryExample = detailExamples[0] ?? result.examples?.[0]
  const resolvedPhonetic = detailData?.phonetic || result.phonetic || '/暂无音标/'
  const resolvedPos = detailData?.pos || result.pos
  const resolvedDefinition = detailData?.definition || summaryDefinition
  const primaryExampleText = detailExamples[0]?.en?.trim() ?? ''

  const noteStatusLabel = useMemo(() => buildNoteStatusLabel(noteStatus), [noteStatus])
  const favoriteVocabulary = useMemo<Word[]>(() => [{
    word: result.word,
    phonetic: resolvedPhonetic,
    pos: resolvedPos,
    definition: resolvedDefinition,
    book_id: result.book_id,
    book_title: result.book_title,
    chapter_id: result.chapter_id,
    chapter_title: result.chapter_title,
  }], [
    resolvedDefinition,
    resolvedPhonetic,
    resolvedPos,
    result.book_id,
    result.book_title,
    result.chapter_id,
    result.chapter_title,
    result.word,
  ])
  const exampleAudioSettings = useMemo(() => {
    const settings = typeof window === 'undefined'
      ? DEFAULT_SETTINGS
      : readAppSettingsFromStorage()
    return {
      playbackSpeed: String(settings.playbackSpeed ?? DEFAULT_SETTINGS.playbackSpeed),
      volume: String(settings.volume ?? DEFAULT_SETTINGS.volume),
    }
  }, [])
  const { isFavorite, isPending, toggleFavorite } = useFavoriteWords({
    userId: user?.id ?? null,
    vocabulary: favoriteVocabulary,
    showToast,
  })

  useEffect(() => {
    detailAbortRef.current?.abort()
    noteAbortRef.current?.abort()

    setActiveTab('examples')
    setDetailData(null)
    setDetailsError(null)
    setIsLoadingDetails(true)
    setNoteText('')
    setNoteStatus('idle')
    lastSyncedNoteRef.current = ''

    const controller = new AbortController()
    detailAbortRef.current = controller

    const loadWordDetails = async () => {
      try {
        const raw = await apiFetch<unknown>(
          `/api/books/word-details?word=${encodeURIComponent(result.word)}`,
          { signal: controller.signal },
        )
        const parsed = safeParse(WordDetailResponseSchema, raw)
        if (!parsed.success) {
          throw new Error('单词详情格式错误')
        }

        setDetailData(parsed.data)
        setNoteText(parsed.data.note.content)
        lastSyncedNoteRef.current = parsed.data.note.content
        setNoteStatus(parsed.data.note.content ? 'saved' : 'idle')
      } catch (error) {
        if (controller.signal.aborted) return
        setDetailsError(error instanceof Error ? error.message : '单词详情加载失败')
      } finally {
        if (!controller.signal.aborted) {
          setIsLoadingDetails(false)
        }
      }
    }

    void loadWordDetails()

    return () => controller.abort()
  }, [result.word])

  useEffect(() => () => {
    stopAudio()
  }, [result.word])

  useEffect(() => {
    primaryExampleTextRef.current = primaryExampleText
  }, [primaryExampleText])

  useEffect(() => {
    if (activeTab !== 'examples') return

    const handlePlayExampleShortcut = (event: KeyboardEvent) => {
      const visiblePrimaryExampleText = primaryExampleTextRef.current
      if (
        event.repeat
        || event.key !== 'Alt'
        || !event.altKey
        || event.shiftKey
        || event.ctrlKey
        || event.metaKey
        || !visiblePrimaryExampleText
      ) {
        return
      }

      event.preventDefault()
      event.stopImmediatePropagation()
      playExampleAudio(visiblePrimaryExampleText, result.word, exampleAudioSettings)
    }

    window.addEventListener('keydown', handlePlayExampleShortcut, true)
    return () => window.removeEventListener('keydown', handlePlayExampleShortcut, true)
  }, [activeTab, exampleAudioSettings, result.word])

  useEffect(() => {
    if (!detailData) return
    if (noteText === lastSyncedNoteRef.current) return

    const controller = new AbortController()
    noteAbortRef.current?.abort()
    noteAbortRef.current = controller

    const timer = window.setTimeout(async () => {
      setNoteStatus('saving')

      try {
        const raw = await apiFetch<unknown>('/api/books/word-details/note', {
          method: 'PUT',
          body: JSON.stringify({
            word: result.word,
            content: noteText.slice(0, WORD_NOTE_LIMIT),
          }),
          signal: controller.signal,
        })
        const parsed = safeParse(SaveWordDetailNoteResponseSchema, raw)
        if (!parsed.success) {
          throw new Error('笔记保存格式错误')
        }

        lastSyncedNoteRef.current = parsed.data.note.content
        setDetailData(prev => prev ? { ...prev, note: parsed.data.note } : prev)
        setNoteText(parsed.data.note.content)
        setNoteStatus(parsed.data.note.content ? 'saved' : 'idle')
      } catch (error) {
        if (controller.signal.aborted) return
        setNoteStatus('error')
      }
    }, 400)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [detailData, noteText, result.word])

  const handleFavoriteToggle = () => {
    void toggleFavorite(favoriteVocabulary[0], {
      bookId: result.book_id,
      chapterId: result.chapter_id != null ? String(result.chapter_id) : null,
      chapterTitle: result.chapter_title ?? null,
    })
  }

  const handleOpenFeedback = () => {
    if (!user) {
      showToast('登录后才能提交反馈', 'info')
      return
    }
    setIsFeedbackOpen(true)
  }

  return (
    <div className="global-word-search-detail">
      <div className="global-word-search-detail-frame">
        <div className="global-word-search-detail-main">
          <div className="global-word-search-detail-header">
            <div className="global-word-search-detail-heading">
              <div className="global-word-search-heading-row">
                <h2 className="global-word-search-word">{result.word}</h2>
                <span className="global-word-search-phonetic">{resolvedPhonetic}</span>
              </div>
              <p className="global-word-search-summary">{resolvedPos} {resolvedDefinition}</p>
            </div>
          </div>

          {result.listening_confusables?.length ? (
            <section className="global-word-search-memory-card" aria-label="串记">
              <span className="global-word-search-memory-badge">串记</span>
              <div className="global-word-search-memory-list">
                {result.listening_confusables.slice(0, 6).map(candidate => (
                  <button
                    key={`${result.word}-${candidate.word}`}
                    type="button"
                    className="global-word-search-memory-item"
                    onClick={() => onPickWord(candidate.word)}
                  >
                    <strong>{candidate.word}</strong>
                    <span>{candidate.definition || '暂无释义'}</span>
                  </button>
                ))}
              </div>
            </section>
          ) : null}

          <div className="global-word-search-tabs" role="tablist" aria-label="单词详情模块">
            {DETAIL_TABS.map(tab => {
              const isActive = tab.id === activeTab
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`global-word-search-tab${isActive ? ' is-active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              )
            })}
          </div>

          {activeTab === 'examples' && (
            <section className="global-word-search-section">
              {detailExamples.length ? (
                <div className="global-word-search-examples">
                  {detailExamples.slice(0, 5).map((example, index) => (
                    <article key={`${result.word}-${index}`} className="global-word-search-example">
                      <div className="global-word-search-example-header">
                        <p className="global-word-search-example-en">
                          {renderHighlightedText(example.en || '暂无英文例句', query)}
                        </p>
                        {example.en ? (
                          <button
                            type="button"
                            className="global-word-search-audio global-word-search-audio--icon global-word-search-audio--example"
                            aria-label={`朗读例句 ${index + 1}`}
                            title={`朗读例句 ${index + 1}（快捷键 Alt）`}
                            onClick={() => playExampleAudio(example.en, result.word, exampleAudioSettings)}
                          >
                            <ExampleAudioIcon className="example-audio-icon" />
                          </button>
                        ) : null}
                      </div>
                      <p className="global-word-search-example-zh">
                        {renderHighlightedText(example.zh || '暂无中文释义', query)}
                      </p>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="global-word-search-empty-panel">当前词条还没有收录例句。</div>
              )}
            </section>
          )}

          {activeTab === 'english' && (
            <section className="global-word-search-section">
              {isLoadingDetails && !englishDetail ? (
                <div className="global-word-search-empty-panel">正在加载英义…</div>
              ) : detailsError && !englishDetail ? (
                <div className="global-word-search-empty-panel">{detailsError}</div>
              ) : englishDetail?.entries.length ? (
                <div className="global-word-search-root-card">
                  <div className="global-word-search-root-explainer">
                    {englishDetail.entries.map((item, index) => (
                      <p key={`${item.pos}-${index}`}>
                        <strong>{item.pos || '释义'}</strong>
                        {' '}
                        {item.definition}
                      </p>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="global-word-search-empty-panel">当前词条还没有英义。</div>
              )}
            </section>
          )}

          {activeTab === 'root' && (
            <section className="global-word-search-section">
              {isLoadingDetails && !rootDetail ? (
                <div className="global-word-search-empty-panel">正在加载词根信息…</div>
              ) : detailsError && !rootDetail ? (
                <div className="global-word-search-empty-panel">{detailsError}</div>
              ) : rootDetail ? (
                <div className="global-word-search-root-card">
                  <div className="global-word-search-root-segments">
                    {rootDetail.segments.map(segment => (
                      <div key={`${segment.kind}-${segment.text}`} className="global-word-search-root-segment">
                        <span className="global-word-search-root-kind">{segment.kind}</span>
                        <strong>{segment.text}</strong>
                      </div>
                    ))}
                  </div>
                  <p className="global-word-search-root-summary">{rootDetail.summary}</p>
                  <div className="global-word-search-root-explainer">
                    {rootDetail.segments.map(segment => (
                      <p key={`explain-${segment.kind}-${segment.text}`}>
                        <strong>{segment.text}</strong>
                        {' '}
                        {segment.meaning}
                      </p>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="global-word-search-empty-panel">当前词条还没有词根信息。</div>
              )}
            </section>
          )}

          {activeTab === 'derivatives' && (
            <section className="global-word-search-section">
              {isLoadingDetails && !detailData ? (
                <div className="global-word-search-empty-panel">正在匹配常见派生词…</div>
              ) : detailsError && !detailData ? (
                <div className="global-word-search-empty-panel">{detailsError}</div>
              ) : derivativeDetails.length === 0 ? (
                <div className="global-word-search-empty-panel">当前还没有匹配到常见派生词。</div>
              ) : (
                <div className="global-word-search-derivatives">
                  {derivativeDetails.map(word => (
                    <button
                      key={word.word}
                      type="button"
                      className="global-word-search-derivative"
                      onClick={() => onPickWord(word.word)}
                    >
                      <div className="global-word-search-derivative-heading">
                        <strong>{word.word}</strong>
                        <span>{word.phonetic || '/暂无音标/'}</span>
                      </div>
                      <span className="global-word-search-derivative-meta">
                        {word.pos || '词性待补充'}
                        {' · '}
                        {word.definition || '暂无释义'}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </section>
          )}

          {activeTab === 'notes' && (
            <section className="global-word-search-section">
              {isLoadingDetails && !detailData ? (
                <div className="global-word-search-empty-panel">正在加载笔记…</div>
              ) : detailsError && !detailData ? (
                <div className="global-word-search-empty-panel">{detailsError}</div>
              ) : (
                <div className="global-word-search-notes">
                  <textarea
                    value={noteText}
                    className="global-word-search-notes-input"
                    maxLength={WORD_NOTE_LIMIT}
                    placeholder="输入笔记内容"
                    onChange={(event) => setNoteText(event.target.value)}
                  />
                  <div className="global-word-search-notes-footer">
                    <span>{noteStatusLabel}</span>
                    <span>{noteText.length} / {WORD_NOTE_LIMIT}</span>
                  </div>
                </div>
              )}
            </section>
          )}
        </div>

        <GlobalWordSearchActionRail
          favoriteActive={isFavorite(result.word)}
          favoritePending={isPending(result.word)}
          word={result.word}
          onToggleFavorite={handleFavoriteToggle}
          onPlayWord={() => speakWord(result.word)}
          onOpenFeedback={handleOpenFeedback}
        />
      </div>

      <WordFeedbackModal
        isOpen={isFeedbackOpen}
        word={result.word}
        phonetic={resolvedPhonetic}
        pos={resolvedPos}
        definition={resolvedDefinition}
        bookId={result.book_id}
        bookTitle={result.book_title}
        chapterId={result.chapter_id}
        chapterTitle={result.chapter_title}
        exampleEn={primaryExample?.en}
        exampleZh={primaryExample?.zh}
        onClose={() => setIsFeedbackOpen(false)}
      />
    </div>
  )
}
