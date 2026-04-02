// ── Utility Functions for Practice Components ─────────────────────────────────────

import type { Word, OptionItem } from './types'

export interface GenerateOptionsConfig {
  mode?: string
  priorityWords?: Word[]
}

export function shuffleArray<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export function normalizeWordAnswer(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[’‘`]/g, "'")
    .replace(/[‐‑‒–—―]/g, '-')
    .replace(/^[\s"'“”‘’.,!?;:()[\]{}]+/, '')
    .replace(/[\s"'“”‘’.,!?;:()[\]{}]+$/, '')
    .replace(/\s+/g, ' ')
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
  // Detect if this is a phrase (multiple words separated by spaces)
  // Phrases should NOT be syllabified - keep them as whole units
  if (word.trim().includes(' ')) {
    return [word.trim()]
  }

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

// ── Levenshtein distance ─────────────────────────────────────────────────────

function levenshtein(a: string, b: string): number {
  const m = a.length, n = b.length
  const dp: number[] = Array.from({ length: n + 1 }, (_, j) => j)
  for (let i = 1; i <= m; i++) {
    let prev = dp[0]
    dp[0] = i
    for (let j = 1; j <= n; j++) {
      const tmp = dp[j]
      dp[j] = a[i - 1] === b[j - 1] ? prev : 1 + Math.min(prev, dp[j], dp[j - 1])
      prev = tmp
    }
  }
  return dp[n]
}

// Score how confusable `candidate` is with `target` for listening mode.
// Higher score = more similar-looking/sounding = better distractor.
function confusabilityScore(target: Word, candidate: Word): number {
  const tw = target.word.toLowerCase()
  const cw = candidate.word.toLowerCase()
  let score = 0

  // Same part of speech makes meaning harder to distinguish
  if (target.pos === candidate.pos) score += 2

  // Spelling similarity (edit distance, normalised)
  const spellDist = levenshtein(tw, cw)
  const maxSpell = Math.max(tw.length, cw.length)
  score += (1 - spellDist / maxSpell) * 5

  // Common prefix (test / tastes → t-a-s/e …)
  let pfx = 0
  while (pfx < tw.length && pfx < cw.length && tw[pfx] === cw[pfx]) pfx++
  score += Math.min(pfx * 0.8, 3)

  // Common suffix (-tion / -sion, -ing / -ed …)
  let sfx = 0
  while (sfx < tw.length && sfx < cw.length &&
         tw[tw.length - 1 - sfx] === cw[cw.length - 1 - sfx]) sfx++
  score += Math.min(sfx * 0.5, 1.5)

  // Similar word length ± 2
  if (Math.abs(tw.length - cw.length) <= 2) score += 0.5

  // Phonetic similarity
  if (target.phonetic && candidate.phonetic) {
    const strip = (s: string) => s.replace(/[/[\]ˈˌ.: ]/g, '').toLowerCase()
    const tp = strip(target.phonetic)
    const cp = strip(candidate.phonetic)
    if (tp && cp) {
      const phonDist = levenshtein(tp, cp)
      const maxPhon = Math.max(tp.length, cp.length)
      score += (1 - phonDist / maxPhon) * 4
    }
  }

  return score
}

export function generateOptions(
  currentWord: Word,
  allWords: Word[],
  modeOrConfig?: string | GenerateOptionsConfig,
): { options: OptionItem[]; correctIndex: number } {
  const config: GenerateOptionsConfig = typeof modeOrConfig === 'string'
    ? { mode: modeOrConfig }
    : (modeOrConfig ?? {})
  const mode = config.mode
  const isMeaningMode = mode === 'meaning'
  const getCandidateKey = (word: Word): string => (
    isMeaningMode
      ? word.word.trim().toLowerCase()
      : word.definition.trim().toLowerCase()
  )
  const seenWords = new Set<string>()
  const seenDefinitions = new Set<string>()
  const candidates = allWords.filter((word) => {
    const wordKey = word.word.trim().toLowerCase()
    const defKey = word.definition.trim().toLowerCase()
    if (!wordKey || !defKey) return false
    if (wordKey === currentWord.word.trim().toLowerCase()) return false
    if (isMeaningMode) {
      if (seenWords.has(wordKey)) return false
    } else {
      if (word.definition === currentWord.definition) return false
      if (seenWords.has(wordKey) || seenDefinitions.has(defKey)) return false
    }
    seenWords.add(wordKey)
    seenDefinitions.add(defKey)
    return true
  })
  const priorityWordMap = new Map(
    (config.priorityWords ?? []).map((word, index) => [word.word.trim().toLowerCase(), index] as const),
  )

  let distractorWords: Word[]

  if (mode === 'listening' && candidates.length >= 3) {
    // Sort by confusability, then pick from the top portion with randomness
    const scored = candidates
      .map(w => ({ w, s: confusabilityScore(currentWord, w) }))
      .sort((a, b) => b.s - a.s)
    // Use top 40% (min 6) as the "confusable pool", shuffle and take 3
    const topN = Math.max(6, Math.ceil(scored.length * 0.4))
    const pool = scored.slice(0, topN).map(x => x.w)
    distractorWords = shuffleArray(pool).slice(0, 3)
    // Fill any gap (small vocab) with random from the rest
    if (distractorWords.length < 3) {
      const used = new Set(distractorWords.map(getCandidateKey))
      const rest = candidates.filter(w => !used.has(getCandidateKey(w)))
      distractorWords.push(...shuffleArray(rest).slice(0, 3 - distractorWords.length))
    }
  } else if (priorityWordMap.size > 0 && candidates.length >= 3) {
    const prioritized = candidates
      .map((word) => {
        const priorityIndex = priorityWordMap.get(word.word.trim().toLowerCase())
        const priorityBonus = priorityIndex == null ? 0 : 12 - Math.min(priorityIndex, 10)
        return {
          word,
          score: confusabilityScore(currentWord, word) + priorityBonus,
          priorityIndex: priorityIndex ?? Number.POSITIVE_INFINITY,
        }
      })
      .sort((a, b) => {
        if (a.priorityIndex !== b.priorityIndex) return a.priorityIndex - b.priorityIndex
        return b.score - a.score
      })

    distractorWords = prioritized.slice(0, 3).map(item => item.word)
    if (distractorWords.length < 3) {
      const used = new Set(distractorWords.map(getCandidateKey))
      distractorWords.push(
        ...prioritized
          .map(item => item.word)
          .filter(word => !used.has(getCandidateKey(word)))
          .slice(0, 3 - distractorWords.length),
      )
    }
  } else {
    distractorWords = shuffleArray(candidates).slice(0, 3)
  }

  const distractors = distractorWords.map<OptionItem>(word => (
    isMeaningMode
      ? {
          word: word.word,
          phonetic: word.phonetic,
          definition: word.definition,
          pos: word.pos,
          display_mode: 'word',
        }
      : {
          definition: word.definition,
          pos: word.pos,
          display_mode: 'definition',
        }
  ))
  const correct: OptionItem = isMeaningMode
    ? {
        word: currentWord.word,
        phonetic: currentWord.phonetic,
        definition: currentWord.definition,
        pos: currentWord.pos,
        display_mode: 'word',
      }
    : {
        definition: currentWord.definition,
        pos: currentWord.pos,
        display_mode: 'definition',
      }
  const allOpts = shuffleArray<OptionItem>([correct, ...distractors])
  const correctIndex = allOpts.findIndex(option => (
    isMeaningMode
      ? option.word?.trim().toLowerCase() === currentWord.word.trim().toLowerCase()
      : option.definition === currentWord.definition
  ))
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
  if (!voices.length) return null  // voices not loaded yet — do NOT cache, let next call retry

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
  speechSynthesis.addEventListener('voiceschanged', () => {
    _bestVoice = undefined  // force re-selection with fresh voice list
  })
}

// ── Audio playback ───────────────────────────────────────────────────────────

// Singleton audio instance — stops previous playback when a new word starts.
let _currentAudio: HTMLAudioElement | null = null

// Generation counter — incremented on every stopAudio() so async fetches can
// detect that playback was cancelled while they were waiting.
let _audioGeneration = 0

// Whether the current audio was explicitly stopped (not naturally finished).
// Allows onended to distinguish "cancelled" from "played to end".
let _audioStopped = false

// Promise that resolves once a silent HTMLAudioElement has successfully played
// through, proving the audio hardware is initialised.  Created on the first
// playWordAudio() call (requires prior user interaction for autoplay to work).
let _htmlAudioWarmupPromise: Promise<void> | null = null
const SILENT_WAV_DATA_URI =
  'data:audio/wav;base64,UklGRlYAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YTIAAACA'

/**
 * Play a 100 ms silent WAV through HTMLAudioElement to initialise the browser's
 * audio hardware pipeline.  Subsequent calls return the same cached Promise so
 * the warmup only ever runs once per session.
 */
function _warmupHtmlAudio(): Promise<void> {
  if (_htmlAudioWarmupPromise) return _htmlAudioWarmupPromise
  _htmlAudioWarmupPromise = new Promise<void>((resolve) => {
    try {
      const wa = new Audio(SILENT_WAV_DATA_URI)
      wa.volume  = 0
      let settled = false
      const done = () => {
        if (settled) return
        settled = true
        resolve()
      }
      wa.onended = done
      wa.onerror = done
      setTimeout(done, 1200)
      wa.play().catch(done)
    } catch {
      resolve()
    }
  })
  return _htmlAudioWarmupPromise
}

// Pre-warm the browser's speechSynthesis engine on module load so the first
// TTS play is not truncated.
;(function warmUpSpeechSynthesis() {
  if (typeof speechSynthesis === 'undefined') return
  const u = new SpeechSynthesisUtterance('')
  u.volume = 0
  u.rate = 1
  speechSynthesis.speak(u)
  speechSynthesis.cancel()
})()

// Cache of word → audio URL from Free Dictionary API (null = no recording found)
const _audioUrlCache = new Map<string, string | null>()

/**
 * Fetch a real pronunciation URL from dictionaryapi.dev (Wiktionary recordings).
 * Results are cached so subsequent calls are instant.
 */
async function fetchAudioUrl(word: string): Promise<string | null> {
  const key = word.toLowerCase()
  if (_audioUrlCache.has(key)) return _audioUrlCache.get(key)!

  // Skip dictionary API for phrases (contains spaces) - they're not supported
  if (word.includes(' ')) {
    _audioUrlCache.set(key, null)
    return null
  }

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
 * Priority:
 *  1. Wiktionary URL (cached)               → direct audio playback
 *  2. Youdao direct audio URL              → direct audio playback
 *  3. Speech synthesis                     → always available
 */
export function playWordAudio(
  word: string,
  settings: { playbackSpeed?: string; volume?: string },
  onEnd?: () => void,
): void {
  stopAudio()
  const gen = _audioGeneration

  const volume = parseFloat(settings.volume || '100') / 100
  const rate   = Math.min(4, Math.max(0.25, parseFloat(settings.playbackSpeed || '0.8')))

  const key = word.toLowerCase()

  // ── Wiktionary URL: already a complete file URL, play immediately ────────────
  if (_audioUrlCache.has(key)) {
    const url = _audioUrlCache.get(key)
    if (url) {
      const audio = new Audio(url)
      audio.volume = volume
      audio.playbackRate = rate
      if (onEnd) audio.onended = () => onEnd()
      _currentAudio = audio
      const doPlay = () => {
        if (_audioGeneration !== gen) return
        audio.play().catch(() => {
          if (_audioGeneration !== gen) return
          _currentAudio = null
          _playFallbackAudio(gen, word, key, volume, rate, onEnd)
        })
      }
      // Wait for hardware warmup before playing (warmup runs concurrently with
      // the audio element loading, so it adds no extra perceived delay).
      const start = () => {
        if (_audioGeneration !== gen) return
        _warmupHtmlAudio().then(doPlay)
      }

      if (audio.readyState >= 2) {
        start()
      } else {
        audio.addEventListener('canplaythrough', start, { once: true })
        audio.load()
      }
      return
    }
    // Cached null → no Wiktionary recording. Skip to Youdao.
  }

  // ── Same-origin cache, then Youdao direct URL, then TTS ──────────────────
  _playFallbackAudio(gen, word, key, volume, rate, onEnd)

  // ── Background: prefetch Wiktionary URL for next time ────────────────────
  fetchAudioUrl(word)
}

/**
 * Play a direct audio URL through HTMLAudioElement.
 * Uses browser media loading instead of fetch so cross-origin audio can play
 * without requiring the remote server to expose CORS headers.
 */
function _playAudioUrl(
  gen: number,
  url: string,
  volume: number,
  rate: number,
  onFailure: () => void,
  onEnd?: () => void,
): void {
  const audio = new Audio(url)
  audio.volume = volume
  audio.playbackRate = rate
  _currentAudio = audio

  let settled = false

  const fail = () => {
    if (settled || _audioGeneration !== gen) return
    settled = true
    if (_currentAudio === audio) _currentAudio = null
    onFailure()
  }

  audio.onerror = fail
  audio.onended = () => {
    if (settled || _audioGeneration !== gen) return
    settled = true
    if (onEnd) onEnd()
  }

  const start = () => {
    if (settled || _audioGeneration !== gen) return
    _warmupHtmlAudio().then(() => {
      if (settled || _audioGeneration !== gen) return
      audio.play().catch(fail)
    })
  }

  if (audio.readyState >= 2) {
    start()
    return
  }

  if (typeof audio.addEventListener === 'function') {
    audio.addEventListener('canplaythrough', start, { once: true })
    audio.load()
    return
  }

  start()
}

function _playFallbackAudio(
  gen: number,
  word: string,
  key: string,
  volume: number,
  rate: number,
  onEnd?: () => void,
): void {
  const youdaoUrl = `https://dict.youdao.com/dictvoice?audio=${encodeURIComponent(key)}&type=2`

  _playAudioUrl(
    gen,
    youdaoUrl,
    volume,
    rate,
    () => _speakWithSynthesis(gen, word, volume, rate, onEnd),
    onEnd,
  )
}

/**
 * Speech synthesis — always complete (no partial audio risk).
 */
function _speakWithSynthesis(
  gen: number,
  word: string | undefined,
  volume: number,
  rate: number,
  onEnd?: () => void,
): void {
  if (typeof speechSynthesis === 'undefined') return
  const overallTimer = setTimeout(() => {
    if (_audioGeneration !== gen) return
    console.warn('[playWordAudio] speech timeout, no audio played')
  }, 5000)
  const u = new SpeechSynthesisUtterance(word ?? '')
  u.lang   = 'en-US'
  u.rate   = rate
  u.volume = volume
  const voice = getBestEnglishVoice()
  if (voice) u.voice = voice
  u.onend = () => { clearTimeout(overallTimer); if (onEnd) onEnd() }
  u.onerror = () => {
    clearTimeout(overallTimer)
    speechSynthesis.cancel()
    console.warn('[playWordAudio] speechSynthesis error, no audio played')
  }
  setTimeout(() => {
    if (_audioGeneration !== gen) return
    speechSynthesis.speak(u)
  }, 50)
}

/** Stop any in-progress audio (both Audio element and speechSynthesis). */
export function stopAudio(): void {
  _audioStopped = true
  _audioGeneration++
  if (_currentAudio) {
    _currentAudio.onended = null
    _currentAudio.pause()
    _currentAudio = null
  }
  if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel()
}

// ── Example Audio ────────────────────────────────────────────────────────────────

// In-memory cache for example audio blobs: sentence → ArrayBuffer
const _exampleAudioCache = new Map<string, ArrayBuffer>()

/**
 * Play example sentence audio from MiniMax TTS (backend /api/tts/example-audio).
 * Falls back to speechSynthesis on network error.
 */
export function playExampleAudio(
  sentence: string,
  _word: string,
  settings: { playbackSpeed?: string; volume?: string },
  onEnd?: () => void,
): void {
  stopAudio()
  _audioStopped = false
  const gen = _audioGeneration

  const volume = parseFloat(settings.volume || '100') / 100
  const rate = parseFloat(settings.playbackSpeed || '1')
  const key = sentence

  const loadAndPlay = (buf: ArrayBuffer | null) => {
    if (!buf) {
      _speakWithSynthesis(gen, sentence, volume, rate, onEnd)
      return
    }
    const blob = new Blob([buf], { type: 'audio/mpeg' })
    const blobUrl = URL.createObjectURL(blob)
    const audio = new Audio(blobUrl)
    audio.volume = volume
    audio.playbackRate = rate
    audio.onended = () => { if (!_audioStopped && onEnd) onEnd() }
    _currentAudio = audio
    const doPlay = () => {
      if (_audioGeneration !== gen) return
      audio.play().catch(() => {
        if (_audioGeneration !== gen) return
        _currentAudio = null
        if (onEnd) onEnd()
      })
    }
    if (audio.readyState >= 2) {
      doPlay()
    } else {
      audio.addEventListener('canplaythrough', () => doPlay(), { once: true })
      audio.load()
    }
  }

  if (_exampleAudioCache.has(key)) {
    _warmupHtmlAudio().then(() => loadAndPlay(_exampleAudioCache.get(key)!))
    return
  }

  const warmup = _warmupHtmlAudio()
  ;(async () => {
    try {
      const res = await fetch('/api/tts/example-audio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sentence, word: _word }),
      })
      await warmup
      if (_audioGeneration !== gen) return
      if (!res.ok) { loadAndPlay(null); return }
      const buf = await res.arrayBuffer()
      _exampleAudioCache.set(key, buf)
      loadAndPlay(buf)
    } catch {
      await warmup
      loadAndPlay(null)
    }
  })()
}
