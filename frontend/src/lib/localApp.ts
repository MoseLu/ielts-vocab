interface LocalAppWindow extends Window {
  __IELTS_LOCAL_APP__?: {
    defaultLogin?: {
      identifier?: unknown
      password?: unknown
    }
  }
}

export interface LocalAppDefaultLogin {
  identifier: string
  password: string
}

export function getLocalAppDefaultLogin(): LocalAppDefaultLogin | null {
  if (typeof window === 'undefined') return null

  const defaultLogin = (window as LocalAppWindow).__IELTS_LOCAL_APP__?.defaultLogin
  if (
    typeof defaultLogin?.identifier !== 'string' ||
    typeof defaultLogin.password !== 'string'
  ) {
    return null
  }

  return {
    identifier: defaultLogin.identifier,
    password: defaultLogin.password,
  }
}
