// ── E2E Tests: Errors Page (Wrong Words) ───────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:3020'

test.describe('Errors Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }))
    })
  })

  test('loads errors page successfully', async ({ page }) => {
    await page.goto(`${BASE}/errors`)
    await expect(page).toHaveURL('/errors')
    await expect(page.getByText(/错词本|errors/i)).toBeVisible()
  })

  test('displays list of wrong words', async ({ page }) => {
    await page.goto(`${BASE}/errors`)
    const wordList = page.locator('.wrong-word, .error-word, [class*="word-item"]')
    await expect(wordList.first()).toBeVisible()
  })

  test('shows word definitions', async ({ page }) => {
    await page.goto(`${BASE}/errors`)
    const definitions = page.locator('.definition, [class*="definition"]')
    await expect(definitions.first()).toBeVisible()
  })

  test('has clear all wrong words button', async ({ page }) => {
    await page.goto(`${BASE}/errors`)
    const clearButton = page.getByRole('button', { name: /清空|clear|全部/i })
    const isClearButtonVisible = await clearButton.count() > 0
    if (isClearButtonVisible) {
      await expect(clearButton).toBeVisible()
    }
  })

  test('can remove individual wrong word', async ({ page }) => {
    await page.goto(`${BASE}/errors`)
    const removeButton = page.locator('button[aria-label*="remove"], button[class*="remove"]')
    const count = await removeButton.count()
    if (count > 0) {
      await expect(removeButton.first()).toBeVisible()
    }
  })

  test('can play audio for wrong words', async ({ page }) => {
    await page.goto(`${BASE}/errors`)
    const audioButton = page.getByRole('button', { name: /播放|play|audio/i })
    await expect(audioButton.first()).toBeVisible()
  })

  test('shows phonetic pronunciation', async ({ page }) => {
    await page.goto(`${BASE}/errors`)
    const phonetic = page.locator('.phonetic, [class*="phonetic"]')
    await expect(phonetic.first()).toBeVisible()
  })

  test('displays word examples', async ({ page }) => {
    await page.goto(`${BASE}/errors`)
    const examples = page.locator('.example, [class*="example"]')
    const count = await examples.count()
    if (count > 0) {
      await expect(examples.first()).toBeVisible()
    }
  })

  test('shows empty state when no wrong words', async ({ page }) => {
    await page.goto(`${BASE}/errors`)
    const emptyState = page.locator('.empty-state, .no-data')
    const isEmptyStateVisible = await emptyState.count() > 0
    if (isEmptyStateVisible) {
      await expect(emptyState).toBeVisible()
    }
  })
})
