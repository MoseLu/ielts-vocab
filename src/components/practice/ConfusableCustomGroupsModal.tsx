import {
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { useToast } from '../../contexts'
import { apiFetch } from '../../lib'
import { Modal, Textarea } from '../ui'

const MAX_GROUPS = 12
const MAX_WORDS_PER_GROUP = 8
const WORD_TOKEN_RE = /[A-Za-z]+(?:[-'][A-Za-z]+)*/g

export interface CustomConfusableChapter {
  id: number | string
  title: string
  word_count?: number
  is_custom?: boolean
}

export interface ParsedConfusableDraft {
  groups: string[][]
  lineCount: number
  issues: string[]
}

interface CreateCustomConfusableResponse {
  created_count?: number
  created_chapters?: CustomConfusableChapter[]
}

interface ConfusableCustomGroupsModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated?: (chapters: CustomConfusableChapter[]) => void
}

export function parseConfusableCustomDraft(draft: string): ParsedConfusableDraft {
  const rawLines = draft
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)

  const issues: string[] = []
  const groups = rawLines.map((line, index) => {
    const tokens = line.match(WORD_TOKEN_RE) ?? []
    const seen = new Set<string>()
    const words: string[] = []

    tokens.forEach(token => {
      const normalized = token.trim().toLowerCase()
      if (!normalized || seen.has(normalized)) return
      seen.add(normalized)
      words.push(normalized)
    })

    if (words.length < 2) {
      issues.push(`第 ${index + 1} 组至少需要 2 个不同单词`)
    } else if (words.length > MAX_WORDS_PER_GROUP) {
      issues.push(`第 ${index + 1} 组最多支持 ${MAX_WORDS_PER_GROUP} 个单词`)
    }

    return words
  })

  if (groups.length > MAX_GROUPS) {
    issues.push(`一次最多创建 ${MAX_GROUPS} 组易混词`)
  }

  return {
    groups,
    lineCount: rawLines.length,
    issues,
  }
}

export default function ConfusableCustomGroupsModal({
  isOpen,
  onClose,
  onCreated,
}: ConfusableCustomGroupsModalProps) {
  const { showToast } = useToast()
  const [draft, setDraft] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const deferredDraft = useDeferredValue(draft)
  const parsedDraft = useMemo(() => parseConfusableCustomDraft(deferredDraft), [deferredDraft])
  const canSubmit =
    parsedDraft.groups.length > 0 &&
    parsedDraft.issues.length === 0 &&
    !submitting

  useEffect(() => {
    if (isOpen) return
    setDraft('')
    setSubmitError('')
    setSubmitting(false)
  }, [isOpen])

  const handleSubmit = async () => {
    if (!parsedDraft.groups.length) {
      setSubmitError('请至少输入一组易混词')
      return
    }

    if (parsedDraft.issues.length > 0) {
      setSubmitError(parsedDraft.issues[0] ?? '输入格式不正确')
      return
    }

    setSubmitting(true)
    setSubmitError('')

    try {
      const response = await apiFetch<CreateCustomConfusableResponse>(
        '/api/books/ielts_confusable_match/custom-chapters',
        {
          method: 'POST',
          body: JSON.stringify({ groups: parsedDraft.groups }),
        },
      )

      const chapters = response.created_chapters ?? []
      const createdCount = response.created_count ?? chapters.length
      showToast(`已创建 ${createdCount} 组自定义易混词`, 'success')
      onCreated?.(chapters)
      onClose()
    } catch (error) {
      const message = error instanceof Error ? error.message : '创建自定义组失败'
      setSubmitError(message)
      showToast(message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!submitting) onClose()
      }}
      title="新建自定义易混组"
      size="lg"
    >
      <div className="confusable-custom-modal">
        <p className="confusable-custom-lead">
          每行一组，只输入英文单词。词与词之间用空格、逗号或换行分开，中文释义和音标会自动补齐。
        </p>

        <Textarea
          value={draft}
          onChange={event => {
            setDraft(event.target.value)
            if (submitError) setSubmitError('')
          }}
          rows={8}
          placeholder={[
            'collect college colleague collide',
            'affect effect',
            'adapt adopt adept',
          ].join('\n')}
          className="confusable-custom-textarea"
        />

        <div className="confusable-custom-meta">
          <span>{parsedDraft.lineCount || 0} 组草稿</span>
          <span>每组 2-{MAX_WORDS_PER_GROUP} 个单词</span>
          <span>一次最多 {MAX_GROUPS} 组</span>
        </div>

        <div className="confusable-custom-preview">
          {parsedDraft.groups.length > 0 ? (
            parsedDraft.groups.slice(0, MAX_GROUPS).map((group, index) => (
              <div key={`${index}-${group.join('-')}`} className="confusable-custom-preview-row">
                <span className="confusable-custom-preview-label">第 {index + 1} 组</span>
                <div className="confusable-custom-preview-chips">
                  {group.map(word => (
                    <span key={word} className="confusable-custom-chip">{word}</span>
                  ))}
                </div>
              </div>
            ))
          ) : (
            <div className="confusable-custom-empty">
              输入后会在这里预览每个易混组。
            </div>
          )}
        </div>

        {(submitError || parsedDraft.issues[0]) && (
          <div className="confusable-custom-error" role="alert">
            {submitError || parsedDraft.issues[0]}
          </div>
        )}

        <div className="confusable-custom-actions">
          <button
            type="button"
            className="confusable-custom-btn confusable-custom-btn--ghost"
            onClick={onClose}
            disabled={submitting}
          >
            取消
          </button>
          <button
            type="button"
            className="confusable-custom-btn confusable-custom-btn--primary"
            onClick={() => { void handleSubmit() }}
            disabled={!canSubmit}
          >
            {submitting ? '创建中...' : '创建并开始练习'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
