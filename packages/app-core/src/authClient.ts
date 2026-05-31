import { MobileAuthSessionSchema, type MobileAuthSession } from './schemas'
import type { AppStorage, SecureTokenStorage } from './storage'
import { CORE_STORAGE_KEYS, writeJson } from './storage'

export interface MobileAuthClientOptions {
  apiBaseUrl: string
  appStorage: AppStorage
  fetchImpl?: typeof fetch
  tokenStorage: SecureTokenStorage
}

export class MobileAuthClient {
  private readonly apiBaseUrl: string
  private readonly appStorage: AppStorage
  private readonly fetchImpl: typeof fetch
  private readonly tokenStorage: SecureTokenStorage

  constructor(options: MobileAuthClientOptions) {
    this.apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, '')
    this.appStorage = options.appStorage
    this.fetchImpl = options.fetchImpl ?? fetch
    this.tokenStorage = options.tokenStorage
  }

  async login(identifier: string, password: string): Promise<MobileAuthSession> {
    const response = await this.fetchImpl(`${this.apiBaseUrl}/api/auth/mobile/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: identifier, password }),
    })
    return this.storeSessionResponse(response, '登录失败')
  }

  async wechatLogin(code: string, state?: string): Promise<MobileAuthSession> {
    const response = await this.fetchImpl(`${this.apiBaseUrl}/api/auth/mobile/wechat-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, state }),
    })
    return this.storeSessionResponse(response, '微信登录失败')
  }

  private async storeSessionResponse(response: Response, fallbackMessage: string): Promise<MobileAuthSession> {
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.error || fallbackMessage)
    }
    const session = MobileAuthSessionSchema.parse(payload)
    await this.tokenStorage.setTokens({
      accessToken: session.access_token,
      refreshToken: session.refresh_token,
    })
    await writeJson(this.appStorage, CORE_STORAGE_KEYS.authUser, session.user)
    return session
  }

  async logout(): Promise<void> {
    const accessToken = await this.tokenStorage.getAccessToken()
    const refreshToken = await this.tokenStorage.getRefreshToken()
    if (accessToken) {
      await this.fetchImpl(`${this.apiBaseUrl}/api/auth/mobile/logout`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => undefined)
    }
    await this.tokenStorage.clearTokens()
    await this.appStorage.removeItem(CORE_STORAGE_KEYS.authUser)
  }
}
