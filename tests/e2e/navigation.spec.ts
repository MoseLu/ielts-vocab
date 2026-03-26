// ── E2E Tests: Navigation & Routes ────────────────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:5173'

test.describe('Navigation & Routes', () => {
  let context: any

  test.beforeAll(async ({ browser }) => {
    // Setup authenticated context
    context = await browser.newContext()
    const page = await context.newPage()

    // Login
    await page.goto(`${BASE}/login`)
    await page.fill('input[placeholder*="用户"]', 'testuser')
    await page.fill('input[type="password"]', 'testpass123')
    await page.click('button:has-text("登录")')

    // Wait for navigation and save storage
    await page.waitForURL('/')
    await page.context().storageState({ path: 'tests/e2e/.auth/auth.json' })
    await page.close()
  })

  test.afterAll(async () => {
    await context.close()
  })

  test.beforeEach(async ({ page }) => {
    // Load authenticated state
    await page.context().addInitScript(() => {
      const auth = localStorage.getItem('token')
      if (!auth) {
        localStorage.setItem('token', 'mock-token-for-testing')
      }
    })
  })

  test('loads home page successfully', async ({ page }) => {
    await page.goto(BASE)
    await expect(page).toHaveURL('/')
    await expect(page.locator('h1, h2, .header')).toBeVisible()
  })

  test('navigates to learning plan page', async ({ page }) => {
    await page.goto(BASE)
    await page.click('a[href="/plan"], button:has-text("计划")')
    await expect(page).toHaveURL('/plan')
    await expect(page.getByText(/学习计划|plan/i)).toBeVisible()
  })

  test('navigates to practice page', async ({ page }) => {
    await page.goto(BASE)
    await page.click('a[href="/practice"], button:has-text("练习")')
    await expect(page).toHaveURL('/practice')
    await expect(page.getByText(/练习|practice/i)).toBeVisible()
  })

  test('navigates to errors page via bottom nav', async ({ page }) => {
    await page.goto(BASE)
    await page.click('.bottom-nav button:has-text("错词本")')
    await expect(page).toHaveURL('/errors')
    await expect(page.getByText(/错词本|errors/i)).toBeVisible()
  })

  test('navigates to stats page via bottom nav', async ({ page }) => {
    await page.goto(BASE)
    await page.click('.bottom-nav button:has-text("统计")')
    await expect(page).toHaveURL('/stats')
    await expect(page.getByText(/统计|stats/i)).toBeVisible()
  })

  test('navigates to profile page via bottom nav', async ({ page }) => {
    await page.goto(BASE)
    await page.click('.bottom-nav button:has-text("我的")')
    await expect(page).toHaveURL('/profile')
    await expect(page.getByText(/个人资料|profile/i)).toBeVisible()
  })

  test('navigates to vocab-test page', async ({ page }) => {
    await page.goto(BASE)
    await page.click('a[href="/vocab-test"], button:has-text("词汇测试")')
    await expect(page).toHaveURL('/vocab-test')
    await expect(page.getByText(/词汇测试|vocab test/i)).toBeVisible()
  })

  test('navigates to learning journal page', async ({ page }) => {
    await page.goto(BASE)
    await page.click('a[href="/journal"], button:has-text("学习日记")')
    await expect(page).toHaveURL('/journal')
    await expect(page.getByText(/学习日记|learning journal/i)).toBeVisible()
  })

  test('admin route is accessible for admin users', async ({ page }) => {
    // Mock admin role
    await page.addInitScript(() => {
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'admin', isAdmin: true }))
    })

    await page.goto(`${BASE}/admin`)
    await expect(page).toHaveURL('/admin')
    await expect(page.getByText(/管理|admin/i)).toBeVisible()
  })

  test('admin route redirects non-admin users', async ({ page }) => {
    // Mock non-admin role
    await page.addInitScript(() => {
      localStorage.setItem('user', JSON.stringify({ id: 2, username: 'user', isAdmin: false }))
    })

    await page.goto(`${BASE}/admin`)
    await expect(page).toHaveURL('/')
  })

  test('unauthenticated users are redirected to login', async ({ page }) => {
    // Clear auth
    await page.context().clearCookies()

    await page.goto(BASE)
    await expect(page).toHaveURL('/login')
  })

  test('unknown routes redirect authenticated users to home', async ({ page }) => {
    await page.goto(`${BASE}/unknown-route`)
    await expect(page).toHaveURL('/')
  })

  test('bottom navigation shows correct active state', async ({ page }) => {
    await page.goto(`${BASE}/errors`)
    await expect(page.locator('.bottom-nav button.active').first()).toHaveText(/错词本/)

    await page.click('.bottom-nav button:has-text("统计")')
    await expect(page.locator('.bottom-nav button.active').first()).toHaveText(/统计/)
  })

  test('header navigation works correctly', async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator('.header, header')).toBeVisible()

    // Test header navigation buttons
    const headerLinks = page.locator('.header a, .header button')
    const count = await headerLinks.count()
    expect(count).toBeGreaterThan(0)
  })
})
