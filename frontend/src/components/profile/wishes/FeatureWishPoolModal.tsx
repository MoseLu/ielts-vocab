import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { apiFetch } from '../../../lib'
import { MicroLoading } from '../../ui'

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
  created_at: string | null
  updated_at: string | null
  can_edit: boolean
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

interface FeatureWishPoolModalProps {
  onClose: () => void
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

function ExpandIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <polyline points="15 3 21 3 21 9" />
      <polyline points="9 21 3 21 3 15" />
      <line x1="21" y1="3" x2="14" y2="10" />
      <line x1="3" y1="21" x2="10" y2="14" />
    </svg>
  )
}

function EditIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
    </svg>
  )
}

function BackIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
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

export default function FeatureWishPoolModal({ onClose }: FeatureWishPoolModalProps) {
  const [wishes, setWishes] = useState<FeatureWish[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedWish, setSelectedWish] = useState<FeatureWish | null>(null)
  const [formMode, setFormMode] = useState<FormMode | null>(null)
  const [editingWish, setEditingWish] = useState<FeatureWish | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftContent, setDraftContent] = useState('')
  const [draftFiles, setDraftFiles] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
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
      setError(err instanceof Error ? err.message : '愿望加载失败')
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
    if ((files?.length ?? 0) > 3) setError('每个愿望最多上传三张图片')
  }

  const handleSubmit = async () => {
    if (!draftTitle.trim() || !draftContent.trim()) {
      setError('愿望名和愿望内容不能为空')
      return
    }
    if (draftFiles.length > 3) {
      setError('每个愿望最多上传三张图片')
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
      closeForm()
      if (selectedWish && data.wish.id === selectedWish.id) setSelectedWish(data.wish)
      await loadWishes(search)
    } catch (err) {
      setError(err instanceof Error ? err.message : '愿望保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  const modal = (
    <div className="feature-wish-modal-overlay" onClick={event => event.target === event.currentTarget && onClose()}>
      <div className="feature-wish-modal" role="dialog" aria-modal="true" aria-label="功能许愿池">
        <div className="feature-wish-modal__header">
          <div className="feature-wish-modal__title">功能许愿池</div>
          <div className="feature-wish-modal__actions">
            <IconButton label="新增愿望" className="feature-wish-modal__icon-button" onClick={() => openForm('create')}>
              <PlusIcon />
            </IconButton>
            <IconButton label="关闭功能许愿池" className="feature-wish-modal__icon-button" onClick={onClose}>
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
              placeholder="搜索愿望名"
            />
          </div>
        )}

        <div className="feature-wish-modal__body">
          {selectedWish ? (
            <div className="feature-wish-detail">
              <div className="feature-wish-detail__header">
                <IconButton label="返回愿望列表" className="feature-wish-detail__back" onClick={() => setSelectedWish(null)}>
                  <BackIcon />
                </IconButton>
                <div className="feature-wish-detail__heading">
                  <div className="feature-wish-detail__title">{selectedWish.title}</div>
                  <div className="feature-wish-detail__meta">
                    {formatDateTime(selectedWish.created_at)} · {selectedWish.username}
                  </div>
                </div>
                {selectedWish.can_edit && (
                  <IconButton label={`编辑愿望：${selectedWish.title}`} className="feature-wish-detail__edit" onClick={() => openForm('edit', selectedWish)}>
                    <EditIcon />
                  </IconButton>
                )}
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
            <div className="feature-wish-state"><MicroLoading text="加载愿望中..." /></div>
          ) : wishes.length === 0 ? (
            <div className="feature-wish-state">暂无愿望</div>
          ) : (
            <div className="feature-wish-grid">
              {wishes.map(wish => (
                <article key={wish.id} className="feature-wish-card">
                  <div className="feature-wish-card__media">
                    <WishMedia wish={wish} />
                    <IconButton label={`展开愿望：${wish.title}`} className="feature-wish-card__expand" onClick={() => setSelectedWish(wish)}>
                      <ExpandIcon />
                    </IconButton>
                  </div>
                  <div className="feature-wish-card__body">
                    <h3>{wish.title}</h3>
                    <p>{wish.content}</p>
                  </div>
                  <div className="feature-wish-card__footer">
                    <span>{formatDateTime(wish.created_at)} · {wish.username}</span>
                    {wish.can_edit && (
                      <IconButton label={`编辑愿望：${wish.title}`} className="feature-wish-card__edit" onClick={() => openForm('edit', wish)}>
                        <EditIcon />
                      </IconButton>
                    )}
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
                <strong>{formMode === 'edit' ? '编辑愿望' : '新增愿望'}</strong>
                <IconButton label="关闭编辑" className="feature-wish-modal__icon-button" onClick={closeForm} disabled={submitting}>
                  <CloseIcon />
                </IconButton>
              </div>
              <input value={draftTitle} onChange={event => setDraftTitle(event.target.value)} placeholder="愿望名" />
              <textarea value={draftContent} onChange={event => setDraftContent(event.target.value)} placeholder="愿望内容" />
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
      </div>
    </div>
  )

  if (typeof document === 'undefined') return null
  return createPortal(modal, document.body)
}
