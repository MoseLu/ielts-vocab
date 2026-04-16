export type SpeakingPrompt =
  | {
      id: string
      kind: 'question'
      text: string
    }
  | {
      id: string
      kind: 'cue-card'
      prompt: string
      bullets: string[]
      prepLabel: string
      answerLabel: string
    }

export type SpeakingSet = {
  id: string
  theme: string
  preview: string
  prompts: SpeakingPrompt[]
}

export const SPEAKING_SETS: SpeakingSet[] = [
  {
    id: 'city-life',
    theme: '家乡与城市生活',
    preview: '城市、居住环境、公共空间',
    prompts: [
      { id: 'city-life-1', kind: 'question', text: 'Do you live in a big city or a small town?' },
      { id: 'city-life-2', kind: 'question', text: 'What do you like most about your hometown?' },
      { id: 'city-life-3', kind: 'question', text: 'Has your area changed much in recent years?' },
      { id: 'city-life-4', kind: 'question', text: 'Do you prefer busy places or quiet places?' },
      { id: 'city-life-5', kind: 'question', text: 'Is public transport convenient where you live?' },
      {
        id: 'city-life-6',
        kind: 'cue-card',
        prompt: 'Describe a place in your city where you like to spend time.',
        bullets: [
          'where the place is',
          'when you usually go there',
          'what you do there',
          'and explain why this place is important to you',
        ],
        prepLabel: '1 分钟准备',
        answerLabel: '1-2 分钟作答',
      },
      { id: 'city-life-7', kind: 'question', text: 'Why do some public places become popular with young people?' },
      { id: 'city-life-8', kind: 'question', text: 'How can cities design better spaces for community life?' },
      { id: 'city-life-9', kind: 'question', text: 'Do modern cities make people feel more connected or more isolated?' },
      { id: 'city-life-10', kind: 'question', text: 'Should governments spend more on parks or on transport infrastructure?' },
    ],
  },
  {
    id: 'study-work',
    theme: '学习与工作节奏',
    preview: '学习习惯、技能成长、职业准备',
    prompts: [
      { id: 'study-work-1', kind: 'question', text: 'Do you work or are you a student?' },
      { id: 'study-work-2', kind: 'question', text: 'What part of your daily schedule is the busiest?' },
      { id: 'study-work-3', kind: 'question', text: 'Do you prefer studying alone or with other people?' },
      { id: 'study-work-4', kind: 'question', text: 'Have your study habits changed over time?' },
      { id: 'study-work-5', kind: 'question', text: 'What kind of job would you like to do in the future?' },
      {
        id: 'study-work-6',
        kind: 'cue-card',
        prompt: 'Describe a skill you learned that has been useful in your study or work.',
        bullets: [
          'what the skill is',
          'when and how you learned it',
          'how you use it now',
          'and explain why it is useful to you',
        ],
        prepLabel: '1 分钟准备',
        answerLabel: '1-2 分钟作答',
      },
      { id: 'study-work-7', kind: 'question', text: 'What skills are most important for young people today?' },
      { id: 'study-work-8', kind: 'question', text: 'Do schools teach practical skills well enough?' },
      { id: 'study-work-9', kind: 'question', text: 'Why do some people keep learning after they start working?' },
      { id: 'study-work-10', kind: 'question', text: 'Will technology change the skills employers value in the future?' },
    ],
  },
  {
    id: 'technology',
    theme: '科技与日常选择',
    preview: '设备使用、线上学习、科技影响',
    prompts: [
      { id: 'technology-1', kind: 'question', text: 'What device do you use most often every day?' },
      { id: 'technology-2', kind: 'question', text: 'Do you often learn things online?' },
      { id: 'technology-3', kind: 'question', text: 'Have you ever reduced your screen time on purpose?' },
      { id: 'technology-4', kind: 'question', text: 'Do older people around you use technology confidently?' },
      { id: 'technology-5', kind: 'question', text: 'What kind of technology would you like to learn next?' },
      {
        id: 'technology-6',
        kind: 'cue-card',
        prompt: 'Describe a piece of technology that has helped you in an important way.',
        bullets: [
          'what it is',
          'when you started using it',
          'what you use it for',
          'and explain why it has been important to you',
        ],
        prepLabel: '1 分钟准备',
        answerLabel: '1-2 分钟作答',
      },
      { id: 'technology-7', kind: 'question', text: 'Why do some technologies spread faster than others?' },
      { id: 'technology-8', kind: 'question', text: 'Has technology made people more productive or more distracted?' },
      { id: 'technology-9', kind: 'question', text: 'Should children use digital devices from an early age?' },
      { id: 'technology-10', kind: 'question', text: 'How can society help older adults adapt to new technology?' },
    ],
  },
  {
    id: 'environment',
    theme: '环境与生活方式',
    preview: '环保习惯、公共政策、社会责任',
    prompts: [
      { id: 'environment-1', kind: 'question', text: 'Do people in your area pay attention to recycling?' },
      { id: 'environment-2', kind: 'question', text: 'Have you ever changed a habit to protect the environment?' },
      { id: 'environment-3', kind: 'question', text: 'Is there enough green space where you live?' },
      { id: 'environment-4', kind: 'question', text: 'Do you think people use too much plastic nowadays?' },
      { id: 'environment-5', kind: 'question', text: 'What environmental issues concern you most?' },
      {
        id: 'environment-6',
        kind: 'cue-card',
        prompt: 'Describe an environmental problem that you would like to help solve.',
        bullets: [
          'what the problem is',
          'where you see it',
          'why it is serious',
          'and explain what people could do about it',
        ],
        prepLabel: '1 分钟准备',
        answerLabel: '1-2 分钟作答',
      },
      { id: 'environment-7', kind: 'question', text: 'Why is it difficult to change people’s environmental habits?' },
      { id: 'environment-8', kind: 'question', text: 'Should governments or individuals take more responsibility for environmental protection?' },
      { id: 'environment-9', kind: 'question', text: 'Do economic goals conflict with environmental goals?' },
      { id: 'environment-10', kind: 'question', text: 'How can schools encourage children to care about environmental issues?' },
    ],
  },
]

export function getSpeakingSet(id: string | null) {
  return SPEAKING_SETS.find(item => item.id === id) ?? null
}

export function parsePromptIndex(value: string | null) {
  const numeric = Number.parseInt(value ?? '', 10)
  return Number.isFinite(numeric) && numeric >= 0 ? numeric : 0
}

export function clampSpeakingPromptIndex(index: number, set: SpeakingSet | null) {
  if (!set || set.prompts.length === 0) {
    return 0
  }

  return Math.min(Math.max(index, 0), set.prompts.length - 1)
}
