import { shuffleArray } from '../../lib'
import type { Word } from './types'

export interface MatchWord extends Word {
  key: string
  groupKey: string
}

export interface MatchGroup {
  key: string
  words: MatchWord[]
}

export interface MatchCard {
  id: string
  side: 'word' | 'definition'
  wordKey: string
  groupKey: string
  label: string
  word: string
  phonetic?: string
}

export interface MatchProgressSnapshot {
  current_index: number
  correct_count: number
  wrong_count: number
  is_completed: boolean
  words_learned: number
  answered_words: string[]
  round_group_keys?: string[]
  updatedAt?: string
}

export function buildMatchGroups(words: Word[]): MatchGroup[] {
  const hasExplicitGroups = words.some(word => typeof word.group_key === 'string' && word.group_key.trim())

  if (hasExplicitGroups) {
    const groupsByKey = new Map<string, MatchWord[]>()
    const orderedKeys: string[] = []

    words.forEach((word, index) => {
      const groupKey = word.group_key?.trim() || `group-${index}`
      if (!groupsByKey.has(groupKey)) {
        groupsByKey.set(groupKey, [])
        orderedKeys.push(groupKey)
      }

      groupsByKey.get(groupKey)?.push({
        ...word,
        key: `${groupKey}-${index}-${word.word.toLowerCase()}`,
        groupKey,
      })
    })

    return orderedKeys
      .map(groupKey => ({
        key: groupKey,
        words: groupsByKey.get(groupKey) ?? [],
      }))
      .filter(group => group.words.length >= 2)
  }

  const groups: MatchGroup[] = []

  for (let index = 0; index + 1 < words.length; index += 2) {
    const left = words[index]
    const right = words[index + 1]
    const groupKey = `group-${Math.floor(index / 2)}`

    groups.push({
      key: groupKey,
      words: [
        {
          ...left,
          key: `${groupKey}-0-${left.word.toLowerCase()}`,
          groupKey,
        },
        {
          ...right,
          key: `${groupKey}-1-${right.word.toLowerCase()}`,
          groupKey,
        },
      ],
    })
  }

  return groups
}

export function buildRoundCards(
  groups: MatchGroup[],
  answeredWordKeys: Set<string>,
): MatchCard[] {
  const clusteredCards = shuffleArray(groups).map(group =>
    shuffleArray(
      group.words
        .filter(word => !answeredWordKeys.has(word.key))
        .flatMap(word => ([
          {
            id: `word-${word.key}`,
            side: 'word' as const,
            wordKey: word.key,
            groupKey: word.groupKey,
            label: word.word,
            word: word.word,
            phonetic: word.phonetic,
          },
          {
            id: `definition-${word.key}`,
            side: 'definition' as const,
            wordKey: word.key,
            groupKey: word.groupKey,
            label: word.definition,
            word: word.word,
          },
        ])),
    ),
  )

  return clusteredCards.flat()
}

export function getUnresolvedGroups(
  groups: MatchGroup[],
  answeredWordKeys: Set<string>,
): MatchGroup[] {
  return groups.filter(group => group.words.some(word => !answeredWordKeys.has(word.key)))
}

export function resolveRoundGroupKeys(
  groups: MatchGroup[],
  answeredWordKeys: Set<string>,
  groupsPerRound: number,
  storedKeys?: string[],
): string[] {
  if (storedKeys?.length) {
    const stored = groups.filter(group =>
      storedKeys.includes(group.key) && group.words.some(word => !answeredWordKeys.has(word.key)),
    )
    if (stored.length > 0) {
      return stored
        .slice(0, groupsPerRound)
        .map(group => group.key)
    }
  }

  return getUnresolvedGroups(groups, answeredWordKeys)
    .slice(0, groupsPerRound)
    .map(group => group.key)
}

export function getRoundGroups(groups: MatchGroup[], roundGroupKeys: string[]): MatchGroup[] {
  const allowedKeys = new Set(roundGroupKeys)
  return groups.filter(group => allowedKeys.has(group.key))
}

export function buildWordKeySet(words: string[] | undefined): Set<string> {
  return new Set(words ?? [])
}
