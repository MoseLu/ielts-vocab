// CORE FLOW perf measurement for ielts-vocab preview build.
// Usage: node /tmp/perf-coreflow.mjs <outJsonPath>
import { chromium } from '@playwright/test'
import { writeFileSync } from 'node:fs'

const BASE = 'http://127.0.0.1:3002'
const OUT = process.argv[2] || '/tmp/perf-baseline.json'
const ROUTES = ['/', '/plan', '/books', '/practice', '/stats']

const initObserver = `
window.__longtasks = [];
window.__bytes = 0;
try {
  const po = new PerformanceObserver((l) => {
    for (const e of l.getEntries()) window.__longtasks.push({ start: e.startTime, dur: e.duration, name: e.name });
  });
  po.observe({ entryTypes: ['longtask'] });
} catch {}
try {
  const po2 = new PerformanceObserver((l) => {
    for (const e of l.getEntries()) if (e.identifier === 'largest-contentful-paint') window.__lcp = e.startTime;
  });
  po2.observe({ type: 'largest-contentful-paint', buffered: true });
} catch {}
try {
  const po3 = new PerformanceObserver((l) => {
    for (const e of l.getEntries()) if (!window.__fcp) window.__fcp = e.startTime;
  });
  po3.observe({ type: 'paint', buffered: true });
} catch {}
`

async function pageMetrics(page) {
  return page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0] || {}
    const res = performance.getEntriesByType('resource') || []
    return {
      url: location.pathname,
      ttfb: Math.round(nav.responseStart || 0),
      domContentLoaded: Math.round(nav.domContentLoadedEventEnd || 0),
      load: Math.round(nav.loadEventEnd || 0),
      fcp: Math.round(window.__fcp || 0),
      lcp: Math.round(window.__lcp || 0),
      requests: res.length,
      transferBytes: res.reduce((a, r) => a + (r.transferSize || 0), 0) + (nav.transferSize || 0),
      longTasks: (window.__longtasks || []).filter(t => t.start > (window.__markBefore || 0)),
    }
  })
}

async function settle(page, ms = 700) {
  try { await page.waitForLoadState('networkidle', { timeout: 8000 }) } catch {}
  await page.waitForTimeout(ms)
}

async function runPass(browser, label) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  const page = await context.newPage()
  await page.addInitScript(initObserver)
  const results = {}

  // 1. cold load of /login
  const t0 = Date.now()
  await page.goto(`${BASE}/login`, { waitUntil: 'load' })
  await page.evaluate(() => { window.__markBefore = performance.now() })
  await settle(page)
  results.loginLoad = await pageMetrics(page)
  results.loginLoad.wallMs = Date.now() - t0

  // 2. login interaction
  const t1 = Date.now()
  await page.fill('input[autocomplete="username"]', 'admin')
  await page.fill('input[type="password"]', 'admin123456')
  await page.click('.auth-btn')
  await page.waitForURL(u => !String(u).includes('/login'), { timeout: 15000 }).catch(() => {})
  await settle(page)
  results.loginSubmit = { wallMs: Date.now() - t1, url: page.url() }
  results.loggedIn = !page.url().includes('/login')

  // 3. SPA interaction: click nav to /books
  const t2 = Date.now()
  const navLink = page.locator(`a[href="/books"]`).first()
  if (await navLink.count()) {
    await page.evaluate(() => { window.__markBefore = performance.now(); window.__longtasks = [] })
    await navLink.click()
    await page.waitForURL('**/books', { timeout: 15000 }).catch(() => {})
    await settle(page)
    results.spaNavBooks = await pageMetrics(page)
    results.spaNavBooks.wallMs = Date.now() - t2
  } else {
    results.spaNavBooks = { error: 'nav link not found' }
  }

  // 4. full-load each core route (measures code-split chunk loading per route)
  for (const r of ROUTES) {
    await page.evaluate(() => { window.__markBefore = performance.now(); window.__longtasks = []; window.__lcp = 0; window.__fcp = 0 })
    const t3 = Date.now()
    await page.goto(`${BASE}${r}`, { waitUntil: 'load' })
    await settle(page)
    const m = await pageMetrics(page)
    m.wallMs = Date.now() - t3
    results[`route${r === '/' ? '_home' : r.replace(/\//g, '_')}`] = m
  }

  await context.close()
  return { label, ...results }
}

const browser = await chromium.launch()
const passes = []
passes.push(await runPass(browser, 'cold'))
passes.push(await runPass(browser, 'warm'))
await browser.close()
writeFileSync(OUT, JSON.stringify(passes, null, 2))
console.log('written', OUT)
