import type { CSSProperties, ReactNode } from 'react'

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function buildBlankWidth(targetPart: string): string {
  const visibleLength = targetPart.replace(/[^a-zA-Z'-]/g, '').length
  const emWidth = Math.max(2.8, Math.min(4.6, 2.1 + visibleLength * 0.18))
  return `${emWidth}em`
}

function buildBlankWord(targetWord: string): ReactNode {
  return (
    <span className="example-blank-word" aria-label="blanked target word">
      {targetWord.split(/\s+/).map((part, index) => (
        <span
          key={`${part}-${index}`}
          className="example-blank-segment"
          style={{ '--example-blank-width': buildBlankWidth(part) } as CSSProperties}
        />
      ))}
    </span>
  )
}

export function buildBlankSentence(sentence: string, targetWord: string): ReactNode {
  const normalizedTarget = targetWord.trim()
  if (!normalizedTarget) return sentence

  const regex = new RegExp(`(${escapeRegExp(normalizedTarget)})`, 'gi')
  const parts = sentence.split(regex)

  return parts.map((part, index) => {
    if (part.toLowerCase() !== normalizedTarget.toLowerCase()) {
      return <span key={`text-${index}`}>{part}</span>
    }

    return <span key={`blank-${index}`}>{buildBlankWord(normalizedTarget)}</span>
  })
}
