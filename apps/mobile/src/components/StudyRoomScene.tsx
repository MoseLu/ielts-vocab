import React from 'react'
import { Animated, Easing, Image, ImageBackground, PanResponder, Pressable, StatusBar, Text, useWindowDimensions, View } from 'react-native'
import { ArtTextFrame } from './ArtTextFrame'
import { ScrollNote } from './CompanionDecor'
import { Card } from './primitives'
import { Sticker, type StickerKey } from './stickers'
import { styles } from './StudyRoomScene.styles'
import type { NavigateOptions, ScreenKey } from '../navigation/types'

const homeHeaderAi = require('../assets/stickers/home-header-ai.png')
const homeHeaderSearch = require('../assets/stickers/home-header-search.png')
const homeSpeechBubble = require('../assets/stickers/study-room-speech-bubble.png')
const studyRoomWideWallpaper = require('../assets/stickers/study-room-wide-wallpaper.png')
const HERO_BOARD_ASPECT_RATIO = 1114 / 1391
const HERO_BOARD_CLOSED_HEIGHT_RATIO = 0.14
const HERO_BOARD_UNFOLD_DURATION_MS = 1600
const WIDE_WALLPAPER_ASPECT_RATIO = 1923 / 818
const WIDE_WALLPAPER_MIN_PAN = 96
const SCENE_TOP_INSET = Math.max((StatusBar.currentHeight ?? 0) - 10, 0)
const SCENE_BOARD_TOP = 60 + SCENE_TOP_INSET
const SCENE_BOTTOM_PADDING = 8
const SCENE_ROW_GAP = 2
const SCENE_SPEECH_ROW_HEIGHT = 92
const SCENE_SPEECH_TOP_OFFSET = 16

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(value, max))
}

export type StudyRoomObject = {
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
  heroAction: StudyRoomObject
  onNavigate: (screen: ScreenKey, options?: NavigateOptions) => void
  sideEntries: StudyRoomObject[]
  wrongWords: number
}

const sideEntryArt: Record<string, StickerKey> = {
  'practice-yard': 'studyBadgePractice',
  'todo-list': 'studyBadgeTodo',
  'wrong-kit': 'studyBadgeWrong',
}

function formatSideEntryBadge(entry: StudyRoomObject): string {
  if (entry.key === 'practice-yard') return '练'
  const numberMatch = entry.value.match(/\d+/)
  if (numberMatch) return numberMatch[0]
  return entry.value.slice(0, 2)
}

function SideEntryArt({
  badge,
  entryKey,
  label,
  artKey,
}: {
  artKey: StickerKey
  badge: string
  entryKey: string
  label: string
}) {
  const labelFrameStyle = [
    styles.iconEntryLabelFrame,
    entryKey === 'wrong-kit' ? styles.iconEntryLabelFrameWrong : null,
    entryKey === 'todo-list' ? styles.iconEntryLabelFrameTodo : null,
  ]
  const badgeStyle = [
    styles.iconBadge,
    entryKey === 'wrong-kit' ? styles.iconBadgeWrong : null,
    entryKey === 'todo-list' ? styles.iconBadgeTodo : null,
  ]

  return (
    <View style={styles.iconBubble}>
      <Sticker height={102} keyName={artKey} width={90} />
      {badge ? (
        <View style={badgeStyle}>
          <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} style={styles.iconBadgeText}>{badge}</Text>
        </View>
      ) : null}
      <View pointerEvents="none" style={labelFrameStyle}>
        <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} style={styles.iconEntryLabel}>{label}</Text>
      </View>
    </View>
  )
}

export function StudyRoomScene({
  heroAction,
  onNavigate,
  sideEntries,
  wrongWords,
}: Props) {
  const { height, width } = useWindowDimensions()
  const [sceneHeight, setSceneHeight] = React.useState(0)
  const layoutHeight = Math.max(sceneHeight || height, 420)
  const wallpaperWidth = Math.max(layoutHeight * WIDE_WALLPAPER_ASPECT_RATIO, width + WIDE_WALLPAPER_MIN_PAN * 2)
  const minWallpaperTranslateX = Math.min(width - wallpaperWidth, 0)
  const centeredWallpaperTranslateX = clamp((width - wallpaperWidth) / 2, minWallpaperTranslateX, 0)
  const viewportStageLeft = -centeredWallpaperTranslateX
  const wallpaperTranslateX = React.useRef(new Animated.Value(centeredWallpaperTranslateX)).current
  const wallpaperOffsetXRef = React.useRef(centeredWallpaperTranslateX)
  const boardWidth = clamp(width - 118, 220, 310)
  const roomWidth = Math.min(width + 108, 520)
  const naturalRoomHeight = roomWidth * 0.67
  const boardMinHeight = Math.max(170, boardWidth * HERO_BOARD_ASPECT_RATIO * 0.72)
  let roomHeight = clamp(layoutHeight * 0.39, 190, naturalRoomHeight)
  let roomTop = layoutHeight - SCENE_BOTTOM_PADDING - roomHeight
  let speechTop = roomTop - SCENE_SPEECH_ROW_HEIGHT - SCENE_ROW_GAP
  let boardHeight = speechTop - SCENE_BOARD_TOP - SCENE_ROW_GAP
  if (boardHeight < boardMinHeight) {
    roomHeight = Math.max(160, roomHeight - (boardMinHeight - boardHeight))
    roomTop = layoutHeight - SCENE_BOTTOM_PADDING - roomHeight
    speechTop = roomTop - SCENE_SPEECH_ROW_HEIGHT - SCENE_ROW_GAP
    boardHeight = Math.max(140, speechTop - SCENE_BOARD_TOP - SCENE_ROW_GAP)
  }
  const boardContentPaddingTop = clamp(boardHeight * 0.2, 42, 74)
  const boardContentPaddingBottom = clamp(boardHeight * 0.29, 62, 100)
  const boardContentPaddingHorizontal = clamp(boardWidth * 0.15, 32, 46)
  const boardContentTranslateX = -clamp(boardWidth * 0.035, 7, 11)
  const boardReveal = React.useRef(new Animated.Value(HERO_BOARD_CLOSED_HEIGHT_RATIO)).current
  const boardRevealHeight = boardReveal.interpolate({
    inputRange: [HERO_BOARD_CLOSED_HEIGHT_RATIO, 1],
    outputRange: [boardHeight * HERO_BOARD_CLOSED_HEIGHT_RATIO, boardHeight],
  })
  const boardContentOpacity = boardReveal.interpolate({
    inputRange: [HERO_BOARD_CLOSED_HEIGHT_RATIO, 0.72, 1],
    outputRange: [0, 0, 1],
  })
  React.useEffect(() => {
    wallpaperOffsetXRef.current = centeredWallpaperTranslateX
    wallpaperTranslateX.setValue(centeredWallpaperTranslateX)
  }, [centeredWallpaperTranslateX, wallpaperTranslateX])

  const wallpaperPanResponder = React.useMemo(
    () => PanResponder.create({
      onMoveShouldSetPanResponder: (_event, gestureState) => {
        const horizontalDrag = Math.abs(gestureState.dx)
        const verticalDrag = Math.abs(gestureState.dy)
        return horizontalDrag > 8 && horizontalDrag > verticalDrag * 1.1
      },
      onPanResponderMove: (_event, gestureState) => {
        wallpaperTranslateX.setValue(clamp(wallpaperOffsetXRef.current + gestureState.dx, minWallpaperTranslateX, 0))
      },
      onPanResponderRelease: (_event, gestureState) => {
        wallpaperOffsetXRef.current = clamp(wallpaperOffsetXRef.current + gestureState.dx, minWallpaperTranslateX, 0)
        wallpaperTranslateX.setValue(wallpaperOffsetXRef.current)
      },
      onPanResponderTerminate: (_event, gestureState) => {
        wallpaperOffsetXRef.current = clamp(wallpaperOffsetXRef.current + gestureState.dx, minWallpaperTranslateX, 0)
        wallpaperTranslateX.setValue(wallpaperOffsetXRef.current)
      },
    }),
    [minWallpaperTranslateX, wallpaperTranslateX],
  )

  React.useEffect(() => {
    const unfoldAnimation = Animated.timing(boardReveal, {
      duration: HERO_BOARD_UNFOLD_DURATION_MS,
      easing: Easing.inOut(Easing.cubic),
      toValue: 1,
      useNativeDriver: false,
    })
    unfoldAnimation.start()
    return () => unfoldAnimation.stop()
  }, [boardReveal])

  function go(object: StudyRoomObject) {
    onNavigate(object.screen, object.options)
  }

  return (
    <View onLayout={event => setSceneHeight(event.nativeEvent.layout.height)} style={styles.scene}>
      <Animated.View
        {...wallpaperPanResponder.panHandlers}
        style={[styles.sceneDraggableStage, {
          height: layoutHeight,
          transform: [{ translateX: wallpaperTranslateX }],
          width: wallpaperWidth,
        }]}
        testID="home.scene.drag"
      >
        <Image
          resizeMode="stretch"
          source={studyRoomWideWallpaper}
          style={[styles.sceneWideWallpaper, {
            height: layoutHeight,
            width: wallpaperWidth,
          }]}
          testID="home.wallpaper.drag"
        />
        <View
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
          pointerEvents="none"
          style={{
            bottom: SCENE_BOTTOM_PADDING,
            left: viewportStageLeft + 18,
            opacity: 0,
            position: 'absolute',
            top: SCENE_BOARD_TOP,
            width: width - 36,
          }}
          testID="home.layout-guide"
        >
          <View style={{ height: boardHeight }} />
          <View style={{ height: SCENE_ROW_GAP }} />
          <View style={{ height: SCENE_SPEECH_ROW_HEIGHT }} />
          <View style={{ height: SCENE_ROW_GAP }} />
          <View style={{ height: roomHeight }} />
        </View>
        <Animated.View style={[styles.heroBoard, { height: boardRevealHeight, left: viewportStageLeft + 18, overflow: 'hidden', paddingHorizontal: 0, paddingTop: 0, top: SCENE_BOARD_TOP, width: boardWidth }]}>
          <ArtTextFrame
            contentInsets={{
              bottom: boardContentPaddingBottom,
              left: boardContentPaddingHorizontal,
              right: boardContentPaddingHorizontal,
              top: boardContentPaddingTop,
            }}
            contentStyle={[styles.heroBoardContent, { opacity: boardContentOpacity, transform: [{ translateX: boardContentTranslateX }] }]}
            height={boardHeight}
            resizeMode="stretch"
            sticker="studyHeroBoard"
            testID="home.hero.artTextFrame"
            width={boardWidth}
          >
            <Text style={styles.heroEyebrow}>今日主线</Text>
            <Text numberOfLines={2} style={styles.heroTitle}>{heroAction.label}</Text>
            <Text numberOfLines={2} style={styles.heroHint}>{heroAction.hint}</Text>
            <View style={styles.heroRewardPlaque} testID="home.hero.rewardPlaque">
              <Sticker height={26} keyName="treasureBox" style={styles.heroRewardIcon} width={26} />
              <View style={styles.heroRewardCopy}>
                <Text style={styles.heroRewardLabel}>行动铭牌</Text>
                <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} style={styles.heroRewardValue}>{heroAction.value}</Text>
              </View>
            </View>
          </ArtTextFrame>
          <Pressable accessibilityLabel="继续今日学习" accessibilityRole="button" onPress={() => go(heroAction)} style={styles.heroButton} testID="home.hero.continue">
            <Text style={styles.heroButtonText}>{heroAction.ctaLabel}</Text>
          </Pressable>
        </Animated.View>
        <Sticker height={roomHeight} keyName="studyLoungeRoom" style={[styles.roomSceneArt, { left: viewportStageLeft + (width - roomWidth) / 2, top: roomTop }]} width={roomWidth} />
        <View style={[styles.roomSpeech, { left: viewportStageLeft + 44, top: speechTop + SCENE_SPEECH_TOP_OFFSET }]}>
          <ImageBackground resizeMode="stretch" source={homeSpeechBubble} style={styles.roomSpeechBubble}>
            <Text numberOfLines={3} style={styles.roomSpeechText}>{wrongWords ? `${wrongWords} 个错词待安抚，先从错词本清一组。` : '橘光洒满书桌，先完成一组主线任务吧。'}</Text>
          </ImageBackground>
        </View>
      </Animated.View>
      <View style={styles.sceneHeader}>
        <View style={styles.sceneHeaderActions}>
          <Pressable accessibilityLabel="全局查词" accessibilityRole="button" onPress={() => onNavigate('search')} style={styles.sceneHeaderButton} testID="home.header.search">
            <Image resizeMode="contain" source={homeHeaderSearch} style={[styles.sceneHeaderIcon, styles.sceneHeaderSearchIcon]} />
          </Pressable>
          <Pressable accessibilityLabel="AI 助手" accessibilityRole="button" onPress={() => onNavigate('ai')} style={styles.sceneHeaderButton} testID="home.header.ai">
            <Image resizeMode="contain" source={homeHeaderAi} style={[styles.sceneHeaderIcon, styles.sceneHeaderAiIcon]} />
          </Pressable>
        </View>
      </View>
      <View style={[styles.iconDock, { top: SCENE_BOARD_TOP }]}>
        <Sticker height={70} keyName="studyDecorMascot" width={72} />
        {sideEntries.map(object => {
          const badge = formatSideEntryBadge(object)
          const artKey = sideEntryArt[object.key] ?? 'studyBadgePractice'
          return (
            <Pressable accessibilityHint={object.hint} accessibilityLabel={`自习室-${object.label}`} accessibilityRole="button" key={object.key} onPress={() => go(object)} style={styles.iconEntry} testID={`home.object.${object.key}`}>
              <SideEntryArt artKey={artKey} badge={badge} entryKey={object.key} label={object.label} />
            </Pressable>
          )
        })}
      </View>
    </View>
  )
}

export function StudyPlanPanel({
  learnedWords,
  onStart,
  onTodoPress,
  plan,
  progress,
  remainingWords,
  todos,
  totalWords,
}: {
  learnedWords: number
  onStart: () => void
  onTodoPress: (index: number) => void
  plan: StudyRoomPlan
  progress: number
  remainingWords: number
  todos: StudyRoomTodo[]
  totalWords: number
}) {
  return (
    <>
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

      <Card style={styles.bigBoard} stickers={[
        { key: 'leafSprig', width: 90, height: 80, left: -25, top: -25, zIndex: 10, rotateDeg: -20 },
        { key: 'citrusCorner', width: 70, height: 70, right: -15, bottom: -15, zIndex: 10 },
      ]}>
        <View style={styles.boardHeader}>
          <Text style={styles.boardTitle}>改变从这里开始</Text>
          <Text style={styles.boardSubtitle}>从系统推荐里选一条，完成后再回来。</Text>
        </View>
        <View style={styles.planTicket}>
          <View>
            <Text style={styles.ticketEyebrow}>今日房间任务</Text>
            <Text style={styles.ticketTitle}>{progress ? `学习进度 ${progress}%` : '从第一组新词开始'}</Text>
          </View>
          <Pressable accessibilityLabel="选择今日计划" accessibilityRole="button" onPress={onStart} style={styles.ticketButton} testID="home.plan.start">
            <Text style={styles.ticketButtonText}>开始学习</Text>
          </Pressable>
        </View>

        {todos.slice(0, 3).map((todo, index) => (
          <Pressable accessibilityLabel={`今日任务-${todo.title || index + 1}`} accessibilityRole="button" key={`${todo.title}-${index}`} onPress={() => onTodoPress(index)} style={styles.todoTicket} testID={`home.todo.${index}`}>
            <Text style={styles.todoIndex}>{String(index + 1).padStart(2, '0')}</Text>
            <View style={styles.todoCopy}>
              <Text numberOfLines={1} style={styles.todoTitle}>{todo.title || '学习任务'}</Text>
              <Text numberOfLines={2} style={styles.todoSubtitle}>{todo.subtitle || '系统推荐的下一步学习动作。'}</Text>
            </View>
            <Text style={styles.todoCta}>{todo.ctaLabel}</Text>
          </Pressable>
        ))}
      </Card>
    </>
  )
}
