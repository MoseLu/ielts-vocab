import React from 'react'
import { Animated, Easing, Image, Pressable, StyleSheet, Text, View } from 'react-native'
import { PRACTICE_MODE_LABELS, type PracticeMode } from '@ielts-vocab/app-core'
import { loadLearningStats, peekLearningStats } from '../api/learnerApi'
import { ArtTextFrame } from '../components/ArtTextFrame'
import { Sticker } from '../components/stickers'
import type { StickerKey } from '../components/stickers/catalog'
import { todayMasteredWordsFromStats } from '../lib/learningStats'
import { theme } from '../theme'
import { PracticeCenterIcon } from './PracticeCenterIcon'

type PracticeActionMenuProps = {
  onDismiss: () => void
  onSelect: (mode: PracticeMode) => void
}

const shortcutModes: PracticeMode[] = ['test', 'listening', 'follow', 'quickmemory', 'dictation', 'meaning', 'smart', 'radio']
const quickActionLabels: Record<PracticeMode, string> = {
  dictation: '听写',
  errors: '错词',
  follow: '跟读',
  listening: '听音',
  meaning: '默写',
  quickmemory: '速记',
  radio: '随身听',
  smart: '智能',
  test: '测试',
}
const modeStickerKeys: Record<PracticeMode, StickerKey> = {
  dictation: 'practiceModeDictation',
  errors: 'wrongWordSticky',
  follow: 'practiceModeFollow',
  listening: 'practiceModeListening',
  meaning: 'practiceModeMeaning',
  quickmemory: 'practiceModeQuickMemory',
  radio: 'practiceModeRadio',
  smart: 'practiceModeSmart',
  test: 'practiceModeTest',
}
const practiceHeroTutor = require('../assets/stickers/practice-hero-tutor.png')
const practiceStatRibbon = require('../assets/stickers/practice-stat-ribbon.png')
const ORBIT_ACTION_WIDTH = 64
const QUICK_ACTION_CENTER_BOTTOM = 18
const QUICK_ACTION_ORBIT_BOTTOM = 86
const TRIANGLE_NODE_SPACING = 88
const TRIANGLE_ROW_HEIGHT = Math.round((TRIANGLE_NODE_SPACING * Math.sqrt(3)) / 2)
const TRIANGLE_BASE_ROW_BOTTOM = 0

function triangleNode(mode: PracticeMode, rowFromBase: number, columnOffset: number) {
  return {
    bottom: TRIANGLE_BASE_ROW_BOTTOM + ((rowFromBase - 1) * TRIANGLE_ROW_HEIGHT),
    mode,
    translateX: Math.round((columnOffset * TRIANGLE_NODE_SPACING) - (ORBIT_ACTION_WIDTH / 2)),
  }
}

const orbitLayout: Array<{ bottom: number; mode: PracticeMode; translateX: number }> = [
  triangleNode('smart', 1, -1),
  triangleNode('radio', 1, 1),
  triangleNode('quickmemory', 2, -1),
  triangleNode('dictation', 2, 0),
  triangleNode('meaning', 2, 1),
  triangleNode('listening', 3, -0.5),
  triangleNode('follow', 3, 0.5),
  triangleNode('test', 4, 0),
]
const LEFT_TO_RIGHT_REVEAL_ORDER = new Map(
  [...orbitLayout]
    .sort((left, right) => (left.translateX === right.translateX ? left.bottom - right.bottom : left.translateX - right.translateX))
    .map((item, index) => [item.mode, index] as const),
)

function layoutForMode(mode: PracticeMode) {
  return orbitLayout.find(item => item.mode === mode) ?? orbitLayout[0]
}

function orbitStyle(mode: PracticeMode) {
  const layout = layoutForMode(mode)
  return {
    bottom: layout.bottom,
  }
}

function modeRevealStyle(mode: PracticeMode, reveal: Animated.Value) {
  const layout = layoutForMode(mode)
  const order = LEFT_TO_RIGHT_REVEAL_ORDER.get(mode) ?? 0
  const start = order * 0.09
  const end = start + 0.34
  return {
    opacity: reveal.interpolate({
      extrapolate: 'clamp',
      inputRange: [start, end],
      outputRange: [0, 1],
    }),
    transform: [
      { translateX: layout.translateX },
      {
        translateY: reveal.interpolate({
          extrapolate: 'clamp',
          inputRange: [start, end],
          outputRange: [20, 0],
        }),
      },
      {
        scale: reveal.interpolate({
          extrapolate: 'clamp',
          inputRange: [start, end],
          outputRange: [0.82, 1],
        }),
      },
    ],
  }
}

export function PracticeActionMenu({ onDismiss, onSelect }: PracticeActionMenuProps) {
  const reveal = React.useRef(new Animated.Value(0)).current
  const closingRef = React.useRef(false)
  const [todayMasteredWords, setTodayMasteredWords] = React.useState(() => {
    const cached = peekLearningStats()
    return cached ? todayMasteredWordsFromStats(cached) : 0
  })

  React.useEffect(() => {
    const opening = Animated.timing(reveal, {
      duration: 720,
      easing: Easing.out(Easing.cubic),
      toValue: 1,
      useNativeDriver: true,
    })
    opening.start()
    return () => opening.stop()
  }, [reveal])

  React.useEffect(() => {
    let active = true
    loadLearningStats()
      .then(stats => {
        if (active) setTodayMasteredWords(todayMasteredWordsFromStats(stats))
      })
      .catch(() => {
        if (active) setTodayMasteredWords(0)
      })
    return () => {
      active = false
    }
  }, [])

  const dismissWithAnimation = React.useCallback(() => {
    if (closingRef.current) return
    closingRef.current = true
    Animated.timing(reveal, {
      duration: 260,
      easing: Easing.in(Easing.quad),
      toValue: 0,
      useNativeDriver: true,
    }).start(() => onDismiss())
  }, [onDismiss, reveal])

  const centerRotate = reveal.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '90deg'],
  })
  const heroOpacity = reveal.interpolate({
    extrapolate: 'clamp',
    inputRange: [0.12, 0.42],
    outputRange: [0, 1],
  })
  const heroTranslateY = reveal.interpolate({
    extrapolate: 'clamp',
    inputRange: [0.12, 0.42],
    outputRange: [8, 0],
  })
  const displayedTodayMasteredWords = Math.max(0, Math.round(todayMasteredWords))

  return (
    <View style={styles.overlay} testID="practice.quickAction.fullscreen">
      <Animated.View pointerEvents="none" style={[styles.overlayBackground, { opacity: reveal }]} />
      <Pressable
        accessibilityLabel="关闭练习快捷菜单"
        accessibilityRole="button"
        onPress={dismissWithAnimation}
        style={styles.backdrop}
        testID="practice.quickAction.backdrop"
      />

      <Animated.View
        pointerEvents="none"
        style={[styles.hero, { opacity: heroOpacity, transform: [{ translateY: heroTranslateY }] }]}
        testID="practice.quickAction.content"
      >
        <View style={styles.heroScene}>
          <ArtTextFrame contentStyle={styles.ribbonTextWrap} height={107} resizeMode="contain" source={practiceStatRibbon} style={styles.heroRibbon} width={408}>
              <Text numberOfLines={1} style={[styles.ribbonText, styles.ribbonTextPrefix]}>今日掌握</Text>
              <View style={styles.ribbonNumberSlot}>
                <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} style={styles.ribbonNumber}>
                  {displayedTodayMasteredWords}
                </Text>
              </View>
              <Text numberOfLines={1} style={[styles.ribbonText, styles.ribbonTextSuffix]}>词</Text>
          </ArtTextFrame>
          <Image resizeMode="contain" source={practiceHeroTutor} style={styles.heroTutorCentered} />
          <View style={styles.modePrompt} testID="practice.quickAction.modePrompt">
            <View style={styles.modePromptRule} />
            <View style={styles.modePromptBadge}>
              <View style={styles.modePromptDot} />
              <Text style={styles.modePromptText}>模式选择</Text>
              <View style={styles.modePromptDot} />
            </View>
            <View style={styles.modePromptRule} />
          </View>
        </View>
      </Animated.View>

      <View pointerEvents="box-none" style={[styles.orbitStage, { bottom: QUICK_ACTION_ORBIT_BOTTOM }]}>
        <View pointerEvents="none" style={styles.orbitGuide} />
        {shortcutModes.map(mode => (
          <Animated.View key={mode} style={[styles.orbitAction, orbitStyle(mode), modeRevealStyle(mode, reveal)]}>
            <Pressable
              accessibilityLabel={`快捷练习-${PRACTICE_MODE_LABELS[mode]}`}
              accessibilityRole="button"
              onPress={() => onSelect(mode)}
              style={({ pressed }) => [styles.orbitActionButton, pressed ? styles.actionPressed : null]}
              testID={`practice.quickAction.${mode}`}
            >
              <View style={styles.iconShell}>
                <Sticker height={30} keyName={modeStickerKeys[mode]} width={30} />
              </View>
              <Text numberOfLines={1} style={styles.actionLabel}>{quickActionLabels[mode]}</Text>
            </Pressable>
          </Animated.View>
        ))}
      </View>

      <Animated.View style={[styles.centerButton, { bottom: QUICK_ACTION_CENTER_BOTTOM, transform: [{ translateX: -29 }, { rotate: centerRotate }] }]}>
        <Pressable
          accessibilityLabel="关闭练习快捷菜单"
          accessibilityRole="button"
          onPress={dismissWithAnimation}
          style={({ pressed }) => [styles.centerButtonHit, pressed ? styles.centerButtonPressed : null]}
          testID="practice.quickAction.center"
        >
          <PracticeCenterIcon open />
        </Pressable>
      </Animated.View>
    </View>
  )
}

const styles = StyleSheet.create({
  actionLabel: {
    color: theme.colors.text,
    fontSize: 10,
    fontWeight: '900',
    lineHeight: 13,
    maxWidth: 60,
    paddingHorizontal: 6,
    paddingVertical: 2,
    textAlign: 'center',
  },
  actionPressed: {
    opacity: 0.78,
  },
  centerButton: {
    alignItems: 'center',
    backgroundColor: 'transparent',
    borderColor: 'transparent',
    borderRadius: 29,
    borderWidth: 0,
    height: 58,
    justifyContent: 'center',
    left: '50%',
    position: 'absolute',
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 5, width: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    width: 58,
    zIndex: 45,
    elevation: 0,
  },
  centerButtonHit: {
    alignItems: 'center',
    height: '100%',
    justifyContent: 'center',
    width: '100%',
  },
  centerButtonPressed: {
    opacity: 0.82,
  },
  hero: {
    alignItems: 'center',
    paddingHorizontal: theme.spacing.lg,
    paddingTop: 135,
  },
  heroScene: {
    alignItems: 'center',
  },
  heroTutorCentered: {
    height: 246,
    marginTop: -theme.spacing.xs,
    width: 214,
  },
  iconShell: {
    alignItems: 'center',
    height: 46,
    justifyContent: 'center',
    width: 46,
  },
  orbitAction: {
    left: '50%',
    position: 'absolute',
    width: ORBIT_ACTION_WIDTH,
  },
  orbitActionButton: {
    alignItems: 'center',
    gap: 3,
    width: ORBIT_ACTION_WIDTH,
  },
  modePrompt: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    marginTop: -theme.spacing.xs,
  },
  modePromptBadge: {
    alignItems: 'center',
    backgroundColor: 'rgba(255, 246, 229, 0.96)',
    borderColor: '#E7A068',
    borderRadius: theme.radius.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 7,
    paddingHorizontal: 14,
    paddingVertical: 5,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 3, width: 0 },
    shadowOpacity: 0.08,
    shadowRadius: 7,
    elevation: 2,
  },
  modePromptDot: {
    backgroundColor: '#F09B51',
    borderRadius: 3,
    height: 6,
    width: 6,
  },
  modePromptRule: {
    backgroundColor: '#E7A068',
    borderRadius: theme.radius.pill,
    height: 2,
    opacity: 0.7,
    width: 34,
  },
  modePromptText: {
    color: '#7B5541',
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 1.4,
    lineHeight: 18,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 35,
  },
  overlayBackground: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#FFFDF0',
  },
  ribbonNumber: {
    color: '#C3551C',
    fontSize: 30,
    fontWeight: '900',
    height: 44,
    includeFontPadding: false,
    lineHeight: 44,
    minWidth: 80,
    textAlign: 'center',
    textAlignVertical: 'center',
  },
  ribbonNumberSlot: {
    alignItems: 'center',
    justifyContent: 'center',
    marginHorizontal: 10,
    width: 94,
  },
  ribbonText: {
    color: '#6E4934',
    fontSize: 16,
    fontWeight: '900',
    height: 44,
    includeFontPadding: false,
    lineHeight: 44,
    textAlign: 'left',
    textAlignVertical: 'center',
  },
  ribbonTextPrefix: {
    textAlign: 'right',
  },
  ribbonTextSuffix: {
    textAlign: 'left',
  },
  ribbonTextWrap: {
    alignItems: 'center',
    bottom: 0,
    flexDirection: 'row',
    height: '100%',
    justifyContent: 'center',
    left: 0,
    paddingTop: 0,
    position: 'absolute',
    right: 0,
    top: 0,
    width: '100%',
  },
  heroRibbon: {
    alignItems: 'center',
    height: 107,
    justifyContent: 'center',
    marginBottom: -theme.spacing.md,
    width: 408,
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'transparent',
  },
  orbitGuide: {
    alignSelf: 'center',
    backgroundColor: 'transparent',
    borderColor: 'transparent',
    borderRadius: 250,
    borderWidth: 1,
    bottom: 0,
    height: 500,
    position: 'absolute',
    width: 340,
  },
  orbitStage: {
    height: 430,
    left: 0,
    position: 'absolute',
    right: 0,
  },
})
