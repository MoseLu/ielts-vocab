import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3020'

test('smoke: login page is reachable', async ({ page }) => {
  await page.goto(`${BASE}/login`)

  await expect(page.locator('input[placeholder*="邮箱或用户名"]')).toBeVisible()
  await expect(page.locator('input[placeholder*="密码"]')).toBeVisible()
  await expect(page.getByRole('button', { name: '登录' })).toBeVisible()
})

test('smoke: unauthenticated home redirects to login', async ({ page }) => {
  await page.goto(BASE)
  await page.waitForURL(/\/login/)
  await expect(page).toHaveURL(/\/login/)
})

test('smoke: register, land on app shell, then logout', async ({ page }) => {
  const uniqueSuffix = Date.now().toString()
  const username = `smoke-user-${uniqueSuffix}`
  const email = `smoke-${uniqueSuffix}@example.com`
  const password = 'password123'

  await page.goto(`${BASE}/login`)
  await page.getByText('注册').click()
  await page.fill('input[placeholder*="用户名"]', username)
  await page.fill('input[type="email"]', email)
  await page.fill('input[placeholder="请输入密码（至少 6 位）"]', password)
  await page.fill('input[placeholder="再次输入密码"]', password)
  await page.getByRole('button', { name: '注册' }).click()

  await page.waitForURL(url => !url.pathname.startsWith('/login'))
  await expect(page.locator('.header')).toBeVisible()
  await page.locator('.user-btn').click()
  await page.getByRole('button', { name: '退出登录' }).click()

  await page.waitForURL(/\/login/)
  await expect(page).toHaveURL(/\/login/)
})
