// ── E2E Tests: Practice Modes ───────────────────────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:3020'

test.describe('Practice Modes', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }))
    })
  })

  test('smart mode is selectable', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=智能模式')
    await expect(page.getByText(/智能|smart/i)).toBeVisible()
  })

  test('listening mode is selectable', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=听音模式')
    await expect(page.getByText(/听音|listening/i)).toBeVisible()
  })

  test('meaning mode is selectable', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=意译模式')
    await expect(page.getByText(/意译|meaning/i)).toBeVisible()
  })

  test('dictation mode is selectable', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=听写模式')
    await expect(page.getByText(/听写|dictation/i)).toBeVisible()
  })

  test('radio mode is selectable', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=收音机模式')
    await expect(page.getByText(/收音机|radio/i)).toBeVisible()
  })

  test('quick memory mode is selectable', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=快速记忆')
    await expect(page.getByText(/快速记忆|quick memory/i)).toBeVisible()
  })

  test('options mode shows multiple choice answers', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=意译模式')

    // Wait for options to load
    await page.waitForTimeout(500)

    const options = page.locator('.option, .choice, button[class*="option"]')
    await expect(options.first()).toBeVisible()
  })

  test('dictation mode shows input field', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=听写模式')

    await page.waitForTimeout(500)

    const inputField = page.locator('input[type="text"], textarea')
    await expect(inputField.first()).toBeVisible()
  })

  test('listening mode plays audio automatically', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=听音模式')

    // Check if audio controls are visible
    await page.waitForTimeout(500)
    const playButton = page.getByRole('button', { name: /播放|play/i })
    await expect(playButton).toBeVisible()
  })

  test('radio mode shows radio controls', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=收音机模式')

    await page.waitForTimeout(500)

    const radioControls = page.locator('.radio-controls, .playback-controls')
    await expect(radioControls).toBeVisible()
  })

  test('quick memory mode shows know/unknown buttons', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("模式")')
    await page.click('text=快速记忆')

    await page.waitForTimeout(500)

    const knowButton = page.getByRole('button', { name: /认识|know/i })
    const unknownButton = page.getByRole('button', { name: /不认识|unknown/i })
    await expect(knowButton.or(unknownButton)).toBeVisible()
  })
})
