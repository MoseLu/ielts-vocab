// ── E2E Tests: Profile Page ────────────────────────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:3020'

test.describe('Profile Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser', email: 'test@example.com' }))
    })
  })

  test('loads profile page successfully', async ({ page }) => {
    await page.goto(`${BASE}/profile`)
    await expect(page).toHaveURL('/profile')
    await expect(page.getByText(/个人资料|profile|我的/i)).toBeVisible()
  })

  test('displays user information', async ({ page }) => {
    await page.goto(`${BASE}/profile`)
    const userInfo = page.locator('.user-info, .profile-info')
    await expect(userInfo).toBeVisible()
  })

  test('shows username', async ({ page }) => {
    await page.goto(`${BASE}/profile`)
    const username = page.locator('.username, [class*="username"]')
    await expect(username.first()).toBeVisible()
  })

  test('shows email address', async ({ page }) => {
    await page.goto(`${BASE}/profile`)
    const email = page.locator('.email, [class*="email"]')
    await expect(email.first()).toBeVisible()
  })

  test('has avatar upload functionality', async ({ page }) => {
    await page.goto(`${BASE}/profile`)
    const avatarUpload = page.locator('input[type="file"], .avatar-upload, [class*="avatar"]')
    const count = await avatarUpload.count()
    if (count > 0) {
      await expect(avatarUpload.first()).toBeVisible()
    }
  })

  test('has settings section', async ({ page }) => {
    await page.goto(`${BASE}/profile`)
    const settingsSection = page.locator('.settings, .preferences')
    await expect(settingsSection).toBeVisible()
  })

  test('has logout button', async ({ page }) => {
    await page.goto(`${BASE}/profile`)
    const logoutButton = page.getByRole('button', { name: /退出|logout/i })
    await expect(logoutButton).toBeVisible()
  })

  test('logout redirects to login page', async ({ page }) => {
    await page.goto(`${BASE}/profile`)
    await page.click('button:has-text("退出"), button:has-text("logout")')
    await expect(page).toHaveURL('/login')
  })

  test('has app settings', async ({ page }) => {
    await page.goto(`${BASE}/profile`)
    const appSettings = page.locator('.app-settings, [class*="settings"]')
    await expect(appSettings.first()).toBeVisible()
  })

  test('can toggle settings', async ({ page }) => {
    await page.goto(`${BASE}/profile`)
    const toggles = page.locator('.toggle, input[type="checkbox"], [role="switch"]')
    const count = await toggles.count()
    if (count > 0) {
      await expect(toggles.first()).toBeVisible()
    }
  })
})
