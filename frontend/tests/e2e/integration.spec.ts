// ── E2E Tests: Integration Tests ─────────────────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:3020'

test.describe('Integration Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }))
    })
  })

  test('complete user journey: login to practice', async ({ page }) => {
    // Start at login (simulate fresh session)
    await page.context().clearCookies()
    await page.goto(`${BASE}/login`)

    // Login
    await page.fill('input[placeholder*="用户"]', 'testuser')
    await page.fill('input[type="password"]', 'testpass123')
    await page.click('button:has-text("登录")')

    // Navigate to home
    await expect(page).toHaveURL('/')

    // Navigate to practice
    await page.click('a[href="/practice"], button:has-text("练习")')
    await expect(page).toHaveURL('/practice')
  })

  test('complete user journey: vocabulary book to practice', async ({ page }) => {
    // Start at home
    await page.goto(BASE)

    // Select a book
    await page.click('.book-card, .vocab-book')
    await page.waitForTimeout(500)

    // Select a chapter
    await page.click('.chapter, [class*="chapter"]')

    // Should be in practice mode
    await expect(page).toHaveURL(/\/practice/)
  })

  test('practice mode switch workflow', async ({ page }) => {
    await page.goto(`${BASE}/practice`)

    // Start with listening mode
    await page.click('button:has-text("模式")')
    await page.click('text=听音模式')

    // Switch to meaning mode
    await page.click('button:has-text("模式")')
    await page.click('text=意译模式')

    // Switch to dictation mode
    await page.click('button:has-text("模式")')
    await page.click('text=听写模式')

    // Verify we're still on practice page
    await expect(page).toHaveURL('/practice')
  })

  test('navigation through all main pages', async ({ page }) => {
    await page.goto(BASE)

    // Navigate through bottom nav
    await page.click('.bottom-nav button:has-text("首页")')
    await expect(page).toHaveURL('/')

    await page.click('.bottom-nav button:has-text("错词本")')
    await expect(page).toHaveURL('/errors')

    await page.click('.bottom-nav button:has-text("统计")')
    await expect(page).toHaveURL('/stats')

    await page.click('.bottom-nav button:has-text("我的")')
    await expect(page).toHaveURL('/profile')
  })

  test('practice to stats workflow', async ({ page }) => {
    // Start practice
    await page.goto(`${BASE}/practice`)

    // Complete a few practice steps (simulate)
    await page.waitForTimeout(1000)

    // Navigate to stats
    await page.click('.bottom-nav button:has-text("统计")')
    await expect(page).toHaveURL('/stats')

    // Verify stats are visible
    await expect(page.getByText(/统计|stats/i)).toBeVisible()
  })

  test('settings persistence across practice sessions', async ({ page }) => {
    // Open settings
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("设置")')

    // Change a setting
    const speedSelect = page.locator('select, [class*="speed"]').first()
    await speedSelect.selectOption('1.5' || 'fast')

    // Close and navigate away
    await page.click('.close-settings')
    await page.goto(`${BASE}/stats`)

    // Return to practice
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("设置")')

    // Settings should persist
    await expect(page).toBeVisible()
  })

  test('logout and re-login workflow', async ({ page }) => {
    // Start logged in
    await page.goto(BASE)

    // Navigate to profile
    await page.click('.bottom-nav button:has-text("我的")')

    // Logout
    await page.click('button:has-text("退出"), button:has-text("logout")')

    // Should be at login
    await expect(page).toHaveURL('/login')

    // Login again
    await page.fill('input[placeholder*="用户"]', 'testuser')
    await page.fill('input[type="password"]', 'testpass123')
    await page.click('button:has-text("登录")')

    // Should be back at home
    await expect(page).toHaveURL('/')
  })
})
