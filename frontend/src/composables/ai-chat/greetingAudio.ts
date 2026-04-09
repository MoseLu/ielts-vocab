import {
  playManagedAudioBuffer,
  stopManagedAudio,
  warmupManagedAudio,
} from '../../components/practice/utils.audio.playback'

const AI_GREETING_TTS_PAYLOAD = {
  emotion: 'neutral',
  model: 'speech-2.8-hd',
  provider: 'minimax',
  speed: 1,
  voice_id: 'female-tianmei',
} as const

let greetingPlaybackGeneration = 0

export async function warmupAIGreetingAudio(): Promise<void> {
  await warmupManagedAudio()
}

export function stopAIGreetingAudio(): void {
  greetingPlaybackGeneration += 1
  stopManagedAudio()
}

export async function playAIGreetingAudio(text: string): Promise<boolean> {
  const trimmedText = text.trim()
  if (!trimmedText) return false

  const generation = ++greetingPlaybackGeneration
  stopManagedAudio()

  try {
    const response = await fetch('/api/tts/generate', {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...AI_GREETING_TTS_PAYLOAD,
        text: trimmedText,
      }),
    })
    if (!response.ok) return false

    const audioBuffer = await response.arrayBuffer()
    if (audioBuffer.byteLength <= 0 || generation !== greetingPlaybackGeneration) return false

    await warmupManagedAudio()
    if (generation !== greetingPlaybackGeneration) return false

    return playManagedAudioBuffer(audioBuffer, {
      isCurrent: () => generation === greetingPlaybackGeneration,
      isStopped: () => generation !== greetingPlaybackGeneration,
      rate: 1,
      volume: 1,
    })
  } catch {
    return false
  }
}
