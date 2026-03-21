// ── Utility Functions for Practice Components ─────────────────────────────────────

import type { Word, OptionItem } from './types'

export function shuffleArray<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

// ── Syllabification helpers ─────────────────────────────────────────────────────

const IPA_VOWELS = 'aeiouəɪʊʌæɒɔɑɛɜɐøœɨɯɵ'

export function countPhoneticSyllables(phonetic: string): number {
  const ipa = phonetic.replace(/[/[\]ˈˌ.ː]/g, '')
  let count = 0
  let i = 0
  while (i < ipa.length) {
    if (IPA_VOWELS.includes(ipa[i])) {
      count++
      i++
      while (i < ipa.length && IPA_VOWELS.includes(ipa[i])) i++
    } else i++
  }
  return Math.max(1, count)
}

const VALID_ONSET2 = new Set([
  'bl','br','ch','cl','cr','dr','dw','fl','fr','gl','gr','kl','kn',
  'ph','pl','pr','sc','sh','sk','sl','sm','sn','sp','st','sw','th','tr','tw','wh','wr',
])
const VALID_ONSET3 = new Set(['str','scr','spr','spl','squ','thr','chr'])

export function syllabifyWord(word: string, phonetic: string): string[] {
  const n = countPhoneticSyllables(phonetic)
  if (n <= 1 || word.length <= 2) return [word]

  const lower = word.toLowerCase()
  const isVowel = (ch: string, i: number): boolean => {
    if ('aeiou'.includes(ch)) return true
    if (ch === 'y' && i > 0 && !'aeiou'.includes(lower[i - 1])) return true
    return false
  }

  const vg: Array<{ start: number; end: number }> = []
  for (let i = 0; i < lower.length; ) {
    if (isVowel(lower[i], i)) {
      let j = i
      while (j < lower.length && isVowel(lower[j], j)) j++
      vg.push({ start: i, end: j })
      i = j
    } else i++
  }

  if (vg.length <= 1) return [word]

  const potentialSplits: number[] = []
  for (let g = 0; g < vg.length - 1; g++) {
    const v1End = vg[g].end
    const v2Start = vg[g + 1].start
    const gap = v2Start - v1End
    const cons = lower.slice(v1End, v2Start)
    let sp: number
    if (gap <= 1) sp = v1End
    else if (gap === 2) sp = VALID_ONSET2.has(cons) ? v1End : v1End + 1
    else sp = (VALID_ONSET3.has(cons) || VALID_ONSET2.has(cons.slice(1))) ? v1End + 1 : v1End + 1
    potentialSplits.push(sp)
  }

  const splits = potentialSplits.slice(0, n - 1)
  const parts: string[] = []
  let prev = 0
  for (const s of splits) {
    if (s > prev) parts.push(word.slice(prev, s))
    prev = s
  }
  if (prev < word.length) parts.push(word.slice(prev))
  return parts.filter(p => p.length > 0)
}

export function generateOptions(currentWord: Word, allWords: Word[]): { options: OptionItem[]; correctIndex: number } {
  const correctDef = currentWord.definition
  const others = allWords
    .filter(w => w.definition !== correctDef)
    .map(w => ({ definition: w.definition, pos: w.pos }))
  const distractors = shuffleArray(others).slice(0, 3)
  const correct = { definition: correctDef, pos: currentWord.pos }
  const allOpts = shuffleArray<OptionItem>([correct, ...distractors])
  const correctIndex = allOpts.findIndex(o => o.definition === correctDef)
  return { options: allOpts, correctIndex }
}

export function playWord(word: string, settings: { playbackSpeed?: string; volume?: string }): void {
  speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(word)
  u.rate = parseFloat(settings.playbackSpeed || '1.0')
  u.volume = parseFloat(settings.volume || '100') / 100
  speechSynthesis.speak(u)
}

// ── Voice selection ──────────────────────────────────────────────────────────

// Priority list: neural/online voices (clearest, most natural stress)
const PREFERRED_VOICES = [
  'Google US English',
  'Microsoft Aria Online (Natural)',
  'Microsoft Christopher Online (Natural)',
  'Microsoft Guy Online (Natural)',
  'Microsoft Aria',
  'Samantha',            // macOS
  'Alex',                // macOS
]

let _bestVoice: SpeechSynthesisVoice | null | undefined = undefined

function getBestEnglishVoice(): SpeechSynthesisVoice | null {
  if (_bestVoice !== undefined) return _bestVoice
  const voices = speechSynthesis.getVoices()
  if (!voices.length) return null

  for (const name of PREFERRED_VOICES) {
    const v = voices.find(v => v.name === name)
    if (v) { _bestVoice = v; return v }
  }
  // Any online (neural) en-US voice
  const online = voices.find(v => !v.localService && v.lang === 'en-US')
  if (online) { _bestVoice = online; return online }
  // Any en-US
  const enUs = voices.find(v => v.lang === 'en-US')
  if (enUs) { _bestVoice = enUs; return enUs }
  // Any English
  _bestVoice = voices.find(v => v.lang.startsWith('en')) ?? null
  return _bestVoice
}

// Reset voice cache whenever browser loads new voices
if (typeof speechSynthesis !== 'undefined') {
  speechSynthesis.addEventListener('voiceschanged', () => { _bestVoice = undefined })
}

// ── Audio playback ───────────────────────────────────────────────────────────

// Singleton audio instance — stops previous playback when a new word starts.
let _currentAudio: HTMLAudioElement | null = null

/**
 * Play word pronunciation.
 * Primary:  Web Speech API with the best available English voice
 *           (Google/Microsoft neural TTS — clear, bright, natural stress).
 * Fallback: Youdao dictionary audio if speechSynthesis is unavailable.
 */
export function playWordAudio(
  word: string,
  settings: { playbackSpeed?: string; volume?: string },
  onEnd?: () => void,
): void {
  // Stop anything currently playing
  if (_currentAudio) {
    _currentAudio.onended = null
    _currentAudio.pause()
    _currentAudio = null
  }
  speechSynthesis.cancel()

  const volume = parseFloat(settings.volume || '100') / 100
  const rate   = parseFloat(settings.playbackSpeed || '0.8')

  const speakWithSynthesis = () => {
    const u = new SpeechSynthesisUtterance(word)
    u.lang   = 'en-US'
    u.rate   = rate
    u.volume = volume
    const voice = getBestEnglishVoice()
    if (voice) u.voice = voice
    if (onEnd) u.onend = onEnd
    speechSynthesis.speak(u)
  }

  const speakWithYoudao = () => {
    const audio = new Audio(
      `https://dict.youdao.com/dictvoice?audio=${encodeURIComponent(word)}&type=2`
    )
    audio.volume = Math.min(1, Math.max(0, volume))
    audio.playbackRate = Math.min(4, Math.max(0.25, rate))
    if (onEnd) audio.onended = onEnd
    _currentAudio = audio
    audio.play().catch(() => {
      _currentAudio = null
      if (onEnd) onEnd()
    })
  }

  // Web Speech API is unavailable (rare) → fall back to Youdao
  if (typeof speechSynthesis === 'undefined') {
    speakWithYoudao()
    return
  }

  // Voices may not be ready on first call — wait for them then speak
  const voices = speechSynthesis.getVoices()
  if (!voices.length) {
    speechSynthesis.addEventListener('voiceschanged', speakWithSynthesis, { once: true })
  } else {
    speakWithSynthesis()
  }
}

/** Stop any in-progress audio (both Audio element and speechSynthesis). */
export function stopAudio(): void {
  if (_currentAudio) {
    _currentAudio.onended = null
    _currentAudio.pause()
    _currentAudio = null
  }
  speechSynthesis.cancel()
}
