import type { PracticeMode, SmartDimension } from './types'
import { PRACTICE_MODE_LABELS } from '../../constants/practiceModes'

export type PracticeStageGuideTone = 'accent' | 'error' | 'review' | 'focus'
export type PracticeStageGuidePhase = 'challenge' | 'review'

export interface PracticeStageGuideRow {
  label: string
  value: string
}

export interface PracticeStageGuideData {
  levelLabel: string
  laneLabel: string
  phaseLabel: string
  title: string
  context: string
  tone: PracticeStageGuideTone
  rows: PracticeStageGuideRow[]
}

interface LaneDescriptor {
  label: string
  context: string
  tone: PracticeStageGuideTone
}

function buildLevelLabel(queueIndex: number, total: number): string {
  return `第 ${queueIndex + 1} 关 / ${total}`
}

function resolveLane({
  mode,
  errorMode = false,
  reviewMode = false,
}: {
  mode: PracticeMode
  errorMode?: boolean
  reviewMode?: boolean
}): LaneDescriptor {
  if (errorMode) {
    return {
      label: '错词攻坚',
      context: '这关是在回炉你之前答错过的词，目标是把卡点补平。',
      tone: 'error',
    }
  }

  if (reviewMode) {
    return {
      label: '到期复习',
      context: '这关是在对抗遗忘，先把到点词重新拉回可用状态。',
      tone: 'review',
    }
  }

  if (mode === 'smart') {
    return {
      label: '智能强化',
      context: '系统正在抓你当前最容易失分的维度来补短板。',
      tone: 'focus',
    }
  }

  if (mode === 'quickmemory') {
    return {
      label: '新词速记',
      context: `这关先用${PRACTICE_MODE_LABELS.quickmemory}检查你能不能快速认出词义，再决定这词后续要不要进入复习链。`,
      tone: 'accent',
    }
  }

  return {
    label: '新词推进',
    context: '这关是在把新词从“眼熟”推进到“能提取、能分辨、能写出”。',
    tone: 'accent',
  }
}

function buildRows(
  step: string,
  purpose: string,
  outcome: string,
): PracticeStageGuideRow[] {
  return [
    { label: '这一步干什么', value: step },
    { label: '这一步有什么作用', value: purpose },
    { label: '过关后会怎样', value: outcome },
  ]
}

export function buildChoiceStageGuide({
  mode,
  smartDimension = 'meaning',
  queueIndex,
  total,
  errorMode = false,
  reviewMode = false,
  answered = false,
}: {
  mode: PracticeMode
  smartDimension?: SmartDimension
  queueIndex: number
  total: number
  errorMode?: boolean
  reviewMode?: boolean
  answered?: boolean
}): PracticeStageGuideData {
  const lane = resolveLane({ mode, errorMode, reviewMode })
  const levelLabel = buildLevelLabel(queueIndex, total)
  const dimension = mode === 'smart' ? smartDimension : mode

  if (dimension === 'listening') {
    return {
      levelLabel,
      laneLabel: lane.label,
      phaseLabel: answered ? '复盘阶段' : '出题阶段',
      title: answered ? '马上复盘这关的听音误差' : '先听发音，再锁定正确词义',
      context: lane.context,
      tone: lane.tone,
      rows: answered
        ? buildRows(
            '看清这次为什么听对或听错，重点确认刚才混淆的释义。',
            '把“声音听到了但意思接错了”的问题当场纠正，避免下次继续靠猜。',
            '复盘完直接进入下一关，系统会继续追你最薄弱的听力识义点。',
          )
        : buildRows(
            '先听发音，再从选项里选出最准确的中文释义，别先猜拼写。',
            '训练“声音到词义”的直接连接，避免只靠眼熟记住单词。',
            '作答后系统会立刻判定，并把这关结果记到听力维度里。',
          ),
    }
  }

  if (dimension === 'dictation') {
    return {
      levelLabel,
      laneLabel: lane.label,
      phaseLabel: answered ? '复盘阶段' : '出题阶段',
      title: answered ? '核对拼写结果，把错误位置钉住' : '先听再写，别跳过主动拼写',
      context: lane.context,
      tone: lane.tone,
      rows: answered
        ? buildRows(
            '看清自己刚才写错、漏写或多写的字母位置，再继续下一关。',
            '把“会认不会写”的隐性漏洞拆开看清，下一次拼写会更稳。',
            '复盘后直接切到下一关，系统会继续追你拼写最薄弱的位置。',
          )
        : buildRows(
            '根据发音把英文完整写出来，先自己提取，不要等答案提示。',
            '训练从声音到拼写的完整提取链，这是最能暴露假会的关卡。',
            '提交后系统会立刻告诉你哪里写错，并进入针对性的复盘。',
          ),
    }
  }

  return {
    levelLabel,
    laneLabel: lane.label,
    phaseLabel: answered ? '复盘阶段' : '出题阶段',
    title: answered ? '核对回想结果，补上正确提取' : '看释义，主动拼词',
    context: lane.context,
    tone: lane.tone,
      rows: answered
        ? buildRows(
            '对照正确答案，确认自己刚才是完全不会、拼错了，还是只差一点点。',
            `把“只会在${PRACTICE_MODE_LABELS.quickmemory}里认得出”推进到“能在${PRACTICE_MODE_LABELS.meaning}里主动拼出来”，这一步最能避免眼熟假象。`,
            `看清之后进入下一关，系统会继续把词从${PRACTICE_MODE_LABELS.quickmemory}推进到${PRACTICE_MODE_LABELS.meaning}的主动提取。`,
          )
        : buildRows(
            '根据中文释义和词性，直接拼出英文单词，不要依赖选项提示。',
            `把“能在${PRACTICE_MODE_LABELS.quickmemory}里认出来”升级成“能在${PRACTICE_MODE_LABELS.meaning}里主动拼出来”，检验你是不是真的能把词调出来。`,
            '提交后系统会立刻判定；答错时会马上展示正确答案帮助你重建记忆。',
          ),
  }
}

export function buildDictationStageGuide({
  queueIndex,
  total,
  errorMode = false,
  reviewMode = false,
  isExampleMode,
  phase,
  isCorrect = false,
}: {
  queueIndex: number
  total: number
  errorMode?: boolean
  reviewMode?: boolean
  isExampleMode: boolean
  phase: PracticeStageGuidePhase
  isCorrect?: boolean
}): PracticeStageGuideData {
  const lane = resolveLane({ mode: 'dictation', errorMode, reviewMode })
  const levelLabel = buildLevelLabel(queueIndex, total)

  if (phase === 'review') {
    return {
      levelLabel,
      laneLabel: lane.label,
      phaseLabel: '复盘阶段',
      title: isCorrect ? '这关已通过，准备进入下一关' : '别急着跳关，先看清错在哪里',
      context: lane.context,
      tone: lane.tone,
      rows: isCorrect
        ? buildRows(
            '快速确认这次拼写是正确的，然后直接推进到下一词。',
            '让正确路径刚建立时就被再次确认，记忆会更牢固。',
            '进入下一关后系统会继续保持同样的拼写强度。',
          )
        : buildRows(
            '看清自己是听漏了、字母顺序错了，还是根本没抓住这个词。',
            `把错误拆到字母层级，才能真正修复“能做${PRACTICE_MODE_LABELS.listening}却还过不了${PRACTICE_MODE_LABELS.dictation}”的问题。`,
            '复盘完继续下一关，系统会保留这次失误作为后续强化依据。',
          ),
    }
  }

  return {
    levelLabel,
    laneLabel: lane.label,
    phaseLabel: '出题阶段',
    title: isExampleMode ? '先听例句，再补全空缺词' : '先听发音，再完整拼出单词',
    context: lane.context,
    tone: lane.tone,
    rows: isExampleMode
      ? buildRows(
          '先听整句语境，再把空缺位置对应的单词写出来。',
          '让你不只记住单词本身，还能知道它在真实语境里怎么出现。',
          '提交后系统会告诉你拼写是否准确，答错会直接标出问题位置。',
        )
      : buildRows(
          '只根据发音把单词写完整，先自己提取，不要等答案出现。',
          '训练从声音到字母的完整输出链，最容易揪出“会认不会写”的问题。',
          '提交后系统会立刻进入复盘，把错字和漏字直接摊开给你看。',
        ),
  }
}

export function buildQuickMemoryStageGuide({
  queueIndex,
  total,
  reviewMode = false,
  errorMode = false,
  phase,
  choice = null,
}: {
  queueIndex: number
  total: number
  reviewMode?: boolean
  errorMode?: boolean
  phase: PracticeStageGuidePhase
  choice?: 'known' | 'unknown' | null
}): PracticeStageGuideData {
  const lane = resolveLane({ mode: 'quickmemory', reviewMode, errorMode })
  const levelLabel = buildLevelLabel(queueIndex, total)

  if (phase === 'review') {
    return {
      levelLabel,
      laneLabel: lane.label,
      phaseLabel: '复盘阶段',
      title: choice === 'unknown' ? '立刻复盘，把陌生词钉住' : '确认这词是真的认识，不是碰巧眼熟',
      context: lane.context,
      tone: lane.tone,
      rows: choice === 'unknown'
        ? buildRows(
            '核对音标、词性和释义，马上把这词的正确信息补完整。',
            '在判断“不认识”之后立刻补记忆，能防止陌生印象继续发散。',
            '进入下一关时，这个词会被系统安排进后续复习链，继续追踪你有没有真正记住。',
          )
        : buildRows(
            '快速确认释义和音标，再进入下一关，不用在这词上停太久。',
            `防止把“似曾相识”误判成“已经掌握”，把${PRACTICE_MODE_LABELS.quickmemory}的判断做得更干净。`,
            `进入下一关后，系统会继续根据你的${PRACTICE_MODE_LABELS.quickmemory}状态调整后续复习压力。`,
          ),
    }
  }

  return {
    levelLabel,
    laneLabel: lane.label,
    phaseLabel: '出题阶段',
    title: '先快速判断，别在这一关想太久',
    context: lane.context,
    tone: lane.tone,
    rows: buildRows(
      '看见单词后，4 秒内判断自己是“认识”还是“不认识”，先做直觉判断。',
      `先把词按${PRACTICE_MODE_LABELS.quickmemory}的熟悉度分层，系统才能决定哪些词该立即回炉、哪些词可以放缓复习。`,
      '选完后会立刻展示音标和释义，再带你进入下一关继续闯。',
    ),
  }
}
