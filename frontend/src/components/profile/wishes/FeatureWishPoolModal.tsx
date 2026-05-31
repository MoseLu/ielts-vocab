import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { apiFetch } from '../../../lib'
import { ConfirmDialog, MicroLoading } from '../../ui'
import { BackIcon, CloseIcon, DeleteIcon, EditIcon, ExpandIcon, PlusIcon } from './FeatureWishIcons'
import {
  WISH_STATUS_OPTIONS,
  editableStatusValue,
  statusLabel,
  statusTone,
  type FeatureWishEditableStatus,
} from './featureWishStatus'

interface FeatureWishImage {
  id: number
  thumbnail_url: string
  full_url: string
  original_filename?: string
}

interface FeatureWish {
  id: number
  user_id: number
  username: string
  title: string
  content: string
  status: string
  created_at: string | null
  updated_at: string | null
  can_edit: boolean
  can_delete: boolean
  can_update_status?: boolean
  images: FeatureWishImage[]
}

interface FeatureWishListResponse {
  items: FeatureWish[]
  total: number
}

interface FeatureWishMutationResponse {
  wish: FeatureWish
  error?: string
}

interface FeatureWishDeleteResponse {
  message?: string
  error?: string
}

interface FeatureWishPoolModalProps {
  onClose: () => void
  initialDraftFiles?: File[]
  onDraftSubmitSuccess?: () => void
}

type FormMode = 'create' | 'edit'

function IconButton({
  label,
  className,
  onClick,
  children,
  disabled = false,
}: {
  label: string
  className: string
  onClick: () => void
  children: ReactNode
  disabled?: boolean
}) {
  return (
    <button type="button" className={className} onClick={onClick} aria-label={label} title={label} disabled={disabled}>
      {children}
    </button>
  )
}

function formatDateTime(value: string | null) {
  if (!value) return '时间未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function StatusBadge({ status }: { status: string | null | undefined }) {
  return (
    <span className={`feature-wish-status-badge feature-wish-status-badge--${statusTone(status)}`}>
      {statusLabel(status)}
    </span>
  )
}

function WishMedia({ wish, detail = false }: { wish: FeatureWish; detail?: boolean }) {
  const image = wish.images[0]
  if (!image) {
    return <div className={detail ? 'feature-wish-detail__empty-image' : 'feature-wish-card__empty-media'}>无图</div>
  }
  return (
    <img
      className={detail ? 'feature-wish-detail__image' : 'feature-wish-card__image'}
      src={detail ? image.full_url : image.thumbnail_url}
      alt=""
    />
  )
}

function StatusSelect({
  wish,
  disabled,
  onChange,
}: {
  wish: FeatureWish
  disabled: boolean
  onChange: (wish: FeatureWish, status: FeatureWishEditableStatus) => void
}) {
  if (!wish.can_update_status) return null
  return (
    <select
      aria-label={`设置 bug 状态：${wish.title}`}
      className="feature-wish-status-select"
      disabled={disabled}
      value={editableStatusValue(wish.status)}
      onChange={event => onChange(wish, event.target.value as FeatureWishEditableStatus)}
    >
      {WISH_STATUS_OPTIONS.map(option => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </select>
  )
}

export default function FeatureWishPoolModal({
  onClose,
  initialDraftFiles = [],
  onDraftSubmitSuccess,
}: FeatureWishPoolModalProps) {
  const [wishes, setWishes] = useState<FeatureWish[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedWish, setSelectedWish] = useState<FeatureWish | null>(null)
  const [formMode, setFormMode] = useState<FormMode | null>(initialDraftFiles.length > 0 ? 'create' : null)
  const [editingWish, setEditingWish] = useState<FeatureWish | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftContent, setDraftContent] = useState('')
  const [draftFiles, setDraftFiles] = useState<File[]>(() => initialDraftFiles.slice(0, 3))
  const [submitting, setSubmitting] = useState(false)
  const [deleteWish, setDeleteWish] = useState<FeatureWish | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadWishes = useCallback(async (searchTerm: string) => {
    setLoading(true)
    setError('')
    try {
      const query = searchTerm.trim()
      const url = query ? `/api/feature-wishes?search=${encodeURIComponent(query)}` : '/api/feature-wishes'
      const data = await apiFetch<FeatureWishListResponse>(url)
      setWishes(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'bug 加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadWishes(search)
    }, 200)
    return () => window.clearTimeout(timer)
  }, [loadWishes, search])

  const selectedImages = useMemo(() => selectedWish?.images ?? [], [selectedWish])

  const openForm = (mode: FormMode, wish: FeatureWish | null = null) => {
    setFormMode(mode)
    setEditingWish(wish)
    setDraftTitle(wish?.title ?? '')
    setDraftContent(wish?.content ?? '')
    setDraftFiles([])
    setError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const closeForm = () => {
    setFormMode(null)
    setEditingWish(null)
    setDraftTitle('')
    setDraftContent('')
    setDraftFiles([])
  }

  const handleFiles = (files: FileList | null) => {
    const nextFiles = Array.from(files ?? []).slice(0, 3)
    setDraftFiles(nextFiles)
    if ((files?.length ?? 0) > 3) setError('每个 bug 最多上传三张图片')
  }

  const handleSubmit = async () => {
    if (!draftTitle.trim() || !draftContent.trim()) {
      setError('bug 标题和 bug 内容不能为空')
      return
    }
    if (draftFiles.length > 3) {
      setError('每个 bug 最多上传三张图片')
      return
    }
    const body = new FormData()
    body.append('title', draftTitle.trim())
    body.append('content', draftContent.trim())
    draftFiles.forEach(file => body.append('images', file))
    setSubmitting(true)
    setError('')
    try {
      const url = formMode === 'edit' && editingWish ? `/api/feature-wishes/${editingWish.id}` : '/api/feature-wishes'
      const data = await apiFetch<FeatureWishMutationResponse>(url, {
        method: formMode === 'edit' ? 'PUT' : 'POST',
        body,
      })
      const createdWish = formMode === 'create'
      closeForm()
      if (selectedWish && data.wish.id === selectedWish.id) setSelectedWish(data.wish)
      await loadWishes(search)
      if (createdWish) onDraftSubmitSuccess?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'bug 保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  const requestDelete = (wish: FeatureWish) => {
    setDeleteWish(wish)
  }

  const handleDeleteConfirm = async () => {
    if (!deleteWish) return
    const wish = deleteWish
    setDeleteWish(null)
    setSubmitting(true)
    setError('')
    try {
      await apiFetch<FeatureWishDeleteResponse>(`/api/feature-wishes/${wish.id}`, { method: 'DELETE' })
      if (selectedWish?.id === wish.id) setSelectedWish(null)
      if (editingWish?.id === wish.id) closeForm()
      await loadWishes(search)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'bug 删除失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleStatusChange = async (wish: FeatureWish, status: FeatureWishEditableStatus) => {
    if (status === editableStatusValue(wish.status)) return
    setSubmitting(true)
    setError('')
    try {
      const data = await apiFetch<FeatureWishMutationResponse>(`/api/feature-wishes/${wish.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      setWishes(current => current.map(item => (item.id === data.wish.id ? data.wish : item)))
      setSelectedWish(current => (current?.id === data.wish.id ? data.wish : current))
      setEditingWish(current => (current?.id === data.wish.id ? data.wish : current))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'bug 状态更新失败')
    } finally {
      setSubmitting(false)
    }
  }

  const modal = (
    <div className="feature-wish-modal-overlay" onClick={event => event.target === event.currentTarget && onClose()}>
      <div className="feature-wish-modal" role="dialog" aria-modal="true" aria-label="Bug反馈">
        <div className="feature-wish-modal__header">
          <div className="feature-wish-modal__title">Bug反馈</div>
          <div className="feature-wish-modal__actions">
            <IconButton label="新增 bug" className="feature-wish-modal__icon-button" onClick={() => openForm('create')}>
              <PlusIcon />
            </IconButton>
            <IconButton label="关闭 Bug反馈" className="feature-wish-modal__icon-button" onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </div>
        </div>

        {!selectedWish && (
          <div className="feature-wish-modal__toolbar">
            <input
              value={search}
              onChange={event => setSearch(event.target.value)}
              className="feature-wish-search"
              placeholder="搜索 bug 标题"
            />
          </div>
        )}

        <div className="feature-wish-modal__body">
          {selectedWish ? (
            <div className={`feature-wish-detail feature-wish-detail--${statusTone(selectedWish.status)}`}>
              <div className="feature-wish-detail__header">
                <IconButton label="返回 bug 列表" className="feature-wish-detail__back" onClick={() => setSelectedWish(null)}>
                  <BackIcon />
                </IconButton>
                <div className="feature-wish-detail__heading">
                  <div className="feature-wish-detail__title">{selectedWish.title}</div>
                  <div className="feature-wish-detail__meta">
                    <StatusBadge status={selectedWish.status} />
                    <span>{formatDateTime(selectedWish.created_at)} · {selectedWish.username}</span>
                  </div>
                </div>
                <div className="feature-wish-detail__actions">
                  <StatusSelect wish={selectedWish} disabled={submitting} onChange={handleStatusChange} />
                  {selectedWish.can_edit && (
                    <IconButton label={`编辑 bug：${selectedWish.title}`} className="feature-wish-detail__edit" onClick={() => openForm('edit', selectedWish)}>
                      <EditIcon />
                    </IconButton>
                  )}
                  {selectedWish.can_delete && (
                    <IconButton label={`删除 bug：${selectedWish.title}`} className="feature-wish-detail__delete" onClick={() => requestDelete(selectedWish)} disabled={submitting}>
                      <DeleteIcon />
                    </IconButton>
                  )}
                </div>
              </div>
              <div className="feature-wish-detail__content">
                <div className="feature-wish-detail__gallery">
                  <WishMedia wish={selectedWish} detail />
                  {selectedImages.length > 1 && (
                    <div className="feature-wish-detail__thumbs">
                      {selectedImages.map(image => (
                        <img key={image.id} src={image.thumbnail_url} alt="" />
                      ))}
                    </div>
                  )}
                </div>
                <div className="feature-wish-detail__text">{selectedWish.content}</div>
              </div>
            </div>
          ) : loading ? (
            <div className="feature-wish-state"><MicroLoading text="加载 bug 中..." /></div>
          ) : wishes.length === 0 ? (
            <div className="feature-wish-state">暂无 bug</div>
          ) : (
            <div className="feature-wish-grid">
              {wishes.map(wish => (
                <article key={wish.id} className={`feature-wish-card feature-wish-card--${statusTone(wish.status)}`}>
                  <div className="feature-wish-card__media">
                    <WishMedia wish={wish} />
                    <IconButton label={`展开 bug：${wish.title}`} className="feature-wish-card__expand" onClick={() => setSelectedWish(wish)}>
                      <ExpandIcon />
                    </IconButton>
                  </div>
                  <div className="feature-wish-card__body">
                    <h3>{wish.title}</h3>
                    <p>{wish.content}</p>
                  </div>
                  <div className="feature-wish-card__footer">
                    <div className="feature-wish-card__meta">
                      <StatusBadge status={wish.status} />
                      <span>{formatDateTime(wish.created_at)} · {wish.username}</span>
                    </div>
                    <div className="feature-wish-card__actions">
                      <StatusSelect wish={wish} disabled={submitting} onChange={handleStatusChange} />
                      {wish.can_edit && (
                        <IconButton label={`编辑 bug：${wish.title}`} className="feature-wish-card__edit" onClick={() => openForm('edit', wish)}>
                          <EditIcon />
                        </IconButton>
                      )}
                      {wish.can_delete && (
                        <IconButton label={`删除 bug：${wish.title}`} className="feature-wish-card__delete" onClick={() => requestDelete(wish)} disabled={submitting}>
                          <DeleteIcon />
                        </IconButton>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>

        {error && <div className="feature-wish-error">{error}</div>}

        {formMode && (
          <div className="feature-wish-form-panel">
            <div className="feature-wish-form">
              <div className="feature-wish-form__header">
                <strong>{formMode === 'edit' ? '编辑 bug' : '新增 bug'}</strong>
                <IconButton label="关闭编辑" className="feature-wish-modal__icon-button" onClick={closeForm} disabled={submitting}>
                  <CloseIcon />
                </IconButton>
              </div>
              <input value={draftTitle} onChange={event => setDraftTitle(event.target.value)} placeholder="bug 标题" />
              <textarea value={draftContent} onChange={event => setDraftContent(event.target.value)} placeholder="bug 内容" />
              <input ref={fileInputRef} type="file" accept="image/*" multiple onChange={event => handleFiles(event.target.files)} />
              <div className="feature-wish-form__hint">最多上传 3 张图片；编辑时不选择图片会保留原图。</div>
              {draftFiles.length > 0 && (
                <div className="feature-wish-form__files">
                  {draftFiles.map(file => <span key={`${file.name}-${file.size}`}>{file.name}</span>)}
                </div>
              )}
              <div className="feature-wish-form__actions">
                <button type="button" onClick={closeForm} disabled={submitting}>取消</button>
                <button type="button" onClick={handleSubmit} disabled={submitting}>
                  {submitting ? <MicroLoading text="保存中..." /> : '保存'}
                </button>
              </div>
            </div>
          </div>
        )}

        <ConfirmDialog
          isOpen={deleteWish !== null}
          onClose={() => setDeleteWish(null)}
          onConfirm={() => {
            void handleDeleteConfirm()
          }}
          title="确认删除 bug"
          message={deleteWish ? `确认删除 bug：${deleteWish.title}？删除后将无法恢复。` : ''}
          confirmText="删除"
          variant="danger"
        />
      </div>
    </div>
  )

  if (typeof document === 'undefined') return null
  return createPortal(modal, document.body)
}
