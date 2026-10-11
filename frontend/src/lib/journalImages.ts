export const MAX_JOURNAL_IMAGES = 3

const JOURNAL_IMAGE_RE = /!\[[^\]]*]\((data:image\/[^)]+)\)/g

export function extractJournalImages(content: string, maxImages = MAX_JOURNAL_IMAGES): string[] {
  return Array.from(content.matchAll(JOURNAL_IMAGE_RE), match => match[1]).slice(0, maxImages)
}

export function stripJournalImages(content: string): string {
  return content.replace(JOURNAL_IMAGE_RE, '').replace(/\n{3,}/g, '\n\n').trim()
}
