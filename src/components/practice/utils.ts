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

// Generation counter — incremented on every stopAudio() so async fetches can
// detect that playback was cancelled while they were waiting.
let _audioGeneration = 0

// Cache of word → audio URL from Free Dictionary API (null = no recording found)
const _audioUrlCache = new Map<string, string | null>()

/**
 * Fetch a real pronunciation URL from dictionaryapi.dev (Wiktionary recordings).
 * Results are cached so subsequent calls are instant.
 */
async function fetchAudioUrl(word: string): Promise<string | null> {
  const key = word.toLowerCase()
  if (_audioUrlCache.has(key)) return _audioUrlCache.get(key)!
  try {
    const controller = new AbortController()
    const tid = setTimeout(() => controller.abort(), 3000)
    const res = await fetch(
      `https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(word)}`,
      { signal: controller.signal },
    )
    clearTimeout(tid)
    if (!res.ok) { _audioUrlCache.set(key, null); return null }
    const data = await res.json()
    for (const entry of data) {
      for (const p of (entry.phonetics || [])) {
        if (p.audio) {
          const url = (p.audio as string).startsWith('//')
            ? 'https:' + p.audio
            : p.audio as string
          if (url.startsWith('https')) {
            _audioUrlCache.set(key, url)
            return url
          }
        }
      }
    }
  } catch { /* network error or abort */ }
  _audioUrlCache.set(key, null)
  return null
}

/**
 * Play word pronunciation.
 *
 * Cache-first strategy to preserve the browser's autoplay gesture requirement:
 *  - URL cached   → play real Wiktionary recording immediately (no async gap).
 *  - URL unknown  → play Web Speech API immediately (stays in gesture context),
 *                   then fetch & cache the URL in the background so the next
 *                   play of the same word uses the real recording.
 *
 * This ensures audio works on production HTTPS where Chrome blocks audio that
 * is triggered after an async operation (which loses the user-gesture context).
 */
export function playWordAudio(
  word: string,
  settings: { playbackSpeed?: string; volume?: string },
  onEnd?: () => void,
): void {
  stopAudio()
  const gen = _audioGeneration

  const volume = parseFloat(settings.volume || '100') / 100
  const rate   = parseFloat(settings.playbackSpeed || '0.8')

  const key = word.toLowerCase()

  // ── Final fallback: Youdao ──────────────────────────────────────────────
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

  // ── Speech synthesis (used when no real recording is cached) ────────────
  const speakWithSynthesis = () => {
    if (typeof speechSynthesis === 'undefined') { speakWithYoudao(); return }
    // Hard cap: force Youdao if speech hasn't started in 5s
    const overallTimer = setTimeout(() => {
      if (_audioGeneration !== gen) return
      console.warn(`[playWordAudio] speech timeout for "${word}", Youdao fallback`)
      speakWithYoudao()
    }, 5000)
    const u = new SpeechSynthesisUtterance(word)
    u.lang   = 'en-US'
    u.rate   = rate
    u.volume = volume
    const voice = getBestEnglishVoice()
    if (voice) u.voice = voice
    if (onEnd) u.onend = () => { clearTimeout(overallTimer); onEnd() }
    u.onerror = () => {
      clearTimeout(overallTimer)
      speechSynthesis.cancel()
      console.warn(`[playWordAudio] speechSynthesis error for "${word}", Youdao fallback`)
      speakWithYoudao()
    }
    // Chrome bug: calling speak() immediately after cancel() can fire onend
    // without actually playing audio (every other word is silent). A short
    // delay lets the cancel settle before the next utterance starts.
    setTimeout(() => {
      if (_audioGeneration !== gen) return
      speechSynthesis.speak(u)
    }, 50)
  }

  // ── URL already cached — play real recording immediately ─────────────────
  if (_audioUrlCache.has(key)) {
    const url = _audioUrlCache.get(key)
    if (url) {
      const audio = new Audio(url)
      audio.volume = Math.min(1, Math.max(0, volume))
      audio.playbackRate = Math.min(4, Math.max(0.25, rate))
      if (onEnd) audio.onended = () => onEnd()
      _currentAudio = audio
      audio.play().catch(() => {
        if (_audioGeneration !== gen) return
        _currentAudio = null
        // Real audio failed — fall through to speech synthesis
        speakWithSynthesis()
      })
      return
    }
    // cached null means no recording exists → use synthesis directly
    speakWithSynthesis()
    return
  }

  // ── URL not yet cached — use speech synthesis immediately ─────────────────
  // Fetch in background to populate cache for the next play.
  speakWithSynthesis()
  fetchAudioUrl(word) // fire-and-forget; populates _audioUrlCache
}

/** Stop any in-progress audio (both Audio element and speechSynthesis). */
export function stopAudio(): void {
  _audioGeneration++
  if (_currentAudio) {
    _currentAudio.onended = null
    _currentAudio.pause()
    _currentAudio = null
  }
  if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel()
}
