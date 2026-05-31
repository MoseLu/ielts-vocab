export type MobileEnvironment = 'dev' | 'staging' | 'prod'

const PROD_BASE_URL = 'https://axiomaticworld.com'
const DEV_API_PORT = 8000
const DEV_SPEECH_PORT = 5001

function resolveMobileEnvironment(): MobileEnvironment {
  const candidate = process.env.IELTS_MOBILE_ENV
  if (candidate === 'dev' || candidate === 'staging' || candidate === 'prod') return candidate
  return 'prod'
}

function resolveDevHost(explicitHost?: string): string {
  const candidate = explicitHost?.trim() || process.env.IELTS_MOBILE_DEV_HOST?.trim()
  return candidate || '127.0.0.1'
}

function resolveBaseUrl(options: {
  devHost?: string
  environment: MobileEnvironment
  override?: string
  port: number
}): string {
  const override = options.override?.trim()
  if (override) return override
  if (options.environment === 'dev') {
    return `http://${resolveDevHost(options.devHost)}:${options.port}`
  }
  return PROD_BASE_URL
}

export function resolveMobileBaseUrls(options?: {
  apiBaseUrlOverride?: string
  devHost?: string
  environment?: MobileEnvironment
  speechBaseUrlOverride?: string
}): { apiBaseUrl: string; speechBaseUrl: string } {
  const environment = options?.environment ?? resolveMobileEnvironment()
  return {
    apiBaseUrl: resolveBaseUrl({
      devHost: options?.devHost,
      environment,
      override: options?.apiBaseUrlOverride ?? process.env.IELTS_MOBILE_API_BASE_URL,
      port: DEV_API_PORT,
    }),
    speechBaseUrl: resolveBaseUrl({
      devHost: options?.devHost,
      environment,
      override: options?.speechBaseUrlOverride ?? process.env.IELTS_MOBILE_SPEECH_BASE_URL,
      port: DEV_SPEECH_PORT,
    }),
  }
}

export const mobileEnvironment: MobileEnvironment = resolveMobileEnvironment()
export const { apiBaseUrl, speechBaseUrl } = resolveMobileBaseUrls({ environment: mobileEnvironment })
export const speechSocketUrl = speechBaseUrl.replace(/^http/, 'ws')
