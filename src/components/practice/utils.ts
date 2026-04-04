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

const MEANING_POS_RE = /\b(?:n|v|vi|vt|adj|adv|prep|pron|conj|aux|int|num|art|a)\.\s*/gi

function cleanMeaningFragment(value: string): string {
  return value
    .replace(MEANING_POS_RE, ' ')
    .replace(/[()（）[\]【】]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function normalizeMeaningText(value: string): string {
  return cleanMeaningFragment(value)
    .toLowerCase()
    .replace(/[;；，,、/]/g, ' ')
    .replace(/[。！？]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

const LISTENING_VARIANT_REPLACEMENTS: Array<[RegExp, string]> = [
  [/metres\b/g, 'meters'],
  [/metre\b/g, 'meter'],
  [/litres\b/g, 'liters'],
  [/litre\b/g, 'liter'],
  [/centres\b/g, 'centers'],
  [/centre\b/g, 'center'],
  [/theatres\b/g, 'theaters'],
  [/theatre\b/g, 'theater'],
]

function singularizeListeningToken(token: string): string {
  if (token.endsWith('ies') && token.length > 4) return `${token.slice(0, -3)}y`
  if (/(?:ches|shes|xes|zes|ses|oes)$/.test(token) && token.length > 4) return token.slice(0, -2)
  if (token.endsWith('s') && token.length > 3 && !/(?:ss|us|is)$/.test(token)) return token.slice(0, -1)
  return token
}

function normalizeListeningFamilyKey(word: Pick<Word, 'word' | 'group_key'>): string {
  const explicitGroupKey = normalizeWordAnswer(word.group_key ?? '')
  const normalizedWord = explicitGroupKey || normalizeWordAnswer(word.word)
  if (!normalizedWord) return ''

  const variantNormalized = LISTENING_VARIANT_REPLACEMENTS.reduce(
    (value, [pattern, replacement]) => value.replace(pattern, replacement),
    normalizedWord,
  )

  return variantNormalized
    .split(' ')
    .map(token => token.split('-').map(singularizeListeningToken).join('-'))
    .join(' ')
}

function listeningDistractorScore(
  currentWord: Word,
  candidate: Word,
  priorityIndex?: number,
): number {
  const priorityBonus = priorityIndex == null ? 0 : 6 - Math.min(priorityIndex, 5)

  return confusabilityScore(currentWord, candidate)
    + priorityBonus
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
  const isListeningMode = mode === 'listening'
  const currentWordKey = currentWord.word.trim().toLowerCase()
  const currentDefinitionKey = normalizeMeaningText(currentWord.definition)
  const currentListeningFamilyKey = isListeningMode
    ? normalizeListeningFamilyKey(currentWord)
    : ''
  const getCandidateKey = (word: Word): string => (
    isMeaningMode
      ? word.word.trim().toLowerCase()
      : isListeningMode
        ? normalizeListeningFamilyKey(word)
        : normalizeMeaningText(word.definition)
  )
  const seenWords = new Set<string>()
  const seenDefinitions = new Set<string>()
  const seenListeningFamilies = new Set<string>()
  const candidates = allWords.filter((word) => {
    const wordKey = word.word.trim().toLowerCase()
    const defKey = normalizeMeaningText(word.definition)
    const listeningFamilyKey = isListeningMode ? normalizeListeningFamilyKey(word) : ''
    if (!wordKey || !defKey || (isListeningMode && !listeningFamilyKey)) return false
    if (wordKey === currentWordKey) return false
    if (isListeningMode && listeningFamilyKey === currentListeningFamilyKey) return false
    if (isMeaningMode) {
      if (seenWords.has(wordKey)) return false
    } else {
      if (defKey === currentDefinitionKey) return false
      if (seenWords.has(wordKey) || seenDefinitions.has(defKey)) return false
      if (isListeningMode && seenListeningFamilies.has(listeningFamilyKey)) return false
    }
    seenWords.add(wordKey)
    seenDefinitions.add(defKey)
    if (isListeningMode) seenListeningFamilies.add(listeningFamilyKey)
    return true
  })
  const priorityWordMap = new Map(
    (config.priorityWords ?? []).map((word, index) => [word.word.trim().toLowerCase(), index] as const),
  )

  let distractorWords: Word[]

  if (isListeningMode && candidates.length >= 3) {
    // Listening mode is an English confusable-word discrimination task.
    const scored = candidates
      .map((word) => {
        const priorityIndex = priorityWordMap.get(word.word.trim().toLowerCase())
        return {
          word,
          score: listeningDistractorScore(currentWord, word, priorityIndex),
        }
      })
      .sort((a, b) => b.score - a.score)
    distractorWords = scored.slice(0, 3).map(item => item.word)

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
          word: word.word,
          definition: cleanMeaningFragment(word.definition) || word.definition,
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
        word: currentWord.word,
        definition: cleanMeaningFragment(currentWord.definition) || currentWord.definition,
        pos: currentWord.pos,
        display_mode: 'definition',
      }
  const allOpts = shuffleArray<OptionItem>([correct, ...distractors])
  const correctIndex = allOpts.findIndex(option => (
    isMeaningMode
      ? option.word?.trim().toLowerCase() === currentWordKey
      : normalizeMeaningText(option.definition) === currentDefinitionKey
  ))
  return { options: allOpts, correctIndex }
}

export function playWord(word: string, settings: { playbackSpeed?: string; volume?: string }): void {
  void playWordAudio(word, settings)
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
const _wordAudioCache = new Map<string, ArrayBuffer>()
const _wordAudioInFlight = new Map<string, Promise<ArrayBuffer | null>>()

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

function _wordAudioCacheKey(word: string): string {
  return word.trim().toLowerCase()
}

async function _fetchWordAudioBuffer(word: string): Promise<ArrayBuffer | null> {
  const text = word.trim()
  const key = _wordAudioCacheKey(text)
  if (!key) return null

  if (_wordAudioCache.has(key)) {
    return _wordAudioCache.get(key)!
  }

  const pending = _wordAudioInFlight.get(key)
  if (pending) {
    return pending
  }

  const request = (async () => {
    try {
      const res = await fetch(`/api/tts/word-audio?w=${encodeURIComponent(text)}`, {
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-cache' },
      })
      if (!res.ok) return null
      const buf = await res.arrayBuffer()
      _wordAudioCache.set(key, buf)
      return buf
    } catch {
      return null
    } finally {
      _wordAudioInFlight.delete(key)
    }
  })()

  _wordAudioInFlight.set(key, request)
  return request
}

export async function preloadWordAudio(word: string): Promise<boolean> {
  const buf = await _fetchWordAudioBuffer(word)
  return buf != null
}

export async function prepareWordAudioPlayback(word: string): Promise<boolean> {
  const [buf] = await Promise.all([
    _fetchWordAudioBuffer(word),
    _warmupHtmlAudio(),
  ])
  return buf != null
}

/**
 * Play a same-origin audio URL through HTMLAudioElement.
 */
function _playAudioUrl(
  gen: number,
  url: string,
  volume: number,
  rate: number,
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
    if (onEnd) onEnd()
  }

  audio.onerror = fail
  audio.onended = () => {
    if (settled || _audioGeneration !== gen) return
    settled = true
    if (_currentAudio === audio) _currentAudio = null
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

/**
 * Play word pronunciation from the local backend endpoint.
 * Fetch the MP3 bytes explicitly so browser URL caching cannot keep serving a
 * stale bad pronunciation after the server cache is repaired.
 */
export function playWordAudio(
  word: string,
  settings: { playbackSpeed?: string; volume?: string },
  onEnd?: () => void,
): Promise<boolean> {
  stopAudio()
  _audioStopped = false
  const gen = _audioGeneration
  const text = word.trim()
  if (!text) {
    if (onEnd) onEnd()
    return Promise.resolve(false)
  }

  const volume = parseFloat(settings.volume || '100') / 100
  const rate = Math.min(4, Math.max(0.25, parseFloat(settings.playbackSpeed || '0.8')))
  const key = _wordAudioCacheKey(text)

  if (_wordAudioCache.has(key)) {
    const buf = _wordAudioCache.get(key)!
    return _warmupHtmlAudio().then(() => {
      if (_audioGeneration !== gen) return false
      return _playAudioBuffer(gen, buf, volume, rate, onEnd)
    }).catch(() => {
      if (_audioGeneration !== gen) return false
      if (onEnd) onEnd()
      return false
    })
  }

  return (async () => {
    try {
      const [buf] = await Promise.all([
        _fetchWordAudioBuffer(text),
        _warmupHtmlAudio(),
      ])
      if (_audioGeneration !== gen) return false
      if (!buf) {
        if (onEnd) onEnd()
        return false
      }
      return _playAudioBuffer(gen, buf, volume, rate, onEnd)
    } catch {
      if (_audioGeneration !== gen) return false
      if (onEnd) onEnd()
      return false
    }
  })()
}

/**
 * Play an MP3 ArrayBuffer through HTMLAudioElement.
 */
function _playAudioBuffer(
  gen: number,
  buf: ArrayBuffer,
  volume: number,
  rate: number,
  onEnd?: () => void,
): Promise<boolean> {
  const blob = new Blob([buf], { type: 'audio/mpeg' })
  const blobUrl = URL.createObjectURL(blob)
  const audio = new Audio(blobUrl)
  audio.volume = volume
  audio.playbackRate = rate
  _currentAudio = audio

  let settled = false
  let started = false
  const cleanup = () => URL.revokeObjectURL(blobUrl)
  const cancel = (resolve: (value: boolean) => void) => {
    if (settled) return
    settled = true
    cleanup()
    if (_currentAudio === audio) _currentAudio = null
    resolve(started)
  }

  return new Promise<boolean>((resolve) => {
    const markStarted = () => {
      if (_audioGeneration !== gen) {
        cancel(resolve)
        return
      }
      if (started || settled) return
      started = true
      resolve(true)
    }

    const fail = () => {
      if (_audioGeneration !== gen) {
        cancel(resolve)
        return
      }
      if (settled) return
      settled = true
      cleanup()
      if (_currentAudio === audio) _currentAudio = null
      resolve(started)
      if (onEnd) onEnd()
    }

    audio.onerror = fail
    audio.onended = () => {
      if (_audioGeneration !== gen) {
        cancel(resolve)
        return
      }
      if (settled) return
      settled = true
      cleanup()
      if (_currentAudio === audio) _currentAudio = null
      resolve(started)
      if (!_audioStopped && onEnd) onEnd()
    }

    const start = () => {
      if (_audioGeneration !== gen) {
        cancel(resolve)
        return
      }
      if (settled) return
      try {
        const playResult = audio.play()
        if (playResult && typeof playResult.then === 'function') {
          void playResult.then(markStarted).catch(fail)
          return
        }
        markStarted()
      } catch {
        fail()
      }
    }

    if (typeof audio.addEventListener === 'function') {
      audio.addEventListener('playing', markStarted, { once: true })
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
  })
}

/** Stop any in-progress audio. */
export function stopAudio(): void {
  _audioStopped = true
  _audioGeneration++
  if (_currentAudio) {
    _currentAudio.onended = null
    _currentAudio.onerror = null
    _currentAudio.pause()
    _currentAudio = null
  }
}

// ── Example Audio ────────────────────────────────────────────────────────────────

// In-memory cache for example audio blobs: sentence → ArrayBuffer
const _exampleAudioCache = new Map<string, ArrayBuffer>()

/**
 * Play example sentence audio from the local MiniMax-backed backend endpoint.
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

  if (_exampleAudioCache.has(key)) {
    _warmupHtmlAudio().then(() => _playAudioBuffer(gen, _exampleAudioCache.get(key)!, volume, rate, onEnd))
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
      if (!res.ok) {
        if (onEnd) onEnd()
        return
      }
      const buf = await res.arrayBuffer()
      _exampleAudioCache.set(key, buf)
      _playAudioBuffer(gen, buf, volume, rate, onEnd)
    } catch {
      if (_audioGeneration !== gen) return
      if (onEnd) onEnd()
    }
  })()
}
