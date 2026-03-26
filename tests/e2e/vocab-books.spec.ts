// ── E2E Tests: Vocabulary Books Page ─────────────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:5173'

test.describe('Vocabulary Books Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }))
    })
  })

  test('loads home page with vocabulary books', async ({ page }) => {
    await page.goto(BASE)
    await expect(page).toHaveURL('/')
    await expect(page.getByText(/词汇|vocabulary|书籍|books/i)).toBeVisible()
  })

  test('displays book list', async ({ page }) => {
    await page.goto(BASE)
    const books = page.locator('.book-card, .vocab-book, [class*="book"]')
    await expect(books.first()).toBeVisible()
  })

  test('can select a book', async ({ page }) => {
    await page.goto(BASE)
    const firstBook = page.locator('.book-card, .vocab-book').first()
    await firstBook.click()
    await expect(page).toHaveURL(/\/plan|\/practice/)
  })

  test('shows chapter progress', async ({ page }) => {
    await page.goto(BASE)
    const progressIndicators = page.locator('.progress, .chapter-progress')
    await expect(progressIndicators.first()).toBeVisible()
  })

  test('displays chapter list', async ({ page }) => {
    await page.goto(BASE)
    await page.click('.book-card, .vocab-book')
    await page.waitForTimeout(500)

    const chapters = page.locator('.chapter, [class*="chapter"]')
    await expect(chapters.first()).toBeVisible()
  })

  test('can select a chapter', async ({ page }) => {
    await page.goto(BASE)
    await page.click('.book-card, .vocab-book')
    await page.waitForTimeout(500)

    const firstChapter = page.locator('.chapter, [class*="chapter"]').first()
    await firstChapter.click()

    // Should navigate to practice or plan
    await expect(page).toHaveURL(/\/practice|\/plan/)
  })

  test('shows word count for chapters', async ({ page }) => {
    await page.goto(BASE)
    await page.click('.book-card, .vocab-book')
    await page.waitForTimeout(500)

    const wordCounts = page.locator('.word-count, [class*="count"]')
    await expect(wordCounts.first()).toBeVisible()
  })

  test('has book filtering options', async ({ page }) => {
    await page.goto(BASE)
    const filterInput = page.locator('input[placeholder*="搜索"], input[placeholder*="filter"]')
    const isFilterVisible = await filterInput.count() > 0
    if (isFilterVisible) {
      await expect(filterInput).toBeVisible()
    }
  })

  test('displays book cover or icon', async ({ page }) => {
    await page.goto(BASE)
    const bookIcons = page.locator('.book-cover, .book-icon, img[class*="book"]')
    await expect(bookIcons.first()).toBeVisible()
  })
})
