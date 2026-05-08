import React, { useState } from 'react'
import { Modal, Pressable, Text, View } from 'react-native'
import { X, type LucideIcon } from 'lucide-react-native'
import { CompanionCatArt, ScrollNote } from './CompanionDecor'
import { StickerLayer, studyRoomFeedbackStickerSlots, studyRoomStickerSlots } from './stickers'
import { styles } from './StudyRoomScene.styles'
import type { NavigateOptions, ScreenKey } from '../navigation/types'
import { theme } from '../theme'

export type StudyRoomObject = {
  Icon: LucideIcon
  ctaLabel: string
  hint: string
  key: string
  label: string
  options?: NavigateOptions
  screen: ScreenKey
  tone: 'blue' | 'green' | 'orange' | 'pink' | 'purple' | 'red'
  value: string
}

export type StudyRoomTodo = {
  ctaLabel: string
  subtitle: string
  title: string
}

type StudyRoomPlan = {
  examDateLabel: string
  targetScore: string
  weakAreas: string[]
}

type Props = {
  learnedWords: number
  onNavigate: (screen: ScreenKey, options?: NavigateOptions) => void
  onTodoPress: (index: number) => void
  plan: StudyRoomPlan
  progress: number
  remainingWords: number
  roomObjects: StudyRoomObject[]
  todos: StudyRoomTodo[]
  totalWords: number
  wrongWords: number
}

const toneStyles = {
  blue: {
    bg: theme.colors.infoSoft,
    color: theme.colors.info,
  },
  green: {
    bg: theme.colors.primarySoft,
    color: theme.colors.primaryDark,
  },
  orange: {
    bg: theme.colors.accentSoft,
    color: theme.colors.accentDark,
  },
  pink: {
    bg: theme.colors.roseSoft,
    color: theme.colors.rose,
  },
  purple: {
    bg: theme.colors.purpleSoft,
    color: theme.colors.purple,
  },
  red: {
    bg: theme.colors.dangerSoft,
    color: theme.colors.danger,
  },
} as const

export function StudyRoomScene({
  learnedWords,
  onNavigate,
  onTodoPress,
  plan,
  progress,
  remainingWords,
  roomObjects,
  todos,
  totalWords,
  wrongWords,
}: Props) {
  const [activeObject, setActiveObject] = useState<StudyRoomObject | null>(null)
  const primaryObjects = roomObjects.slice(0, 5)
  const railObjects = roomObjects.slice(5, 8)
  const challengeObject = roomObjects.find(object => object.key === 'challenge')
  const letterObject = roomObjects.find(object => object.key === 'ai-letter')
  const proPlanObject = roomObjects.find(object => object.key === 'pro-plan')

  function go(object: StudyRoomObject) {
    setActiveObject(null)
    onNavigate(object.screen, object.options)
  }

  return (
    <>
      <View style={styles.scene}>
        <StickerLayer slots={studyRoomStickerSlots} />
        <View style={styles.pawOne} />
        <View style={styles.pawTwo} />
        <Pressable accessibilityRole="button" onPress={() => challengeObject && setActiveObject(challengeObject)} style={styles.challengeBanner}>
          <Text style={styles.challengeText}>挑战赛</Text>
        </Pressable>
        <Pressable accessibilityRole="button" onPress={() => letterObject && setActiveObject(letterObject)} style={styles.hangingLetter}>
          <Text style={styles.letterHeart}>♥</Text>
        </Pressable>
        <View style={styles.rightRail}>
          {railObjects.map(object => {
            const tone = toneStyles[object.tone]
            return (
              <Pressable accessibilityRole="button" key={object.key} onPress={() => setActiveObject(object)} style={styles.railItem}>
                <object.Icon color={tone.color} size={20} strokeWidth={2.5} />
                <Text style={styles.railLabel}>{object.label}</Text>
              </Pressable>
            )
          })}
        </View>
        <View style={styles.catSpot}>
          <CompanionCatArt size={156} variant={wrongWords ? 'worried' : 'idle'} />
          <View style={styles.catSpeech}>
            <Text style={styles.catSpeechText}>{wrongWords ? `${wrongWords} 个错词待安抚` : '今天很清爽'}</Text>
          </View>
        </View>
        <View style={styles.studyDesk}>
          {primaryObjects.map(object => {
            const tone = toneStyles[object.tone]
            return (
              <Pressable accessibilityRole="button" key={object.key} onPress={() => setActiveObject(object)} style={styles.roomObject}>
                <View style={[styles.objectIcon, { backgroundColor: tone.bg }]}>
                  <object.Icon color={tone.color} size={22} strokeWidth={2.5} />
                </View>
                <Text numberOfLines={1} style={styles.objectLabel}>{object.label}</Text>
              </Pressable>
            )
          })}
        </View>
        {proPlanObject ? (
          <Pressable accessibilityRole="button" onPress={() => setActiveObject(proPlanObject)} style={styles.vipSticker}>
            <Text style={styles.vipStickerTiny}>IELTS Pro</Text>
            <Text style={styles.vipStickerText}>冲刺计划</Text>
          </Pressable>
        ) : null}
      </View>

      <View style={styles.roomStats}>
        <View style={styles.roomStatCell}>
          <Text style={styles.roomStatValue}>{learnedWords}</Text>
          <Text style={styles.roomStatLabel}>已学</Text>
        </View>
        <View style={styles.roomStatCell}>
          <Text style={styles.roomStatValue}>{totalWords}</Text>
          <Text style={styles.roomStatLabel}>总词</Text>
        </View>
        <View style={styles.roomStatCell}>
          <Text style={styles.roomStatValue}>{remainingWords}</Text>
          <Text style={styles.roomStatLabel}>待攻克</Text>
        </View>
      </View>

      <ScrollNote
        title={`猫咪卷轴 · IELTS ${plan.targetScore}`}
        caption={`${plan.examDateLabel}考试，今日建议先清复习，再补新词。弱项：${plan.weakAreas.join(' / ')}。`}
      />

      <View style={styles.planTicket}>
        <View>
          <Text style={styles.ticketEyebrow}>今日房间任务</Text>
          <Text style={styles.ticketTitle}>{progress ? `学习进度 ${progress}%` : '从第一组新词开始'}</Text>
        </View>
        <Pressable accessibilityRole="button" onPress={() => onNavigate('practice', { mode: 'smart' })} style={styles.ticketButton}>
          <Text style={styles.ticketButtonText}>开始</Text>
        </Pressable>
      </View>

      {todos.slice(0, 3).map((todo, index) => (
        <Pressable accessibilityRole="button" key={`${todo.title}-${index}`} onPress={() => onTodoPress(index)} style={styles.todoTicket}>
          <Text style={styles.todoIndex}>{String(index + 1).padStart(2, '0')}</Text>
          <View style={styles.todoCopy}>
            <Text numberOfLines={1} style={styles.todoTitle}>{todo.title || '学习任务'}</Text>
            <Text numberOfLines={2} style={styles.todoSubtitle}>{todo.subtitle || '系统推荐的下一步学习动作。'}</Text>
          </View>
          <Text style={styles.todoCta}>{todo.ctaLabel}</Text>
        </Pressable>
      ))}

      <Modal animationType="slide" onRequestClose={() => setActiveObject(null)} transparent visible={Boolean(activeObject)}>
        <View style={styles.modalRoot}>
          <Pressable accessibilityRole="button" onPress={() => setActiveObject(null)} style={styles.modalBackdrop} />
          {activeObject ? (
            <View style={styles.feedbackSheet}>
              <StickerLayer slots={studyRoomFeedbackStickerSlots} />
              <Pressable accessibilityLabel="关闭" accessibilityRole="button" onPress={() => setActiveObject(null)} style={styles.closeButton}>
                <X color={theme.colors.muted} size={18} strokeWidth={2.4} />
              </Pressable>
              <CompanionCatArt size={82} variant="celebrate" />
              <Text style={styles.feedbackTitle}>{activeObject.label}</Text>
              <Text style={styles.feedbackValue}>{activeObject.value}</Text>
              <Text style={styles.feedbackHint}>{activeObject.hint}</Text>
              <Pressable accessibilityRole="button" onPress={() => go(activeObject)} style={styles.feedbackButton}>
                <Text style={styles.feedbackButtonText}>{activeObject.ctaLabel}</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      </Modal>
    </>
  )
}
