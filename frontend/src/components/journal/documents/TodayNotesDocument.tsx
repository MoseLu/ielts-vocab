import { useCallback, useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { createPortal } from 'react-dom'
import { htmlToMarkdown } from '../../../lib/htmlToMarkdown'
import { extractJournalImages, MAX_JOURNAL_IMAGES, stripJournalImages } from '../../../lib/journalImages'
import { renderJournalMarkdown } from '../../../lib/journalMarkdown'
import type { JournalEntry } from '../../../lib/schemas'
import { Button } from '../../ui/Button'
import { Modal } from '../../ui/Modal'

interface TodayNotesDocumentProps {
  entry: JournalEntry | null
  editMode: boolean
  polishing: boolean
  polishedPreview: string | null
  onSave: (content: string) => void
  onDraftChange: (content: string) => void
  onPolish: (content?: string) => void
  onAcceptPolish: () => void
  onRejectPolish: () => void
  formatDateTime: (iso: string) => string
}

interface CtxMenuState { x: number; y: number; visible: boolean }

/* -- Image Gallery -- */

const TODAY_RECAP_PLACEHOLDER = '写下今日复盘：今天完成了什么、进度如何、哪里需要查漏补缺、下一步怎么安排。'

interface ImageGalleryProps {
  images: string[]
  isReadOnly?: boolean
  onAddImage?: () => void
  onRemove: (idx: number) => void
}

function ImageGallery({ images, isReadOnly, onAddImage, onRemove }: ImageGalleryProps) {
  const [previewIndex, setPreviewIndex] = useState<number | null>(null)
  const previewSrc = previewIndex === null ? null : images[previewIndex] ?? null

  if (images.length === 0 && isReadOnly) return null

  return (
    <section
      className={`journal-image-panel ${isReadOnly ? 'journal-image-panel--readonly' : ''}`}
      aria-label="日记图片附件"
    >
      <div className="journal-image-panel__head">
        <span className="journal-image-panel__title">图片附件</span>
        <span className="journal-image-panel__count">{images.length}/{MAX_JOURNAL_IMAGES}</span>
      </div>
      <div className={`journal-image-card-grid ${isReadOnly ? 'journal-image-card-grid--readonly' : ''}`}>
        {images.map((src, i) => (
          <figure key={i} className="journal-image-card">
            <button type="button" className="journal-image-card__preview" aria-label={`预览图片 ${i + 1}`} onClick={() => setPreviewIndex(i)}>
              <img src={src} alt={`附件 ${i + 1}`} />
            </button>
            <figcaption>图片 {i + 1}</figcaption>
            {!isReadOnly && (
              <button className="journal-image-card__remove" title="移除图片" aria-label={`移除图片 ${i + 1}`} onClick={() => onRemove(i)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            )}
          </figure>
        ))}
        {!isReadOnly && images.length < MAX_JOURNAL_IMAGES ? (
          <button className="journal-image-card journal-image-card--add" type="button" onClick={onAddImage}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="22" height="22" aria-hidden="true">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <path d="M21 15l-5-5L5 21" />
              <path d="M12 7v6" />
              <path d="M9 10h6" />
            </svg>
            <span>添加图片</span>
            <small>最多 {MAX_JOURNAL_IMAGES} 张</small>
          </button>
        ) : null}
      </div>
      {previewSrc && createPortal(
        <div className="bug-screenshot-preview-overlay" role="dialog" aria-modal="true" aria-label="日记图片预览" onClick={event => event.target === event.currentTarget && setPreviewIndex(null)}>
          <div className="bug-screenshot-preview">
            <div className="bug-screenshot-preview__header">
              <strong>图片 {previewIndex! + 1}</strong>
              <button type="button" aria-label="关闭日记图片预览" onClick={() => setPreviewIndex(null)}>×</button>
            </div>
            <div className="bug-screenshot-preview__image-stage">
              <img src={previewSrc} alt={`日记图片预览 ${previewIndex! + 1}`} />
            </div>
          </div>
        </div>,
        document.body,
      )}
    </section>
  )
}

/* ── Context Menu ── */

function EditorContextMenu({ x, y, onClose, onInsertImage }: { x: number; y: number; onClose: () => void; onInsertImage: () => void }) {
  return (
    <div
      className="journal-ctx-menu"
      style={{
        '--journal-ctx-left': `${x}px`,
        '--journal-ctx-top': `${y}px`,
      } as CSSProperties}
      role="menu"
    >
      <button className="journal-ctx-menu-item" role="menuitem" onClick={() => { onInsertImage(); onClose() }}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" />
        </svg>
        <span>插入图片</span>
      </button>
    </div>
  )
}

/* ── Polish Modal ── */

function PolishModal({ original, polished, onAccept, onReject, onContinuePolish, polishing }: {
  original: string; polished: string; onAccept: () => void; onReject: () => void; onContinuePolish: () => void; polishing: boolean
}) {
  return (
    <Modal isOpen onClose={onReject} title="AI 润色预览" size="xl" closeOnOverlay={false}>
      <div className="journal-polish-modal">
        <p className="journal-polish-modal__intro">确认润色结果后再应用到今天的日记正文。</p>
        <div className="journal-polish-modal__grid">
          <section className="journal-polish-modal__col" aria-label="原文">
            <h3 className="journal-polish-modal__label">原文</h3>
            <div className="journal-polish-modal__content markdown-content" dangerouslySetInnerHTML={{ __html: renderJournalMarkdown(original) }} />
          </section>
          <section className="journal-polish-modal__col journal-polish-modal__col--result" aria-label="润色后">
            <h3 className="journal-polish-modal__label">润色后</h3>
            <div className="journal-polish-modal__content markdown-content" dangerouslySetInnerHTML={{ __html: renderJournalMarkdown(polished) }} />
          </section>
        </div>
        <div className="ui-modal__actions journal-polish-modal__actions">
          <Button variant="secondary" onClick={onContinuePolish} isLoading={polishing}>
            {polishing ? '润色中' : '继续润色'}
          </Button>
          <Button variant="ghost" onClick={onReject}>拒绝</Button>
          <Button onClick={onAccept}>接受修改</Button>
        </div>
      </div>
    </Modal>
  )
}

/* ── Main Component ── */

export default function TodayNotesDocument({
  entry, editMode, polishing, polishedPreview, onSave, onDraftChange, onPolish, onAcceptPolish, onRejectPolish, formatDateTime,
}: TodayNotesDocumentProps) {
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [showPolishModal, setShowPolishModal] = useState(false)
  const [polishContent, setPolishContent] = useState('')
  const [ctxMenu, setCtxMenu] = useState<CtxMenuState>({ x: 0, y: 0, visible: false })
  const [images, setImages] = useState<string[]>([])

  // Load images from entry on mount / entry change
  useEffect(() => {
    if (entry?.content) {
      setImages(extractJournalImages(entry.content))
    }
  }, [entry?.content])

  const textContent = entry?.content ? stripJournalImages(entry.content) : ''

  const editor = useEditor({
    extensions: [StarterKit, Placeholder.configure({ placeholder: TODAY_RECAP_PLACEHOLDER })],
    content: textContent ? renderJournalMarkdown(textContent) : '',
    editorProps: { attributes: { class: 'journal-editor-content' } },
    onUpdate: ({ editor }) => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
      const md = htmlToMarkdown(editor.getHTML())
      onDraftChange(md)
      saveTimerRef.current = setTimeout(() => {
        saveCombined(md, images)
      }, 2000)
    },
  })

  const saveCombined = useCallback((textMd: string, imgs: string[]) => {
    const imgBlock = imgs.slice(0, MAX_JOURNAL_IMAGES).map((src, i) => `![image-${i + 1}](${src})`).join('\n')
    const combined = [textMd.trim(), imgBlock].filter(Boolean).join('\n\n')
    onDraftChange(textMd.trim())
    onSave(combined)
  }, [onDraftChange, onSave])

  const insertImage = useCallback(() => {
    if (images.length >= MAX_JOURNAL_IMAGES) return
    const inp = document.createElement('input')
    inp.type = 'file'; inp.accept = 'image/*'
    inp.onchange = (ev: Event) => {
      const file = (ev.target as HTMLInputElement).files?.[0]
      if (!file) return
      const r = new FileReader()
      r.onload = () => {
        const dataUrl = r.result as string
        setImages(prev => {
          const next = [...prev, dataUrl].slice(0, MAX_JOURNAL_IMAGES)
          // Immediate save
          if (editor) {
            saveCombined(htmlToMarkdown(editor.getHTML()), next)
          }
          return next
        })
      }
      r.readAsDataURL(file)
    }
    inp.click()
  }, [editor, images.length, saveCombined])

  const removeImage = useCallback((idx: number) => {
    setImages(prev => {
      const next = prev.filter((_, i) => i !== idx)
      if (editor) {
        saveCombined(htmlToMarkdown(editor.getHTML()), next)
      }
      return next
    })
  }, [editor, saveCombined])

  useEffect(() => {
    if (!editor || !editMode) return
    const el = editor.view.dom
    const onCtx = (e: MouseEvent) => {
      if (images.length >= MAX_JOURNAL_IMAGES) return
      e.preventDefault()
      setCtxMenu({ x: e.clientX, y: e.clientY, visible: true })
    }
    el.addEventListener('contextmenu', onCtx)
    return () => el.removeEventListener('contextmenu', onCtx)
  }, [editor, editMode, images.length])

  useEffect(() => {
    if (images.length >= MAX_JOURNAL_IMAGES) {
      setCtxMenu(prev => ({ ...prev, visible: false }))
    }
  }, [images.length])

  useEffect(() => {
    if (!editor) return
    const cur = editor.getHTML()
    if (!editMode || !cur || cur === '<p></p>') {
      const target = textContent ? renderJournalMarkdown(textContent) : ''
      if (cur !== target) editor.commands.setContent(target)
    }
  }, [textContent, editor, editMode])

  useEffect(() => {
    onDraftChange(textContent)
  }, [onDraftChange, textContent])

  useEffect(() => { if (polishedPreview) { setPolishContent(polishedPreview); setShowPolishModal(true) } }, [polishedPreview])

  useEffect(() => {
    if (!ctxMenu.visible) return
    const handler = () => setCtxMenu(prev => ({ ...prev, visible: false }))
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [ctxMenu.visible])

  useEffect(() => () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current) }, [])

  if (editMode) {
    return (
      <div className="journal-doc-shell journal-doc-shell--today">
        {ctxMenu.visible && images.length < MAX_JOURNAL_IMAGES && <EditorContextMenu x={ctxMenu.x} y={ctxMenu.y} onClose={() => setCtxMenu(prev => ({ ...prev, visible: false }))} onInsertImage={insertImage} />}
        {showPolishModal && editor && (
          <PolishModal original={htmlToMarkdown(editor.getHTML())} polished={polishContent}
            onAccept={() => { setShowPolishModal(false); onAcceptPolish() }}
            onReject={() => { setShowPolishModal(false); onRejectPolish() }}
            onContinuePolish={() => onPolish(htmlToMarkdown(editor.getHTML()))} polishing={polishing} />
        )}
        <div className="journal-today-stack journal-today-stack--edit">
          <ImageGallery images={images} onAddImage={insertImage} onRemove={removeImage} />
          <EditorContent editor={editor} className="journal-editor" />
        </div>
      </div>
    )
  }

  // Preview mode
  return (
    <div className="journal-doc-shell journal-doc-shell--today">
      {entry ? (
        <article className="journal-doc-main journal-doc-main--today">
          <div className="journal-doc-main-scroll">
            <div className="journal-today-stack">
              <ImageGallery images={images} isReadOnly onRemove={() => {}} />
              <div className="journal-doc-body journal-doc-body--today markdown-content" dangerouslySetInnerHTML={{ __html: renderJournalMarkdown(textContent) }} />
            </div>
            <div className="journal-doc-meta-row"><span>今日复盘上次编辑于 {formatDateTime(entry.updated_at)}</span></div>
          </div>
        </article>
      ) : (
        <div className="journal-empty journal-empty--main">
          <p>今天还没有写复盘。</p>
          <p>点击右上角编辑今日复盘，记录今天完成了什么、进度如何、查漏补缺和下一步。</p>
        </div>
      )}
    </div>
  )
}
