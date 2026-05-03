import { MobileApiClient, MobileAuthClient } from '@ielts-vocab/app-core'
import { apiBaseUrl } from '../config'
import { asyncAppStorage, mobileTokenStorage } from '../storage/mobileStorage'

export const mobileApiClient = new MobileApiClient({
  baseUrl: apiBaseUrl,
  tokenStorage: mobileTokenStorage,
})

export const mobileAuthClient = new MobileAuthClient({
  apiBaseUrl,
  appStorage: asyncAppStorage,
  tokenStorage: mobileTokenStorage,
})
