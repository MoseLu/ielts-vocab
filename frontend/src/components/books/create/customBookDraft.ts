export interface CustomBookWordDraft {
  word: string
  phonetic?: string
  pos?: string
  definition?: string
}

export interface CustomBookChapterDraft {
  id: string
  title: string
  content: string
  entries: CustomBookWordDraft[]
}

export interface CustomBookPayload {
  title: string
  description: string
  education_stage: string
  exam_type: string
  ielts_skill: string
  share_enabled: boolean
  chapter_word_target: number
  chapters: Array<{
    id: string
    title: string
  }>
  words: Array<{
    chapterId: string
    word: string
    phonetic?: string
    pos?: string
    definition?: string
  }>
}

let chapterDraftCounter = 0

export const DEFAULT_CHAPTER_WORD_TARGET = 15

export const CHAPTER_WORD_TARGETS = [15, 30, 50, 100, 200]

export const EDUCATION_STAGE_OPTIONS = [
  { value: 'abroad', label: '留学' },
  { value: 'primary', label: '小学' },
  { value: 'middle', label: '初中' },
  { value: 'high', label: '高中' },
  { value: 'university', label: '大学' },
  { value: 'other', label: '其他' },
]

export const EXAM_TYPE_OPTIONS = [
  { value: 'ielts', label: '雅思' },
  { value: 'toefl', label: '托福' },
  { value: 'gre', label: 'GRE' },
  { value: 'gmat', label: 'GMAT' },
  { value: 'sat', label: 'SAT' },
  { value: 'pte', label: 'PTE' },
  { value: 'duolingo', label: '多邻国' },
  { value: 'other', label: '其他' },
]

export const IELTS_SKILL_OPTIONS = [
  { value: 'listening', label: '听力' },
  { value: 'reading', label: '阅读' },
  { value: 'writing', label: '写作' },
  { value: 'speaking', label: '口语' },
]

function nextChapterDraftId(): string {
  chapterDraftCounter += 1
  return `chapter-${chapterDraftCounter}`
}

function normalizeLine(line: string): string {
  return line.replace(/\u3000/g, ' ').trim()
}

export function parseChapterContent(content: string): CustomBookWordDraft[] {
  return content
    .split(/\r?\n/)
    .map(normalizeLine)
    .filter(Boolean)
    .map(word => ({ word }))
}

export function createChapterDraft(
  index: number,
  values: Partial<CustomBookChapterDraft> = {},
): CustomBookChapterDraft {
  const entries = values.entries ?? parseChapterContent(values.content ?? '')
  const content = values.content ?? entries.map(entry => entry.word).join('\n')
  return {
    id: values.id ?? nextChapterDraftId(),
    title: values.title?.trim() || `第${index}章`,
    content,
    entries,
  }
}

export function updateChapterContent(
  chapter: CustomBookChapterDraft,
  content: string,
): CustomBookChapterDraft {
  return {
    ...chapter,
    content,
    entries: parseChapterContent(content),
  }
}

export function countChapterWords(chapter: CustomBookChapterDraft): number {
  return chapter.entries.length
}

export function countDraftWords(chapters: CustomBookChapterDraft[]): number {
  return chapters.reduce((total, chapter) => total + countChapterWords(chapter), 0)
}

export function buildCustomBookPayload(params: {
  title: string
  educationStage: string
  examType: string
  ieltsSkill: string
  shareEnabled: boolean
  chapterWordTarget: number
  chapters: CustomBookChapterDraft[]
}): CustomBookPayload {
  const nonEmptyChapters = params.chapters.filter(chapter => chapter.entries.length > 0)
  return {
    title: params.title.trim(),
    description: '用户自定义导入词书',
    education_stage: params.educationStage,
    exam_type: params.examType,
    ielts_skill: params.examType === 'ielts' ? params.ieltsSkill : '',
    share_enabled: params.shareEnabled,
    chapter_word_target: params.chapterWordTarget,
    chapters: nonEmptyChapters.map(chapter => ({
      id: chapter.id,
      title: chapter.title.trim() || '未命名章节',
    })),
    words: nonEmptyChapters.flatMap(chapter => (
      chapter.entries.map(entry => ({
        chapterId: chapter.id,
        word: entry.word,
        phonetic: entry.phonetic,
        pos: entry.pos,
        definition: entry.definition,
      }))
    )),
  }
}
