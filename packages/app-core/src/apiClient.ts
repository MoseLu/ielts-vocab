import { MobileAuthSessionSchema, type MobileAuthSession } from './schemas'
import type { SecureTokenStorage } from './storage'

export interface ApiClientOptions {
  baseUrl: string
  fetchImpl?: typeof fetch
  tokenStorage: SecureTokenStorage
}

export interface ApiRequestOptions extends RequestInit {
  skipAuthRefresh?: boolean
}

type RefreshResult = 'success' | 'auth_failed' | 'temporarily_unavailable'

export class MobileApiClient {
  private readonly baseUrl: string
  private readonly fetchImpl: typeof fetch
  private readonly tokenStorage: SecureTokenStorage
  private refreshInFlight: Promise<RefreshResult> | null = null

  constructor(options: ApiClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, '')
    this.fetchImpl = options.fetchImpl ?? fetch
    this.tokenStorage = options.tokenStorage
  }

  buildUrl(path: string): string {
    if (/^https?:\/\//i.test(path)) return path
    return `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`
  }

  getAccessToken(): Promise<string | null> {
    return this.tokenStorage.getAccessToken()
  }

  async request(path: string, options: ApiRequestOptions = {}): Promise<Response> {
    const { skipAuthRefresh = false, ...requestOptions } = options
    const response = await this.performRequest(path, requestOptions)
    if (response.status !== 401 || skipAuthRefresh) return response

    const refreshResult = await this.refreshSession()
    if (refreshResult !== 'success') return response
    return this.performRequest(path, requestOptions)
  }

  async refreshSession(): Promise<RefreshResult> {
    if (this.refreshInFlight) return this.refreshInFlight
    this.refreshInFlight = this.doRefresh().finally(() => {
      this.refreshInFlight = null
    })
    return this.refreshInFlight
  }

  private async doRefresh(): Promise<RefreshResult> {
    const refreshToken = await this.tokenStorage.getRefreshToken()
    if (!refreshToken) return 'auth_failed'
    try {
      const response = await this.fetchImpl(this.buildUrl('/api/auth/mobile/refresh'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (response.status === 401) {
        await this.tokenStorage.clearTokens()
        return 'auth_failed'
      }
      if (!response.ok) return 'temporarily_unavailable'
      const parsed = MobileAuthSessionSchema.parse(await response.json()) as MobileAuthSession
      await this.tokenStorage.setTokens({
        accessToken: parsed.access_token,
        refreshToken: parsed.refresh_token,
      })
      return 'success'
    } catch {
      return 'temporarily_unavailable'
    }
  }

  private async performRequest(path: string, options: RequestInit): Promise<Response> {
    const token = await this.tokenStorage.getAccessToken()
    const headers = new Headers(options.headers)
    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json')
    }
    if (token) headers.set('Authorization', `Bearer ${token}`)
    return this.fetchImpl(this.buildUrl(path), { ...options, headers })
  }

  async json<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    const response = await this.request(path, options)
    const payload = await response.json().catch(() => null)
    if (!response.ok) {
      const message = payload && typeof payload === 'object' && 'error' in payload
        ? String(payload.error)
        : `Request failed with ${response.status}`
      throw new Error(message)
    }
    return payload as T
  }
}
