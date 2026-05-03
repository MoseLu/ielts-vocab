import AsyncStorage from '@react-native-async-storage/async-storage'
import type { AppStorage, SecureTokenStorage } from '@ielts-vocab/app-core'

export const asyncAppStorage: AppStorage = {
  getItem: key => AsyncStorage.getItem(key),
  removeItem: key => AsyncStorage.removeItem(key),
  setItem: (key, value) => AsyncStorage.setItem(key, value),
}

const TOKEN_SERVICE = 'ielts-vocab-mobile-session'
const ACCESS_TOKEN_KEY = `${TOKEN_SERVICE}:access-token`
const REFRESH_TOKEN_KEY = `${TOKEN_SERVICE}:refresh-token`

export const mobileTokenStorage: SecureTokenStorage = {
  async clearTokens() {
    await AsyncStorage.multiRemove([ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY])
  },
  async getAccessToken() {
    return AsyncStorage.getItem(ACCESS_TOKEN_KEY)
  },
  async getRefreshToken() {
    return AsyncStorage.getItem(REFRESH_TOKEN_KEY)
  },
  async setTokens(tokens) {
    await AsyncStorage.multiSet([
      [ACCESS_TOKEN_KEY, tokens.accessToken],
      [REFRESH_TOKEN_KEY, tokens.refreshToken],
    ])
  },
}
