import { NativeEventEmitter, NativeModules } from 'react-native'

type NativeAudioCaptureModule = {
  addListener: (eventName: string) => void
  configureSession: () => Promise<void>
  removeListeners: (count: number) => void
  startPcmCapture: () => Promise<void>
  stopPcmCapture: () => Promise<NativeAudioCaptureResult | null>
}

const nativeModule = NativeModules.IeltsAudioCapture as NativeAudioCaptureModule | undefined

export type NativeAudioCaptureResult = {
  durationSeconds?: number
  fileUri?: string
  mimeType?: string
  name?: string
  path?: string
}

export const audioCaptureEvents = nativeModule ? new NativeEventEmitter(nativeModule) : null

export async function configureNativeAudioSession(): Promise<void> {
  await nativeModule?.configureSession?.()
}

export async function startNativePcmCapture(): Promise<void> {
  if (!nativeModule) throw new Error('Native audio capture module is unavailable')
  await nativeModule.startPcmCapture()
}

export async function stopNativePcmCapture(): Promise<NativeAudioCaptureResult | null> {
  return nativeModule?.stopPcmCapture?.() ?? null
}
