import {
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { useToast } from '../../contexts'
import { apiFetch } from '../../lib'
import { Modal, Textarea } from '../ui'
import type { Word } from './types'

const MAX_GROUPS = 12
const MAX_WORDS_PER_GROUP = 8
const WORD_TOKEN_RE = /[A-Za-z]+(?:[-'][A-Za-z]+)*/g
const GROUP_CONTINUATION_RE = /[，,;；、/]\s*$/

export interface CustomConfusableChapter {
  id: number | string
  title: string
  word_count?: number
  group_count?: number
  is_custom?: boolean
}

export interface ParsedConfusableDraft {
  groups: string[][]
  groupCount: number
  issues: string[]
}

interface CreateCustomConfusableResponse {
  created_count?: number
  created_chapters?: CustomConfusableChapter[]
}

interface UpdateCustomConfusableResponse {
  chapter?: CustomConfusableChapter
  words?: Word[]
}

interface ConfusableCustomGroupsModalProps {
  isOpen: boolean
  onClose: () => void
  editChapter?: CustomConfusableChapter | null
  initialWords?: string[]
  onCreated?: (chapters: CustomConfusableChapter[]) => void
  onUpdated?: (chapter: CustomConfusableChapter, words: Word[]) => void
}

export function parseConfusableCustomDraft(draft: string): ParsedConfusableDraft {
  const issues: string[] = []
  const groups: string[][] = []
  const rawSections = draft
    .split(/\r?\n\s*\r?\n/g)
    .map(section => section.trim())
    .filter(Boolean)

  const parseGroupWords = (rawGroup: string): string[] => {
    const tokens = rawGroup.match(WORD_TOKEN_RE) ?? []
    const seen = new Set<string>()
    const words: string[] = []

    tokens.forEach(token => {
      const normalized = token.trim().toLowerCase()
      if (!normalized || seen.has(normalized)) return
      seen.add(normalized)
      words.push(normalized)
    })

    return words
  }

  rawSections.forEach(section => {
    const sectionLines = section
      .split(/\r?\n/)
      .map(line => line.trim())
      .filter(Boolean)

    const shouldMergeAsSingleGroup =
      sectionLines.length === 1 ||
      sectionLines.every(line => (line.match(WORD_TOKEN_RE) ?? []).length <= 1) ||
      sectionLines.some(line => GROUP_CONTINUATION_RE.test(line))

    const rawGroups = shouldMergeAsSingleGroup ? [section] : sectionLines

    rawGroups.forEach(rawGroup => {
      const words = parseGroupWords(rawGroup)
      const groupIndex = groups.length + 1

      if (words.length < 2) {
        issues.push(`第 ${groupIndex} 组至少需要 2 个不同单词`)
      } else if (words.length > MAX_WORDS_PER_GROUP) {
        issues.push(`第 ${groupIndex} 组最多支持 ${MAX_WORDS_PER_GROUP} 个单词`)
      }

      groups.push(words)
    })
  })

  if (groups.length > MAX_GROUPS) {
    issues.push(`一次最多创建 ${MAX_GROUPS} 组易混词`)
  }

  return {
    groups,
    groupCount: groups.length,
    issues,
  }
}

export default function ConfusableCustomGroupsModal({
  isOpen,
  onClose,
  editChapter,
  initialWords,
  onCreated,
  onUpdated,
}: ConfusableCustomGroupsModalProps) {
  const { showToast } = useToast()
  const [draft, setDraft] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const isEditMode = Boolean(editChapter)

  const deferredDraft = useDeferredValue(draft)
  const parsedDraft = useMemo(() => parseConfusableCustomDraft(deferredDraft), [deferredDraft])
  const canSubmit =
    parsedDraft.groups.length > 0 &&
    parsedDraft.issues.length === 0 &&
    !submitting

  useEffect(() => {
    if (!isOpen) {
      setDraft('')
      setSubmitError('')
      setSubmitting(false)
      return
    }
    if (isEditMode) {
      setDraft((initialWords ?? []).join(', '))
    }
  }, [initialWords, isEditMode, isOpen])

  const handleSubmit = async () => {
    if (!parsedDraft.groups.length) {
      setSubmitError('请至少输入一组易混词')
      return
    }

    if (parsedDraft.issues.length > 0) {
      setSubmitError(parsedDraft.issues[0] ?? '输入格式不正确')
      return
    }

    if (isEditMode && parsedDraft.groups.length !== 1) {
      setSubmitError('编辑当前组时只能保留一组单词')
      return
    }

    setSubmitting(true)
    setSubmitError('')

    try {
      if (isEditMode && editChapter) {
        const response = await apiFetch<UpdateCustomConfusableResponse>(
          `/api/books/ielts_confusable_match/custom-chapters/${editChapter.id}`,
          {
            method: 'PUT',
            body: JSON.stringify({ words: parsedDraft.groups[0] }),
          },
        )

        if (!response.chapter) {
          throw new Error('更新后的章节数据缺失')
        }

        const updatedWords = response.words ?? []
        showToast('已更新当前自定义易混组', 'success')
        onUpdated?.(response.chapter, updatedWords)
        onClose()
        return
      }

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
      title={isEditMode ? '编辑当前易混组' : '新建自定义易混组'}
      size="lg"
    >
      <div className="confusable-custom-modal">
        <p className="confusable-custom-lead">
          支持 2-8 个词组成一组。只输入英文单词，中文释义和音标会自动补齐。
        </p>

        <div className="confusable-custom-rules" aria-label="导入规则">
          <div className="confusable-custom-rule">
            <strong>简单写法</strong>
            <span>一行就是一组，组内用空格、逗号或顿号分开。</span>
          </div>
          <div className="confusable-custom-rule">
            <strong>长组写法</strong>
            <span>同一组可以连续写多行；只有空行才表示下一组。换行续写时，上一行末尾保留逗号更稳。</span>
          </div>
        </div>

        <Textarea
          value={draft}
          onChange={event => {
            setDraft(event.target.value)
            if (submitError) setSubmitError('')
          }}
          rows={8}
          placeholder={[
            'strick, stock, struck,',
            'striking, string',
            '',
            'affect effect',
            'adapt adopt adept',
          ].join('\n')}
          className="confusable-custom-textarea"
        />

        <div className="confusable-custom-meta">
          <span>{parsedDraft.groupCount || 0} 组草稿</span>
          <span>每组 2-{MAX_WORDS_PER_GROUP} 个单词</span>
          <span>一次最多 {MAX_GROUPS} 组</span>
        </div>

        <div className="confusable-custom-preview">
          {parsedDraft.groups.length > 0 ? (
            parsedDraft.groups.slice(0, MAX_GROUPS).map((group, index) => (
              <div key={`${index}-${group.join('-')}`} className="confusable-custom-preview-row">
                <div className="confusable-custom-preview-head">
                  <span className="confusable-custom-preview-label">第 {index + 1} 组</span>
                  <span className="confusable-custom-preview-meta">
                    {group.length} 个词 · {group.length * 2} 张卡片
                  </span>
                </div>
                <div className="confusable-custom-preview-chips">
                  {group.map(word => (
                    <span key={word} className="confusable-custom-chip">{word}</span>
                  ))}
                </div>
              </div>
            ))
          ) : (
            <div className="confusable-custom-empty">
              输入后会在这里预览每组包含几个词，以及练习时会生成多少张卡片。
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
            {submitting ? (isEditMode ? '保存中...' : '创建中...') : (isEditMode ? '保存并刷新当前组' : '创建并开始练习')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
