import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import AvatarUpload from './AvatarUpload'

vi.mock('../../../lib', () => ({
  apiFetch: vi.fn(),
}))

describe('AvatarUpload', () => {
  it('renders in a body portal and shows the shared default avatar when no custom avatar exists', () => {
    const { container } = render(
      <AvatarUpload
        user={{ id: 1, username: 'admin', avatar_url: null }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />,
    )

    expect(container.firstChild).toBeNull()
    expect(document.body.querySelector('.avatar-modal-overlay')).not.toBeNull()

    const previewImage = screen.getByAltText('默认头像') as HTMLImageElement
    expect(previewImage.getAttribute('src')).toBe('/default-avatar.jpg')
    expect(screen.getByRole('heading', { name: '更换头像' })).toBeInTheDocument()
  })
})
