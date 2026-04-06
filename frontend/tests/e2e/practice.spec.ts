// ── E2E Tests: Practice Page ───────────────────────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:3020'

test.describe('Practice Page', () => {
  test.beforeEach(async ({ page }) => {
    // Setup mock auth
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }))
    })
  })

  test('loads practice page successfully', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await expect(page).toHaveURL('/practice')
    await expect(page.getByText(/练习|practice/i)).toBeVisible()
  })

  test('shows practice control bar', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await expect(page.locator('.practice-control-bar, .control-bar')).toBeVisible()
  })

  test('shows mode selector', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    const modeSelector = page.getByText(/模式|mode/i)
    await expect(modeSelector).toBeVisible()
  })

  test('has pause/resume controls', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await expect(page.getByRole('button', { name: /暂停|pause/i })).toBeVisible()
  })

  test('shows progress indicator', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    const progress = page.locator('.progress, .progress-bar, [role="progressbar"]')
    await expect(progress.first()).toBeVisible()
  })

  test('can open word list panel', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    const wordListButton = page.getByRole('button', { name: /单词|word|list/i })
    await wordListButton.click()
    await expect(page.locator('.word-list-panel, .word-panel')).toBeVisible()
  })

  test('can close word list panel', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("单词")')
    await page.click('button[aria-label="close"], .close-button')
    const wordPanel = page.locator('.word-list-panel, .word-panel')
    await expect(wordPanel).not.toBeVisible()
  })

  test('can open practice settings', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    const settingsButton = page.getByRole('button', { name: /设置|settings/i })
    await settingsButton.click()
    await expect(page.locator('.settings-panel, .practice-settings')).toBeVisible()
  })

  test('has play audio button', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    const playButton = page.getByRole('button', { name: /播放|play|audio/i })
    await expect(playButton).toBeVisible()
  })

  test('has skip button', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    const skipButton = page.getByRole('button', { name: /跳过|skip/i })
    await expect(skipButton).toBeVisible()
  })

  test('has go back button', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    const backButton = page.getByRole('button', { name: /返回|back/i })
    await expect(backButton).toBeVisible()
  })

  test('displays current word', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    const wordDisplay = page.locator('.word-display, .current-word, h1, h2')
    await expect(wordDisplay.first()).toBeVisible()
  })

  test('displays correct/wrong counters', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    const counters = page.locator('.counter, .score, .correct-count, .wrong-count')
    await expect(counters.first()).toBeVisible()
  })
})
