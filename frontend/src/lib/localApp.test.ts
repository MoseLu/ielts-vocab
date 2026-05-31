import { afterEach, describe, expect, it } from 'vitest'
import { getLocalAppDefaultLogin } from './localApp'

interface TestLocalAppWindow extends Window {
  __IELTS_LOCAL_APP__?: {
    defaultLogin?: {
      identifier?: unknown
      password?: unknown
    }
  }
}

const testWindow = window as TestLocalAppWindow

describe('getLocalAppDefaultLogin', () => {
  afterEach(() => {
    delete testWindow.__IELTS_LOCAL_APP__
  })

  it('returns injected local app credentials', () => {
    testWindow.__IELTS_LOCAL_APP__ = {
      defaultLogin: {
        identifier: 'admin',
        password: 'admin123456',
      },
    }

    expect(getLocalAppDefaultLogin()).toEqual({
      identifier: 'admin',
      password: 'admin123456',
    })
  })

  it('ignores missing or invalid injected credentials', () => {
    testWindow.__IELTS_LOCAL_APP__ = {
      defaultLogin: {
        identifier: 'admin',
        password: null,
      },
    }

    expect(getLocalAppDefaultLogin()).toBeNull()
  })
})
