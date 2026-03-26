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
  mode?: string,
): { options: OptionItem[]; correctIndex: number } {
  const correctDef = currentWord.definition
  const candidates = allWords.filter(w => w.definition !== correctDef)

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
      const used = new Set(distractorWords.map(w => w.definition))
      const rest = candidates.filter(w => !used.has(w.definition))
      distractorWords.push(...shuffleArray(rest).slice(0, 3 - distractorWords.length))
    }
  } else {
    distractorWords = shuffleArray(candidates).slice(0, 3)
  }

  const distractors = distractorWords.map(w => ({ definition: w.definition, pos: w.pos }))
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
  // Increment generation AFTER stopAudio so the setTimeout check below
  // (which captures this value) is consistent with what stopAudio set.
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
