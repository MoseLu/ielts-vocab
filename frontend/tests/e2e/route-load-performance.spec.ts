// Route load measurement for AppRoutes.tsx paths.
// Run: `pnpm exec playwright test tests/e2e/route-load-performance.spec.ts` (starts dev server unless PLAYWRIGHT_SKIP_WEBSERVER=true).
// Preview build: terminal A `pnpm preview` → http://127.0.0.1:3002 ; terminal B `BASE_URL=http://127.0.0.1:3002 PLAYWRIGHT_SKIP_WEBSERVER=true pnpm exec playwright test tests/e2e/route-load-performance.spec.ts`
// Production-style (real /api/**, no Playwright stubs): `BASE_URL=https://axiomaticworld.com PLAYWRIGHT_SKIP_WEBSERVER=true pnpm exec playwright test tests/e2e/route-load-performance.spec.ts`
// - Auto uses real APIs when BASE_URL host is axiomaticworld.com (www included). Override: ROUTE_PERF_REAL_API=1, or force mocks: ROUTE_PERF_MOCK_API=1.
// - Protected routes: without env creds only guest/public paths are timed; optional `ROUTE_PERF_PROD_USERNAME` + `ROUTE_PERF_PROD_PASSWORD` performs a single /login flow first (supply your own account—do not use local-only fixtures on prod).
//
// Auth (mock mode): `AuthContext` validates `auth_user` via GET /api/auth/me — this spec stubs /api/** so protected routes render without a real login.

import { test, type BrowserContext, type Page } from '@playwright/test'
import { STORAGE_KEYS } from '../../src/constants'

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3020'

function perfHost(hostname: string): boolean {
  return hostname === 'axiomaticworld.com' || hostname === 'www.axiomaticworld.com'
}

function shouldUseRealApi(): boolean {
  if (process.env.ROUTE_PERF_MOCK_API === '1') return false
  if (process.env.ROUTE_PERF_REAL_API === '1') return true
  try {
    return perfHost(new URL(BASE).hostname)
  } catch {
    return false
  }
}

async function tryProdLogin(page: Page, context: BrowserContext): Promise<boolean> {
  const user = process.env.ROUTE_PERF_PROD_USERNAME?.trim()
  const pass = process.env.ROUTE_PERF_PROD_PASSWORD?.trim()
  if (!user || !pass) return false
  await context.clearCookies()
  await page.goto(`${BASE.replace(/\/$/, '')}/login`, { waitUntil: 'load', timeout: 90_000 })
  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
  await page.getByPlaceholder('请输入邮箱或用户名').fill(user)
  await page.getByPlaceholder('请输入密码（至少 6 位）').fill(pass)
  await Promise.all([
    page.waitForURL(url => url.pathname === '/plan', { timeout: 120_000 }),
    page.locator('form button.auth-btn[type="submit"]').filter({ hasText: '登录' }).first().click(),
  ])
  return true
}

/** Matches DEFAULT_GAME_THEME_ID in `frontend/src/app/GameRouteElement.tsx`. */
const GAME_THEME_SAMPLE = 'study-campus'

const PERF_SESSION_USER = {
  id: 1,
  email: 'route-perf@example.com',
  username: 'route_perf',
  avatar_url: null as string | null,
  is_admin: true,
  created_at: '2020-01-01T00:00:00.000Z',
}

interface RouteRow {
  path: string
  bucket: 'guest' | 'auth'
  domContentLoadedMs: number | null
  loadEventMs: number | null
  lcpMs: number | null
  wallClockMs: number
  finalUrl: string
  note?: string
}

/**
 * Mocks session probes and stubs every other `/api/**` call so a local/proxied backend cannot
 * return `401` mid-load and clear `AuthContext` (which would redirect protected routes to `/login`).
 */
async function installApiStubsForRoutePerf(page: Page) {
  const sessionJson = JSON.stringify({
    user: PERF_SESSION_USER,
    access_expires_in: 3600,
  })
  await page.route('**/api/**', async route => {
    const req = route.request()
    const url = req.url()
    if (url.includes('/api/auth/me') || url.includes('/api/auth/refresh')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: sessionJson,
      })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '{}',
    })
  })
}

async function collectNavigationMs(page: Page): Promise<{ domContentLoadedMs: number | null; loadEventMs: number | null }> {
  return page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation').at(-1) as PerformanceNavigationTiming | undefined
    if (!nav || nav.startTime === undefined) return { domContentLoadedMs: null, loadEventMs: null }
    return {
      domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd - nav.fetchStart),
      loadEventMs: nav.loadEventEnd > 0 ? Math.round(nav.loadEventEnd - nav.fetchStart) : null,
    }
  })
}

async function collectLcpMs(page: Page): Promise<number | null> {
  await page.waitForTimeout(400)
  return page.evaluate(() => {
    const entries = performance.getEntriesByType('largest-contentful-paint') as PerformanceEntry[]
    const last = entries.at(-1)
    return last ? Math.round(last.startTime) : null
  })
}

async function measurePath(
  page: Page,
  path: string,
  bucket: 'guest' | 'auth',
  note?: string,
): Promise<RouteRow> {
  const url = `${BASE.replace(/\/$/, '')}${path.startsWith('/') ? path : `/${path}`}`
  const wallStart = Date.now()
  await page.goto(url, { waitUntil: 'load', timeout: 90_000 })
  const wallClockMs = Date.now() - wallStart
  const { domContentLoadedMs, loadEventMs } = await collectNavigationMs(page)
  const lcpMs = await collectLcpMs(page)
  const finalUrl = page.url()
  return {
    path,
    bucket,
    domContentLoadedMs,
    loadEventMs,
    lcpMs,
    wallClockMs,
    finalUrl,
    note,
  }
}

function markdownTable(rows: RouteRow[]): string {
  const header = '| path | bucket | DCL (ms) | load (ms) | LCP (ms) | wall (ms) | final URL | notes |'
  const sep = '| --- | --- | ---: | ---: | ---: | ---: | --- | --- |'
  const lines = rows.map(r => {
    const dcl = r.domContentLoadedMs ?? '—'
    const load = r.loadEventMs ?? '—'
    const lcp = r.lcpMs ?? '—'
    const note = r.note ?? ''
    return `| \`${r.path}\` | ${r.bucket} | ${dcl} | ${load} | ${lcp} | ${r.wallClockMs} | \`${r.finalUrl.replace(BASE, '') || '/'}\` | ${note} |`
  })
  return [header, sep, ...lines].join('\n')
}

const GUEST_PATHS: { path: string; note?: string }[] = [
  { path: '/login' },
  { path: '/register' },
  { path: '/forgot-password' },
  { path: '/terms' },
  { path: '/404' },
  { path: '/', note: 'redirects to /login when unauthenticated' },
]

const AUTH_PATHS: { path: string; note?: string }[] = [
  { path: '/plan' },
  { path: '/books' },
  { path: '/books/create' },
  { path: '/practice', note: 'with API stubs may redirect to /plan' },
  { path: '/practice?mode=listening', note: 'query variant; stubs may redirect to /plan' },
  { path: '/practice/confusable' },
  { path: '/game' },
  { path: '/game/themes' },
  { path: `/game/themes/${GAME_THEME_SAMPLE}` },
  { path: `/game/themes/${GAME_THEME_SAMPLE}/mission` },
  { path: '/game/mission' },
  { path: '/exams' },
  { path: '/exams/1', note: 'representative :paperId' },
  { path: '/errors' },
  { path: '/stats' },
  { path: '/profile' },
  { path: '/vocab-test' },
  { path: '/journal' },
  { path: '/admin', note: 'requires isAdmin (mock user is admin)' },
  { path: '/speaking', note: 'legacy redirect → /game' },
  { path: '/not-a-real-route', note: 'catch-all → /404' },
]

test.describe.configure({ mode: 'serial' })

test('measure frontend route loads (navigation timing + optional LCP)', async ({ page, context }) => {
  const rows: RouteRow[] = []

  for (const { path, note } of GUEST_PATHS) {
    await context.clearCookies()
    await page.goto(BASE, { waitUntil: 'domcontentloaded' })
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
    try {
      rows.push(await measurePath(page, path, 'guest', note))
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error(`[route-load] FAILED guest ${path}:`, err)
      throw err
    }
  }

  const realApi = shouldUseRealApi()
  let authMeasured: 'mock-stubs' | 'prod-session' | 'guest-only'

  if (realApi) {
    const loggedIn = await tryProdLogin(page, context)
    if (!loggedIn) {
      // eslint-disable-next-line no-console
      console.warn(
        '\n[route-load] Real API mode without ROUTE_PERF_PROD_USERNAME/PASSWORD: skipping authenticated routes (timing table is guest/public only).\n',
      )
      authMeasured = 'guest-only'
    } else {
      authMeasured = 'prod-session'
    }
  } else {
    await installApiStubsForRoutePerf(page)
    await context.addInitScript(
      ({ key, user }) => {
        localStorage.setItem(key, JSON.stringify(user))
      },
      { key: STORAGE_KEYS.AUTH_USER, user: PERF_SESSION_USER },
    )
    authMeasured = 'mock-stubs'
  }

  if (authMeasured !== 'guest-only') {
    for (const { path, note } of AUTH_PATHS) {
      try {
        rows.push(await measurePath(page, path, 'auth', note))
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error(`[route-load] FAILED auth ${path}:`, err)
        throw err
      }
    }
  }

  const md = markdownTable(rows)
  // eslint-disable-next-line no-console
  console.log('\n--- Route load report (see frontend/src/app/AppRoutes.tsx) ---\n')
  // eslint-disable-next-line no-console
  console.log(md)
  // eslint-disable-next-line no-console
  console.log(`\nBASE_URL=${BASE}`)
  const methodNote =
    authMeasured === 'mock-stubs'
      ? 'Auth: localStorage auth_user + Playwright stubs for all /api/** (session + empty JSON).'
      : authMeasured === 'prod-session'
        ? 'Auth: one real /login with ROUTE_PERF_PROD_*; no route interception; subsequent navigations use live /api/**.'
        : 'Auth: not measured (real API mode; set ROUTE_PERF_PROD_USERNAME + ROUTE_PERF_PROD_PASSWORD for protected routes).'
  // eslint-disable-next-line no-console
  console.log(
    `Method: full navigation; PerformanceNavigationTiming vs fetchStart after waitUntil=load; LCP ~400ms after load (often empty in headless). ${methodNote}\n`,
  )
})
