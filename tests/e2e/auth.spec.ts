// ── E2E Tests: Auth Flow ───────────────────────────────────────────────────────
//
// Prerequisites (run once):
//   cd backend && pip install -r requirements.txt
//   pnpm exec playwright install chromium
//
// Start servers (two terminals):
//   Terminal 1: pnpm run dev          # frontend at http://localhost:5173
//   Terminal 2: cd backend && python app.py  # backend at http://localhost:5000
//
// Run tests:
//   pnpm exec playwright test

import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://localhost:5173'

// ── /login ─────────────────────────────────────────────────────────────────────

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE}/login`)
  })

  test('renders login form', async ({ page }) => {
    await expect(page.locator('input[type="text"], input[name="identifier"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.getByRole('button', { name: /登|登录|login/i })).toBeVisible()
  })

  test('has a register tab link', async ({ page }) => {
    // AuthPage switches tabs on the same page
    const registerLink = page.getByText(/注册|register/i)
    await expect(registerLink).toBeVisible()
  })

  test('switches to register tab', async ({ page }) => {
    await page.getByText(/注册|register/i).click()
    // After switching, a username field should appear
    const usernameField = page.locator('input[name="username"], input[placeholder*="用户"]')
    await expect(usernameField).toBeVisible()
  })
})

// ── /register ─────────────────────────────────────────────────────────────────

test.describe('Register Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE}/login`)
    // Switch to register tab
    await page.getByText(/注册|register/i).click()
    await page.waitForTimeout(300)
  })

  test('shows validation errors on empty submit', async ({ page }) => {
    await page.getByRole('button', { name: /注册/i }).click()
    // Should show required field errors
    const errors = page.locator('.field-error')
    await expect(errors.first()).toBeVisible()
  })

  test('shows error for short password', async ({ page }) => {
    await page.fill('input[placeholder*="用户"]', 'newuser')
    await page.fill('input[type="password"]', '123')
    await page.getByRole('button', { name: /注册/i }).click()
    await expect(page.locator('.field-error')).toBeVisible()
  })
})

// ── / (Home Page) ─────────────────────────────────────────────────────────────

test.describe('Home Page', () => {
  test('redirects to /login when unauthenticated', async ({ page }) => {
    await page.goto(BASE)
    await page.waitForURL(/\/login/)
    await expect(page).toHaveURL(/\/login/)
  })
})
