export type MobileEnvironment = 'dev' | 'staging' | 'prod'

const ENVIRONMENT_URLS: Record<MobileEnvironment, string> = {
  dev: 'http://127.0.0.1:8000',
  staging: 'https://axiomaticworld.com',
  prod: 'https://axiomaticworld.com',
}

function resolveMobileEnvironment(): MobileEnvironment {
  const candidate = process.env.IELTS_MOBILE_ENV
  if (candidate === 'dev' || candidate === 'staging' || candidate === 'prod') return candidate
  return 'prod'
}

export const mobileEnvironment: MobileEnvironment = resolveMobileEnvironment()
export const apiBaseUrl = ENVIRONMENT_URLS[mobileEnvironment]
export const speechSocketUrl = apiBaseUrl.replace(/^http/, 'ws')
