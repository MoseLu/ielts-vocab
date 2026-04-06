import React, { useRef, useState } from 'react'
import { apiFetch } from '../../../lib'
import { MicroLoading } from '../../ui'

interface AvatarUploadProps {
  user: AuthUser | null
  onClose: () => void
  onSave: (user: AuthUser) => void
}

interface AuthUser {
  id?: number | string
  username?: string
  email?: string
  avatar_url?: string | null
}

interface AvatarApiResponse {
  user?: AuthUser
  error?: string
}

function AvatarUpload({ user, onClose, onSave }: AvatarUploadProps) {
  const [preview, setPreview] = useState<string | null>(user?.avatar_url || null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('请选择图片文件')
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      setError('图片大小不能超过 2MB')
      return
    }
    setError('')
    const reader = new FileReader()
    reader.onload = (ev) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const size = 200
        canvas.width = size
        canvas.height = size
        const ctx = canvas.getContext('2d') as CanvasRenderingContext2D
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-inverse').trim()
        ctx.fillRect(0, 0, size, size)
        const min = Math.min(img.width, img.height)
        const sx = (img.width - min) / 2
        const sy = (img.height - min) / 2
        ctx.drawImage(img, sx, sy, min, min, 0, 0, size, size)
        setPreview(canvas.toDataURL('image/jpeg', 0.85))
      }
      img.src = ev.target?.result as string
    }
    reader.readAsDataURL(file)
  }

  const handleSave = async () => {
    if (!preview) return
    setSaving(true)
    setError('')
    try {
      const data = await apiFetch<AvatarApiResponse>('/api/auth/avatar', {
        method: 'PUT',
        body: JSON.stringify({ avatar_url: preview }),
      })
      if (data.error) {
        setError(data.error || '保存失败')
        return
      }
      localStorage.setItem('auth_user', JSON.stringify(data.user))
      onSave(data.user as AuthUser)
      onClose()
    } catch {
      setError('网络错误，请重试')
    } finally {
      setSaving(false)
    }
  }

  const handleRemove = () => {
    setPreview(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <div className="avatar-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="avatar-modal">
        <div className="avatar-modal-header">
          <h3>更换头像</h3>
          <button className="avatar-modal-close" onClick={onClose} aria-label="关闭头像弹窗">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="avatar-modal-body">
          <div className="avatar-preview-area">
            {preview ? (
              <img src={preview} alt="头像预览" className="avatar-preview-img" />
            ) : (
              <img src="/default-avatar.jpg" alt="默认头像" className="avatar-preview-img" />
            )}
          </div>

          <div className="avatar-actions">
            <button
              className="avatar-upload-btn"
              onClick={() => fileRef.current?.click()}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              选择图片
            </button>
            {preview && preview !== (user?.avatar_url || null) && (
              <button className="avatar-remove-btn" onClick={handleRemove}>
                移除
              </button>
            )}
          </div>

          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="avatar-file-input"
            onChange={handleFileChange}
          />

          <p className="avatar-hint">支持 JPG、PNG 格式，大小不超过 2MB</p>

          {error && <div className="avatar-error">{error}</div>}
        </div>

        <div className="avatar-modal-footer">
          <button className="avatar-cancel-btn" onClick={onClose} disabled={saving}>
            取消
          </button>
          <button
            className="avatar-save-btn"
            onClick={handleSave}
            disabled={saving || !preview}
          >
            {saving ? <MicroLoading text="保存中..." /> : '保存头像'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default AvatarUpload
