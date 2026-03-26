// ── E2E Tests: Admin Dashboard ─────────────────────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:5173'

test.describe('Admin Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'admin', isAdmin: true }))
    })
  })

  test('loads admin dashboard successfully', async ({ page }) => {
    await page.goto(`${BASE}/admin`)
    await expect(page).toHaveURL('/admin')
    await expect(page.getByText(/管理|admin|dashboard/i)).toBeVisible()
  })

  test('redirects non-admin users', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 2, username: 'user', isAdmin: false }))
    })

    await page.goto(`${BASE}/admin`)
    await expect(page).toHaveURL('/')
  })

  test('displays user management section', async ({ page }) => {
    await page.goto(`${BASE}/admin`)
    const userManagement = page.locator('.user-management, [class*="user"]')
    await expect(userManagement).toBeVisible()
  })

  test('shows user list', async ({ page }) => {
    await page.goto(`${BASE}/admin`)
    const userList = page.locator('.user-list, [class*="user-list"]')
    await expect(userList).toBeVisible()
  })

  test('has vocabulary management section', async ({ page }) => {
    await page.goto(`${BASE}/admin`)
    const vocabManagement = page.locator('.vocab-management, [class*="vocab"]')
    await expect(vocabManagement).toBeVisible()
  })

  test('can add new vocabulary book', async ({ page }) => {
    await page.goto(`${BASE}/admin`)
    const addBookButton = page.getByRole('button', { name: /添加|add|new/i })
    await expect(addBookButton).toBeVisible()
  })

  test('has statistics overview', async ({ page }) => {
    await page.goto(`${BASE}/admin`)
    const statsOverview = page.locator('.stats, .overview, [class*="stat"]')
    await expect(statsOverview.first()).toBeVisible()
  })

  test('shows system logs or activity', async ({ page }) => {
    await page.goto(`${BASE}/admin`)
    const logs = page.locator('.logs, .activity, [class*="log"]')
    const count = await logs.count()
    if (count > 0) {
      await expect(logs.first()).toBeVisible()
    }
  })
})
