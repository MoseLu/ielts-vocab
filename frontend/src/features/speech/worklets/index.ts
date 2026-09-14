// speech worklets public surface.
//
// AudioWorkletProcessor files must be loaded by URL at runtime
// (e.g. `audioContext.audioWorklet.addModule(url)`); this barrel exposes
// the URL factory so callers do not reach into deep paths.
export const SPEECH_MIC_CAPTURE_WORKLET_URL =
  new URL('./micCaptureProcessor.js', import.meta.url).href
