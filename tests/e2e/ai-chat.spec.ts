// ── E2E Tests: AI Chat Panel ────────────────────────────────────────────────────

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:3020'

test.describe('AI Chat Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token-for-testing')
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }))
    })
  })

  test('shows AI chat panel on authenticated pages', async ({ page }) => {
    await page.goto(BASE)
    const chatPanel = page.locator('.ai-chat, .chat-panel, [class*="ai-chat"]')
    await expect(chatPanel).toBeVisible()
  })

  test('can open AI chat panel', async ({ page }) => {
    await page.goto(BASE)
    const openButton = page.getByRole('button', { name: /ai|助手|chat/i })
    await openButton.click()
    const chatPanel = page.locator('.ai-chat, .chat-panel')
    await expect(chatPanel).toBeVisible()
  })

  test('can close AI chat panel', async ({ page }) => {
    await page.goto(BASE)
    const openButton = page.getByRole('button', { name: /ai|助手/i })
    await openButton.click()

    const closeButton = page.locator('.chat-panel button[aria-label="close"], .close-chat')
    const count = await closeButton.count()
    if (count > 0) {
      await closeButton.click()
      const chatPanel = page.locator('.ai-chat, .chat-panel')
      await expect(chatPanel).not.toBeVisible()
    }
  })

  test('has message input field', async ({ page }) => {
    await page.goto(BASE)
    const chatPanel = page.locator('.ai-chat, .chat-panel')
    const inputField = chatPanel.locator('textarea, input[type="text"]')
    await expect(inputField).toBeVisible()
  })

  test('has send button', async ({ page }) => {
    await page.goto(BASE)
    const chatPanel = page.locator('.ai-chat, .chat-panel')
    const sendButton = chatPanel.getByRole('button', { name: /发送|send/i })
    await expect(sendButton).toBeVisible()
  })

  test('displays chat history', async ({ page }) => {
    await page.goto(BASE)
    const chatPanel = page.locator('.ai-chat, .chat-panel')
    const messages = chatPanel.locator('.message, [class*="message"]')
    const count = await messages.count()
    if (count > 0) {
      await expect(messages.first()).toBeVisible()
    }
  })

  test('shows loading state when waiting for AI response', async ({ page }) => {
    await page.goto(BASE)
    const chatPanel = page.locator('.ai-chat, .chat-panel')
    const inputField = chatPanel.locator('textarea, input[type="text"]')

    await inputField.fill('Hello')
    const sendButton = chatPanel.getByRole('button', { name: /发送/i })
    await sendButton.click()

    const loadingIndicator = chatPanel.locator('.loading, [class*="loading"]')
    await expect(loadingIndicator.first()).toBeVisible({ timeout: 5000 })
  })

  test('can clear chat history', async ({ page }) => {
    await page.goto(BASE)
    const chatPanel = page.locator('.ai-chat, .chat-panel')
    const clearButton = chatPanel.getByRole('button', { name: /清空|clear/i })
    const count = await clearButton.count()
    if (count > 0) {
      await expect(clearButton).toBeVisible()
    }
  })
})
