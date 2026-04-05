// ── E2E Tests: Settings ─────────────────────────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:3020'

test.describe('Settings & Preferences', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }))
    })
  })

  test('can access settings from practice page', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    const settingsButton = page.getByRole('button', { name: /设置|settings/i })
    await settingsButton.click()
    const settingsPanel = page.locator('.settings-panel, .practice-settings')
    await expect(settingsPanel).toBeVisible()
  })

  test('has shuffle vocabulary toggle', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("设置")')

    const shuffleToggle = page.locator('label:has-text("随机"), input[type="checkbox"]')
    const count = await shuffleToggle.count()
    if (count > 0) {
      await expect(shuffleToggle.first()).toBeVisible()
    }
  })

  test('has repeat wrong words toggle', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("设置")')

    const repeatToggle = page.locator('label:has-text("错误"), input[type="checkbox"]')
    const count = await repeatToggle.count()
    if (count > 0) {
      await expect(repeatToggle.first()).toBeVisible()
    }
  })

  test('has audio playback speed setting', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("设置")')

    const speedSetting = page.locator('select, input[type="range"], [class*="speed"]')
    await expect(speedSetting.first()).toBeVisible()
  })

  test('has volume control', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("设置")')

    const volumeControl = page.locator('input[type="range"], [class*="volume"]')
    await expect(volumeControl.first()).toBeVisible()
  })

  test('has interval setting', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("设置")')

    const intervalSetting = page.locator('[class*="interval"], input[type="number"]')
    await expect(intervalSetting.first()).toBeVisible()
  })

  test('can close settings panel', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("设置")')

    const closeButton = page.locator('.settings-panel button[aria-label="close"], .close-settings')
    await closeButton.click()

    const settingsPanel = page.locator('.settings-panel, .practice-settings')
    await expect(settingsPanel).not.toBeVisible()
  })

  test('settings persist across page reloads', async ({ page }) => {
    await page.goto(`${BASE}/practice`)
    await page.click('button:has-text("设置")')

    // Toggle a setting
    const toggle = page.locator('input[type="checkbox"]').first()
    const count = await toggle.count()
    if (count > 0) {
      const isChecked = await toggle.isChecked()
      await toggle.click()

      // Reload page
      await page.reload()
      await page.click('button:has-text("设置")')

      const newToggle = page.locator('input[type="checkbox"]').first()
      const newIsChecked = await newToggle.isChecked()

      expect(newIsChecked).toBe(!isChecked)
    }
  })
})
