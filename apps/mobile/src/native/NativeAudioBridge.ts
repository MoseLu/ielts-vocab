import { NativeEventEmitter, NativeModules } from 'react-native'

type NativeAudioCaptureModule = {
  addListener: (eventName: string) => void
  configureSession: () => Promise<void>
  removeListeners: (count: number) => void
  startPcmCapture: () => Promise<void>
  stopPcmCapture: () => Promise<void>
}

const nativeModule = NativeModules.IeltsAudioCapture as NativeAudioCaptureModule | undefined

export const audioCaptureEvents = nativeModule ? new NativeEventEmitter(nativeModule) : null

export async function configureNativeAudioSession(): Promise<void> {
  await nativeModule?.configureSession?.()
}

export async function startNativePcmCapture(): Promise<void> {
  if (!nativeModule) throw new Error('Native audio capture module is unavailable')
  await nativeModule.startPcmCapture()
}

export async function stopNativePcmCapture(): Promise<void> {
  await nativeModule?.stopPcmCapture?.()
}
