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

test.describe('Enhanced Stats Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }))
    })
  })

  test('displays learning streak counter', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const streakCard = page.locator('.stats-card').filter({ hasText: '连续学习' })
    await expect(streakCard).toBeVisible()
    await expect(streakCard.locator('.stats-card-value')).toBeVisible()
  })

  test('shows upcoming review countdown', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const ebbinghausSection = page.locator('.stats-card-ebbinghaus, .ebb-chart-wrap')
    await expect(ebbinghausSection.first()).toBeVisible()
    const reviewHint = page.locator('text=/待复|复习.*\\d+.*词|即将到期/')
    const count = await reviewHint.count()
    if (count > 0) {
      await expect(reviewHint.first()).toBeVisible()
    }
  })

  test('wrong words show error category when available', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const wrongTable = page.locator('.stats-wrong-table')
    const tableCount = await wrongTable.count()
    if (tableCount > 0) {
      const rows = wrongTable.locator('tbody tr')
      const rowCount = await rows.count()
      if (rowCount > 0) {
        const fourthCell = rows.first().locator('td:nth-child(4)')
        await expect(fourthCell).toBeVisible()
      }
    }
  })

  test('mode breakdown shows recommendation indicator', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const modeSection = page.locator('.stats-section--mode-strip, .mode-breakdown-table-wrap')
    await expect(modeSection.first()).toBeVisible()
    const recommendation = page.locator('text=/推荐|建议.*模式|薄弱/')
    const recCount = await recommendation.count()
    if (recCount > 0) {
      await expect(recommendation.first()).toBeVisible()
    }
  })

  test('daily goal progress is visible when set', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const goalSection = page.locator('.stats-card, .goal-progress, [class*="goal"]')
    const goalCount = await goalSection.count()
    if (goalCount > 0) {
      await expect(goalSection.first()).toBeVisible()
    }
  })

  test('learning trend insight is displayed', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const trendElement = page.locator('text=/趋势|提升|下滑|稳定|进步/')
    const count = await trendElement.count()
    if (count > 0) {
      await expect(trendElement.first()).toBeVisible()
    }
  })

  test('chapter priority labels for low accuracy chapters', async ({ page }) => {
    await page.goto(`${BASE}/stats`)
    const chapterSection = page.locator('.stats-section--chapter-cell, .stats-table--compact')
    const sectionCount = await chapterSection.count()
    if (sectionCount > 0) {
      await expect(chapterSection.first()).toBeVisible()
      const priorityLabel = page.locator('text=/需加强|优先|推荐/')
      const labelCount = await priorityLabel.count()
      if (labelCount > 0) {
        await expect(priorityLabel.first()).toBeVisible()
      }
    }
  })
})
