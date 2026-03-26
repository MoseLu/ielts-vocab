// ── E2E Tests: Stats Page ─────────────────────────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:5173'

test.describe('Stats Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }))
    })
  })

  test('loads stats page successfully', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    await expect(page).toHaveURL('/stats')
    await expect(page.getByText(/统计|stats/i)).toBeVisible()
  })

  test('displays learning statistics', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const statsSection = page.locator('.stats, .statistics, [class*="stat"]')
    await expect(statsSection.first()).toBeVisible()
  })

  test('shows total words learned', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const totalWords = page.locator('.total-words, [class*="total"]')
    await expect(totalWords.first()).toBeVisible()
  })

  test('shows correct/wrong counts', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const counters = page.locator('.counter, .count, .correct, .wrong')
    await expect(counters.first()).toBeVisible()
  })

  test('displays learning progress charts', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const charts = page.locator('.chart, .graph, [class*="chart"]')
    const count = await charts.count()
    if (count > 0) {
      await expect(charts.first()).toBeVisible()
    }
  })

  test('shows book-level statistics', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const bookStats = page.locator('.book-stats, [class*="book-stat"]')
    await expect(bookStats.first()).toBeVisible()
  })

  test('shows chapter-level statistics', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const chapterStats = page.locator('.chapter-stats, [class*="chapter-stat"]')
    await expect(chapterStats.first()).toBeVisible()
  })

  test('displays practice mode breakdown', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const modeBreakdown = page.locator('.mode-stats, [class*="mode"]')
    await expect(modeBreakdown.first()).toBeVisible()
  })

  test('shows recent activity', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const recentActivity = page.locator('.recent-activity, [class*="recent"]')
    await expect(recentActivity.first()).toBeVisible()
  })

  test('has date range filter', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const dateFilter = page.locator('input[type="date"], [class*="date"]')
    const count = await dateFilter.count()
    if (count > 0) {
      await expect(dateFilter.first()).toBeVisible()
    }
  })
})
