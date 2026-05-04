type ErrorSeverity = 'info' | 'warning' | 'error'
type ErrorSource = 'http' | 'network' | 'window-error' | 'unhandledrejection' | 'react-error-boundary' | 'manual'

interface FrontendErrorInput {
  source: ErrorSource
  severity?: ErrorSeverity
  statusCode?: number
  method?: string
  requestUrl?: string
  routePath?: string
  message: string
  errorName?: string
  stack?: string
  componentStack?: string
  responseExcerpt?: string
  context?: Record<string, unknown>
}

interface HttpErrorInput {
  requestUrl: string
  method?: string
  response: Response
}

interface NetworkErrorInput {
  requestUrl: string
  method?: string
  error: unknown
}

const RAW_API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.trim() ?? ''
const REPORT_ENDPOINT = '/api/ops/frontend-error-logs'
const DEDUPE_WINDOW_MS = 60_000
const SENSITIVE_KEYS = new Set([
  'authorization',
  'code',
  'cookie',
  'email',
  'jwt',
  'password',
  'refresh_token',
  'secret',
  'token',
  'access_token',
])
const recentFingerprints = new Map<string, number>()
let reportingEnabled = true
let installedWindow: Window | null = null

function buildReportUrl(): string {
  const normalizedApiBase = RAW_API_BASE.replace(/\/+$/, '')
  return normalizedApiBase ? `${normalizedApiBase}${REPORT_ENDPOINT}` : REPORT_ENDPOINT
}

function truncate(value: unknown, maxLength: number): string | undefined {
  if (value === null || value === undefined) return undefined
  const text = String(value)
  if (!text) return undefined
  return text.length > maxLength ? `${text.slice(0, maxLength - 3)}...` : text
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function redactText(value: string): string {
  return value.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '[redacted-email]')
}

function isSensitiveKey(key: string): boolean {
  const normalized = key.toLowerCase()
  return [...SENSITIVE_KEYS].some(sensitiveKey => normalized.includes(sensitiveKey))
}

export function sanitizeErrorUrl(rawUrl: string | undefined): string | undefined {
  if (!rawUrl) return undefined
  try {
    const base = typeof window !== 'undefined' ? window.location.origin : 'http://localhost'
    const url = new URL(rawUrl, base)
    url.searchParams.forEach((_value, key) => {
      if (isSensitiveKey(key)) {
        url.searchParams.set(key, '[redacted]')
      }
    })
    if (!/^https?:\/\//i.test(rawUrl)) {
      return truncate(`${url.pathname}${url.search}${url.hash}`, 2048)
    }
    return truncate(url.toString(), 2048)
  } catch {
    return truncate(redactText(rawUrl), 2048)
  }
}

function routePathFromUrl(rawUrl: string | undefined): string | undefined {
  if (!rawUrl) return undefined
  try {
    const base = typeof window !== 'undefined' ? window.location.origin : 'http://localhost'
    return truncate(new URL(rawUrl, base).pathname, 255)
  } catch {
    return undefined
  }
}

function sanitizeContext(value: unknown, depth = 0): unknown {
  if (depth > 2) return truncate(value, 500)
  if (Array.isArray(value)) {
    return value.slice(0, 24).map(item => sanitizeContext(item, depth + 1))
  }
  if (isRecord(value)) {
    const entries = Object.entries(value).slice(0, 24).map(([key, item]) => {
      const safeKey = truncate(key, 80) ?? 'field'
      if (isSensitiveKey(key)) return [safeKey, '[redacted]']
      return [safeKey, sanitizeContext(item, depth + 1)]
    })
    return Object.fromEntries(entries)
  }
  return typeof value === 'string' ? truncate(redactText(value), 500) : value
}

function hashString(value: string): string {
  let hash = 2166136261
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(36)
}

function randomId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID().replace(/-/g, '')
  }
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`
}

function browserSessionId(): string | undefined {
  try {
    const key = 'frontend_error_browser_session_id'
    const existing = sessionStorage.getItem(key)
    if (existing) return existing
    const next = randomId()
    sessionStorage.setItem(key, next)
    return next
  } catch {
    return undefined
  }
}

function shouldSkipUrl(url: string | undefined): boolean {
  return Boolean(url && sanitizeErrorUrl(url)?.includes(REPORT_ENDPOINT))
}

function buildFingerprint(input: FrontendErrorInput): string {
  return hashString([
    input.source,
    input.statusCode ?? '',
    input.method ?? '',
    input.routePath ?? routePathFromUrl(input.requestUrl) ?? '',
    input.errorName ?? '',
    input.message.slice(0, 160),
  ].join('|'))
}

function shouldDedupe(fingerprint: string, now = Date.now()): boolean {
  const lastSeenAt = recentFingerprints.get(fingerprint) ?? 0
  if (now - lastSeenAt < DEDUPE_WINDOW_MS) return true
  recentFingerprints.set(fingerprint, now)
  return false
}

async function responseExcerpt(response: Response): Promise<string | undefined> {
  const clone = response.clone()
  const contentType = clone.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    const payload = await clone.json().catch(() => null)
    if (isRecord(payload)) {
      const safePayload = {
        error: payload.error,
        detail: payload.detail,
        code: payload.code,
      }
      return truncate(redactText(JSON.stringify(safePayload)), 2000)
    }
  }
  const text = await clone.text().catch(() => '')
  return truncate(redactText(text), 2000)
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message || error.name
  if (typeof error === 'string') return error
  if (isRecord(error) && typeof error.message === 'string') return error.message
  return 'Unknown frontend error'
}

function errorStack(error: unknown): string | undefined {
  return error instanceof Error ? error.stack : undefined
}

function errorName(error: unknown): string | undefined {
  if (error instanceof Error) return error.name
  if (isRecord(error) && typeof error.name === 'string') return error.name
  return undefined
}

export function reportFrontendError(input: FrontendErrorInput): void {
  if (!reportingEnabled || shouldSkipUrl(input.requestUrl)) return
  const sanitizedUrl = sanitizeErrorUrl(input.requestUrl)
  const routePath = input.routePath ?? routePathFromUrl(input.requestUrl)
  const fingerprint = buildFingerprint({ ...input, requestUrl: sanitizedUrl, routePath })
  if (shouldDedupe(fingerprint)) return

  const payload = {
    event_id: randomId(),
    source: input.source,
    severity: input.severity ?? (input.statusCode && input.statusCode >= 500 ? 'error' : 'warning'),
    status_code: input.statusCode,
    method: truncate(input.method?.toUpperCase(), 12),
    request_url: sanitizedUrl,
    route_path: routePath,
    message: truncate(redactText(input.message), 2000) ?? 'Frontend error',
    error_name: truncate(input.errorName, 120),
    stack: truncate(redactText(input.stack ?? ''), 8000),
    component_stack: truncate(redactText(input.componentStack ?? ''), 8000),
    response_excerpt: truncate(redactText(input.responseExcerpt ?? ''), 2000),
    fingerprint,
    browser_session_id: browserSessionId(),
    app_version: truncate(import.meta.env.VITE_APP_VERSION as string | undefined, 80),
    user_agent: typeof navigator !== 'undefined' ? truncate(navigator.userAgent, 500) : undefined,
    context: sanitizeContext(input.context),
  }

  void fetch(buildReportUrl(), {
    method: 'POST',
    credentials: 'include',
    keepalive: true,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).catch(() => {})
}

export function reportHttpResponseError(input: HttpErrorInput): void {
  if (input.response.ok || shouldSkipUrl(input.requestUrl)) return
  void responseExcerpt(input.response).then(excerpt => {
    reportFrontendError({
      source: 'http',
      severity: input.response.status >= 500 ? 'error' : 'warning',
      statusCode: input.response.status,
      method: input.method,
      requestUrl: input.requestUrl,
      message: `HTTP ${input.response.status} ${input.response.statusText || 'Request failed'}`,
      responseExcerpt: excerpt,
    })
  })
}

export function reportNetworkError(input: NetworkErrorInput): void {
  if (shouldSkipUrl(input.requestUrl)) return
  reportFrontendError({
    source: 'network',
    severity: 'error',
    method: input.method,
    requestUrl: input.requestUrl,
    message: errorMessage(input.error),
    errorName: errorName(input.error),
    stack: errorStack(input.error),
  })
}

export function installGlobalErrorReporting(targetWindow: Window = window): void {
  if (installedWindow === targetWindow) return
  installedWindow = targetWindow
  targetWindow.addEventListener('error', event => {
    reportFrontendError({
      source: 'window-error',
      severity: 'error',
      requestUrl: event.filename,
      message: event.message || errorMessage(event.error),
      errorName: errorName(event.error),
      stack: errorStack(event.error),
      context: { lineno: event.lineno, colno: event.colno },
    })
  })
  targetWindow.addEventListener('unhandledrejection', event => {
    reportFrontendError({
      source: 'unhandledrejection',
      severity: 'error',
      message: errorMessage(event.reason),
      errorName: errorName(event.reason),
      stack: errorStack(event.reason),
      requestUrl: targetWindow.location.href,
    })
  })
}

export function reportReactError(error: unknown, componentStack?: string): void {
  reportFrontendError({
    source: 'react-error-boundary',
    severity: 'error',
    message: errorMessage(error),
    errorName: errorName(error),
    stack: errorStack(error),
    componentStack,
    requestUrl: typeof window !== 'undefined' ? window.location.href : undefined,
  })
}

export function __resetErrorReportingForTests(): void {
  recentFingerprints.clear()
  reportingEnabled = true
  installedWindow = null
}

export function __setErrorReportingEnabledForTests(enabled: boolean): void {
  reportingEnabled = enabled
}
