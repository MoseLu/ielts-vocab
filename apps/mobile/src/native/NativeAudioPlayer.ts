import { NativeModules } from 'react-native'
import { mobileApiClient } from '../api/mobileApi'

type NativeAudioPlayerModule = {
  playUrl: (url: string, token?: string | null) => Promise<void>
  stop: () => Promise<void>
}

const nativePlayer = NativeModules.IeltsAudioPlayer as NativeAudioPlayerModule | undefined

export async function playRemoteAudio(path: string): Promise<void> {
  if (!nativePlayer) throw new Error('Native audio playback module is unavailable')
  const token = await mobileApiClient.getAccessToken()
  await nativePlayer.playUrl(mobileApiClient.buildUrl(path), token)
}

export async function stopRemoteAudio(): Promise<void> {
  await nativePlayer?.stop?.()
}
