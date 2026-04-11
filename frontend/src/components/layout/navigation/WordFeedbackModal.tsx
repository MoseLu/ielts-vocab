import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../../../lib'
import { useToast } from '../../../contexts'
import { Modal } from '../../ui/Modal'

const FEEDBACK_OPTIONS = [
  { value: 'audio_pronunciation', label: '音频发音问题' },
  { value: 'spelling', label: '单词拼写错误' },
  { value: 'translation', label: '翻译不准' },
  { value: 'other', label: '其他' },
] as const

interface WordFeedbackModalProps {
  isOpen: boolean
  onClose: () => void
  word: string
  phonetic: string
  pos: string
  definition: string
  bookId?: string
  bookTitle?: string
  chapterId?: string | number
  chapterTitle?: string
  exampleEn?: string
  exampleZh?: string
}

export default function WordFeedbackModal({
  isOpen,
  onClose,
  word,
  phonetic,
  pos,
  definition,
  bookId,
  bookTitle,
  chapterId,
  chapterTitle,
  exampleEn,
  exampleZh,
}: WordFeedbackModalProps) {
  const { showToast } = useToast()
  const [selectedTypes, setSelectedTypes] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const sourceMeta = useMemo(
    () => [bookTitle, chapterTitle].filter(Boolean).join(' · '),
    [bookTitle, chapterTitle],
  )

  useEffect(() => {
    if (!isOpen) return
    setSelectedTypes([])
    setSubmitting(false)
    setError('')
  }, [isOpen, word])

  const toggleType = (value: string) => {
    setSelectedTypes(previous => (
      previous.includes(value)
        ? previous.filter(item => item !== value)
        : [...previous, value]
    ))
  }

  const handleSubmit = async () => {
    if (selectedTypes.length === 0) {
      setError('至少选择一个问题类型')
      return
    }

    setSubmitting(true)
    setError('')
    try {
      await apiFetch('/api/books/word-feedback', {
        method: 'POST',
        body: JSON.stringify({
          word,
          phonetic,
          pos,
          definition,
          book_id: bookId ?? null,
          book_title: bookTitle ?? null,
          chapter_id: chapterId != null ? String(chapterId) : null,
          chapter_title: chapterTitle ?? null,
          example_en: exampleEn ?? '',
          example_zh: exampleZh ?? '',
          feedback_types: selectedTypes,
          source: 'global_search',
        }),
      })
      showToast('反馈已提交', 'success')
      onClose()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : '反馈提交失败，请稍后重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="报告问题" size="sm">
      <div className="word-feedback-modal">
        <div className="word-feedback-modal__card">
          <div className="word-feedback-modal__word">{word}</div>
          <div className="word-feedback-modal__meta">
            {[phonetic, pos].filter(Boolean).join('  ')}
          </div>
          <div className="word-feedback-modal__definition">{definition || '暂无释义'}</div>
          {sourceMeta ? (
            <div className="word-feedback-modal__source">{sourceMeta}</div>
          ) : null}
          {exampleEn ? (
            <div className="word-feedback-modal__example">
              <strong>{exampleEn}</strong>
              {exampleZh ? <span>{exampleZh}</span> : null}
            </div>
          ) : null}
        </div>

        <div className="word-feedback-modal__section">
          <div className="word-feedback-modal__label">问题类型（可多选）</div>
          <div className="word-feedback-modal__options">
            {FEEDBACK_OPTIONS.map(option => (
              <label key={option.value} className="word-feedback-modal__option">
                <input
                  type="checkbox"
                  checked={selectedTypes.includes(option.value)}
                  onChange={() => toggleType(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        {error ? <div className="word-feedback-modal__error">{error}</div> : null}

        <div className="word-feedback-modal__actions">
          <button
            type="button"
            className="word-feedback-modal__secondary"
            disabled={submitting}
            onClick={onClose}
          >
            取消
          </button>
          <button
            type="button"
            className="word-feedback-modal__primary"
            disabled={submitting}
            onClick={() => void handleSubmit()}
          >
            {submitting ? '提交中...' : '提交反馈'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
