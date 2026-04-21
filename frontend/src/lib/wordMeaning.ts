export type WordMeaningGroup = {
  posLabel: string
  meaningText: string
}

const WORD_MEANING_POS_LABELS = new Map([
  ['n.', 'n.'],
  ['v.', 'v.'],
  ['vi.', 'vi.'],
  ['vt.', 'vt.'],
  ['adj.', 'adj.'],
  ['adv.', 'adv.'],
  ['prep.', 'prep.'],
  ['pron.', 'pron.'],
  ['conj.', 'conj.'],
  ['aux.', 'aux.'],
  ['int.', 'int.'],
  ['num.', 'num.'],
  ['art.', 'art.'],
  ['a.', 'a.'],
])

const WORD_MEANING_BOUNDARY_RE = /[;；。!?！？]/u
const WORD_MEANING_EDGE_PUNCTUATION_RE = /^[\s;；，,、。!?！？]+|[\s;；，,、。!?！？]+$/gu

export const WORD_MEANING_POS_RE = /\b(?:vi|vt|adj|adv|prep|pron|conj|aux|int|num|art|n|v|a)\.\s*/gi

function normalizeMeaningPosLabel(value: string | null | undefined): string {
  const trimmedValue = (value ?? '').trim().toLowerCase()
  return WORD_MEANING_POS_LABELS.get(trimmedValue) ?? (value ?? '').trim()
}

function trimMeaningChunk(value: string): string {
  return value
    .replace(WORD_MEANING_EDGE_PUNCTUATION_RE, '')
    .replace(/\s+/gu, ' ')
    .trim()
}

function getPreviousSignificantChar(text: string, fromIndex: number): string {
  for (let index = fromIndex - 1; index >= 0; index -= 1) {
    const currentChar = text[index]
    if (!/\s/u.test(currentChar)) return currentChar
  }
  return ''
}

function isBoundaryPosMarker(text: string, markerIndex: number): boolean {
  if (markerIndex === 0) return true
  return WORD_MEANING_BOUNDARY_RE.test(getPreviousSignificantChar(text, markerIndex))
}

function collectMeaningPosMarkers(definition: string): Array<{ end: number; posLabel: string; start: number }> {
  const markers: Array<{ end: number; posLabel: string; start: number }> = []
  WORD_MEANING_POS_RE.lastIndex = 0

  let match = WORD_MEANING_POS_RE.exec(definition)
  while (match) {
    if (isBoundaryPosMarker(definition, match.index)) {
      markers.push({
        start: match.index,
        end: match.index + match[0].length,
        posLabel: normalizeMeaningPosLabel(match[0]),
      })
    }
    match = WORD_MEANING_POS_RE.exec(definition)
  }

  WORD_MEANING_POS_RE.lastIndex = 0
  return markers
}

function appendMeaningGroup(groups: WordMeaningGroup[], posLabel: string, chunk: string) {
  const normalizedPosLabel = normalizeMeaningPosLabel(posLabel)
  const meaningText = trimMeaningChunk(chunk)
  if (!normalizedPosLabel && !meaningText) return

  const lastGroup = groups[groups.length - 1]
  if (lastGroup && lastGroup.posLabel === normalizedPosLabel && meaningText) {
    lastGroup.meaningText = trimMeaningChunk([lastGroup.meaningText, meaningText].filter(Boolean).join('；'))
    return
  }

  groups.push({ posLabel: normalizedPosLabel, meaningText })
}

export function parseWordMeaningGroups({
  definition,
  pos,
}: {
  definition: string | null | undefined
  pos: string | null | undefined
}): WordMeaningGroup[] {
  const rawDefinition = (definition ?? '').trim()
  const fallbackPosLabel = normalizeMeaningPosLabel(pos)

  if (!rawDefinition) {
    return fallbackPosLabel ? [{ posLabel: fallbackPosLabel, meaningText: '' }] : []
  }

  const posMarkers = collectMeaningPosMarkers(rawDefinition)
  if (posMarkers.length === 0) {
    return [{
      posLabel: fallbackPosLabel,
      meaningText: trimMeaningChunk(rawDefinition),
    }]
  }

  const groups: WordMeaningGroup[] = []
  let currentPosLabel = fallbackPosLabel
  let cursor = 0

  posMarkers.forEach(marker => {
    appendMeaningGroup(groups, currentPosLabel, rawDefinition.slice(cursor, marker.start))
    currentPosLabel = marker.posLabel
    cursor = marker.end
  })
  appendMeaningGroup(groups, currentPosLabel, rawDefinition.slice(cursor))

  return groups.length > 0
    ? groups
    : [{
        posLabel: fallbackPosLabel,
        meaningText: trimMeaningChunk(rawDefinition),
      }]
}
