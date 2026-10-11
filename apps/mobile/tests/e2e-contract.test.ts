import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'
import {
  buildMobileWrongWordsReviewQueue,
  buildNextErrorReviewRoundWords,
  buildProgressSnapshot,
  buildQuickMemoryReviewQueuePath,
  buildQuickMemorySyncRecord,
  buildWrongWordRecord,
  evaluatePracticeAnswer,
  updateErrorReviewRoundResults,
  type MobileWord,
  type WrongWord,
} from '@ielts-vocab/app-core'

const mobileRoot = new URL('..', import.meta.url).pathname
const workspaceRoot = join(mobileRoot, '..', '..')
const flowDir = join(mobileRoot, 'e2e', 'maestro')
const runnerPath = join(mobileRoot, 'scripts', 'run-maestro-e2e.sh')

const requiredFlowFiles = [
  '_login.yaml',
  'login-smoke.yaml',
  '00-login-smoke.yaml',
  '01-book-chapter-practice.yaml',
  '02-wrong-word-recovery.yaml',
  '03-global-search-word-detail.yaml',
  '04-stats-ai-journal-exams.yaml',
  '05-feedback-and-advanced-entry.yaml',
] as const

const requiredSelectorNeedles = [
  'login.account.entry',
  'login.account.submit',
  'testID={`screen.${routeState.current.screen}`}',
  'tab.${item.key}',
  'header.search',
  'header.ai',
  'home.layout-guide',
  'home.hero.continue',
  'testID={`home.object.${object.key}`}',
  'search.input',
  'practice.quickAction.${mode}',
  'practice.quickAction.center',
  'practice.entry.${item.key}',
  'practice.controlSurface',
  'practice.control.wordList',
  'practice.control.favorite',
  'practice.control.pronunciation',
  'practice.control.settings',
  'practice.quickmemory.known',
  'ai.prompt',
  'feedback.title',
] as const

const requiredHomeObjectKeys = [
  "key: 'practice-yard'",
  "key: 'wrong-kit'",
  "key: 'todo-list'",
] as const

function read(relativePath: string): string {
  return readFileSync(join(workspaceRoot, relativePath), 'utf8')
}

function makeWord(word: string): MobileWord {
  return {
    book_id: 'book-a',
    book_title: 'Book A',
    chapter_id: '1',
    chapter_title: 'Chapter 1',
    definition: `${word} definition`,
    examples: [],
    group_key: '',
    listening_confusables: [],
    phonetic: '',
    pos: 'n.',
    word,
  }
}

function makeWrongWord(word: string, mistakeType: string): WrongWord {
  return {
    ...makeWord(word),
    dimension_states: {},
    ebbinghaus_completed: false,
    ebbinghaus_remaining: 0,
    ebbinghaus_streak: 0,
    last_error_at: '',
    mistake_type: mistakeType,
    pending_dimensions: [],
    recognition_pass_streak: 0,
    wrong_count: 1,
  }
}

describe('mobile Maestro E2E contract', () => {
  it('defines the first Web-parity mobile E2E flow set', () => {
    for (const file of requiredFlowFiles) {
      const path = join(flowDir, file)
      assert.equal(existsSync(path), true, `${file} should exist`)
      const content = readFileSync(path, 'utf8')
      assert.match(content, /^appId: com\.axiomaticworld\.ieltsvocab/m)
    }
  })

  it('keeps root and mobile scripts wired to the Maestro runner', () => {
    assert.equal(existsSync(runnerPath), true)
    const runner = readFileSync(runnerPath, 'utf8')
    assert.match(runner, /maestro test/)
    assert.match(runner, /ielts_vocab_api35/)
    assert.match(read('package.json'), /mobile:e2e:android/)
    assert.match(read('apps/mobile/package.json'), /e2e:android/)
  })

  it('exposes stable selectors used by the smoke flows', () => {
    const source = [
      read('apps/mobile/src/navigation/RootNavigator.tsx'),
      read('apps/mobile/src/navigation/PracticeActionMenu.tsx'),
      read('apps/mobile/src/screens/HomeScreen.tsx'),
      read('apps/mobile/src/components/StudyRoomScene.tsx'),
      read('apps/mobile/src/screens/LoginScreen.tsx'),
      read('apps/mobile/src/components/AccountLoginPane.tsx'),
      read('apps/mobile/src/screens/PracticeControlSurface.tsx'),
      read('apps/mobile/src/screens/PracticeEntryPanel.tsx'),
      read('apps/mobile/src/screens/PracticeScreen.tsx'),
      read('apps/mobile/src/screens/SearchScreen.tsx'),
      read('apps/mobile/src/screens/AIChatScreen.tsx'),
      read('apps/mobile/src/screens/ProfileScreen.tsx'),
    ].join('\n')

    for (const needle of requiredSelectorNeedles) {
      assert.ok(source.includes(needle), `${needle} should be present in mobile source`)
    }

    for (const needle of requiredHomeObjectKeys) {
      assert.ok(source.includes(needle), `${needle} should be present in mobile source`)
    }
  })

  it('keeps AI out of the home scene because the shell already exposes it', () => {
    const homeSource = [
      read('apps/mobile/src/screens/HomeScreen.tsx'),
      read('apps/mobile/src/components/StudyRoomScene.tsx'),
    ].join('\n')

    assert.equal(homeSource.includes('home.object.ai-letter'), false)
    assert.equal(homeSource.includes('AI 信件'), false)
  })

  it('keeps home side entries as icon shortcuts instead of large cards', () => {
    const sceneSource = [
      read('apps/mobile/src/components/StudyRoomScene.tsx'),
      read('apps/mobile/src/components/StudyRoomScene.styles.ts'),
    ].join('\n')

    assert.equal(sceneSource.includes('iconDock'), true)
    assert.equal(sceneSource.includes('iconBubble'), true)
    assert.equal(sceneSource.includes('iconBubbleAligned'), false)
    assert.equal(sceneSource.includes('rightRail'), false)
    assert.equal(sceneSource.includes('railItem'), false)
  })

  it('binds home scene text to art containers and live numeric badges', () => {
    const sceneSource = read('apps/mobile/src/components/StudyRoomScene.tsx')
    const sceneStyles = read('apps/mobile/src/components/StudyRoomScene.styles.ts')
    const artTextFrameSource = read('apps/mobile/src/components/ArtTextFrame.tsx')

    assert.match(sceneSource, /import \{ ArtTextFrame \} from '\.\/ArtTextFrame'/)
    assert.match(sceneSource, /testID="home\.hero\.artTextFrame"/)
    assert.match(sceneSource, /sticker="studyHeroBoard"/)
    assert.match(sceneSource, /contentInsets=\{\{/)
    assert.match(sceneSource, /boardContentTranslateX/)
    assert.match(sceneSource, /testID="home\.hero\.rewardPlaque"/)
    assert.match(sceneSource, /function formatSideEntryBadge/)
    assert.equal(sceneSource.includes('sideEntryTestBadges'), false)
    assert.match(sceneStyles, /heroBoardContent/)
    assert.match(sceneStyles, /heroRewardPlaque/)
    assert.match(sceneStyles, /heroRewardIcon/)
    assert.match(artTextFrameSource, /export function ArtTextFrame/)
    assert.match(artTextFrameSource, /fallbackArt/)
  })

  it('sizes the home board from the hidden scene layout guide', () => {
    const sceneSource = read('apps/mobile/src/components/StudyRoomScene.tsx')

    assert.match(sceneSource, /SCENE_SPEECH_ROW_HEIGHT/)
    assert.match(sceneSource, /setSceneHeight\(event\.nativeEvent\.layout\.height\)/)
    assert.match(sceneSource, /testID="home\.layout-guide"/)
    assert.match(sceneSource, /Animated\.timing\(boardReveal/)
    assert.match(sceneSource, /height: boardRevealHeight/)
  })

  it('keeps the home wallpaper as a horizontally draggable wide scene', () => {
    const sceneSource = read('apps/mobile/src/components/StudyRoomScene.tsx')
    const sceneStyles = read('apps/mobile/src/components/StudyRoomScene.styles.ts')

    assert.equal(existsSync(join(workspaceRoot, 'apps/mobile/src/assets/stickers/study-room-wide-wallpaper.png')), true)
    assert.match(sceneSource, /PanResponder\.create/)
    assert.match(sceneSource, /WIDE_WALLPAPER_ASPECT_RATIO/)
    assert.match(sceneSource, /wallpaperOffsetXRef/)
    assert.match(sceneSource, /testID="home\.scene\.drag"/)
    assert.match(sceneSource, /testID="home\.wallpaper\.drag"/)
    assert.match(sceneSource, /<Animated\.View\n        \{\.\.\.wallpaperPanResponder\.panHandlers\}/)
    assert.match(sceneSource, /<View onLayout=\{event => setSceneHeight\(event\.nativeEvent\.layout\.height\)\} style=\{styles\.scene\}>/)
    assert.match(sceneStyles, /sceneDraggableStage/)
    assert.match(sceneStyles, /sceneWideWallpaper/)
  })

  it('keeps the home header shortcuts fixed outside the draggable scene', () => {
    const sceneSource = read('apps/mobile/src/components/StudyRoomScene.tsx')

    const draggableStagePosition = sceneSource.indexOf('testID="home.scene.drag"')
    const fixedHeaderPosition = sceneSource.indexOf('<View style={styles.sceneHeader}>')

    assert.notEqual(draggableStagePosition, -1)
    assert.notEqual(fixedHeaderPosition, -1)
    assert.ok(fixedHeaderPosition > draggableStagePosition)
  })

  it('opens the center practice tab as the fullscreen quick practice view', () => {
    const navigatorSource = read('apps/mobile/src/navigation/RootNavigator.tsx')
    const practiceActionMenuSource = read('apps/mobile/src/navigation/PracticeActionMenu.tsx')
    const practiceEntrySource = read('apps/mobile/src/screens/PracticeEntryPanel.tsx')
    const practiceStyles = read('apps/mobile/src/screens/PracticeScreen.styles.ts')
    const navigatorStyles = read('apps/mobile/src/navigation/RootNavigator.styles.ts')
    const centerIconSource = read('apps/mobile/src/navigation/PracticeCenterIcon.tsx')

    assert.equal(existsSync(join(workspaceRoot, 'apps/mobile/src/assets/stickers/tab-practice-edit-loop.png')), true)
    assert.equal(existsSync(join(workspaceRoot, 'apps/mobile/src/assets/stickers/practice-hero-tutor.png')), true)
    assert.equal(existsSync(join(workspaceRoot, 'apps/mobile/src/assets/stickers/practice-stat-ribbon.png')), true)
    for (const iconFile of [
      'practice-mode-test.png',
      'practice-mode-listening.png',
      'practice-mode-follow.png',
      'practice-mode-quickmemory.png',
      'practice-mode-dictation.png',
      'practice-mode-meaning.png',
      'practice-mode-smart.png',
      'practice-mode-radio.png',
    ]) {
      assert.equal(existsSync(join(workspaceRoot, 'apps/mobile/src/assets/stickers', iconFile)), true)
    }
    assert.match(navigatorSource, /const rootTabKeys: ScreenKey\[\] = \['home', 'books', 'stats', 'profile'\]/)
    assert.match(navigatorSource, /practice: require\('\.\.\/assets\/stickers\/tab-practice-edit-loop\.png'\)/)
    assert.match(practiceActionMenuSource, /practiceHeroTutor = require\('\.\.\/assets\/stickers\/practice-hero-tutor\.png'\)/)
    assert.match(practiceActionMenuSource, /practiceStatRibbon = require\('\.\.\/assets\/stickers\/practice-stat-ribbon\.png'\)/)
    assert.equal(practiceActionMenuSource.includes('centerOpenSource'), false)
    assert.match(navigatorSource, /const \[practiceMenuOpen, setPracticeMenuOpen\] = React\.useState\(false\)/)
    assert.match(navigatorSource, /setPracticeMenuOpen\(current => !current\)/)
    assert.match(navigatorSource, /pointerEvents=\{practiceMenuOpen \? 'none' : 'auto'\}/)
    assert.match(navigatorSource, /const tabBarFade = React\.useRef\(new Animated\.Value\(1\)\)\.current/)
    assert.match(navigatorSource, /Animated\.timing\(tabBarFade, \{[\s\S]*?duration: practiceMenuOpen \? 280 : 180,[\s\S]*?toValue: practiceMenuOpen \? 0 : 1,[\s\S]*?useNativeDriver: true,/)
    assert.match(navigatorSource, /<PracticeActionMenu/)
    assert.match(navigatorSource, /onSelect=\{openPracticeShortcut\}/)
    assert.match(navigatorSource, /navigate\('practice', \{ mode \}\)/)
    assert.equal(navigatorSource.includes('Animated.timing(practiceSpin'), false)
    assert.equal(navigatorSource.includes("if (finished) navigate('practice')"), false)
    assert.match(navigatorSource, /const active = item\.key === routeState\.current\.screen/)
    assert.equal(navigatorSource.includes('styles.tabButtonPrimaryActive'), false)
    assert.equal(navigatorSource.includes('styles.tabIconBoxPrimaryOpen'), false)
    assert.match(navigatorSource, /pressed \? styles\.tabButtonPressed : null/)
    assert.equal(navigatorSource.includes('menuOpen={primary && practiceMenuOpen}'), false)
    assert.equal(navigatorSource.includes('tab-practice-entry-drawn.png'), false)
    assert.equal(practiceActionMenuSource.includes('tab-practice-entry-drawn.png'), false)
    assert.equal(practiceActionMenuSource.includes('practice-quick-action.png'), false)
    assert.match(navigatorSource, /onPress=\{primary \? openPractice : \(\) => navigate\(item\.key\)\}/)
    assert.match(navigatorSource, /accessibilityState=\{\{ selected: active, expanded: primary \? practiceMenuOpen : undefined \}\}/)
    assert.match(practiceActionMenuSource, /testID="practice\.quickAction\.fullscreen"/)
    assert.match(practiceActionMenuSource, /testID=\{`practice\.quickAction\.\$\{mode\}`\}/)
    assert.match(practiceActionMenuSource, /testID="practice\.quickAction\.backdrop"/)
    assert.match(practiceActionMenuSource, /testID="practice\.quickAction\.center"/)
    assert.equal(practiceActionMenuSource.includes("import { X } from 'lucide-react-native'"), false)
    assert.match(practiceActionMenuSource, /import \{ PracticeCenterIcon \} from '\.\/PracticeCenterIcon'/)
    assert.match(practiceActionMenuSource, /<PracticeCenterIcon open \/>/)
    assert.match(navigatorSource, /<PracticeCenterIcon \/>/)
    assert.match(centerIconSource, /markOpen: \{\n    transform: \[\{ rotate: '45deg' \}\],\n  \}/)
    assert.match(centerIconSource, /barHorizontal: \{\n    height: 7,\n    width: 28,\n  \}/)
    assert.match(centerIconSource, /barVertical: \{\n    height: 28,\n    width: 7,\n  \}/)
    assert.match(centerIconSource, /mark: \{\n    alignItems: 'center',\n    height: 34,\n    justifyContent: 'center',\n    width: 34,\n  \}/)
    assert.match(navigatorSource, /<Animated\.View pointerEvents=\{practiceMenuOpen \? 'none' : 'auto'\} style=\{\[styles\.tabBar, \{ opacity: tabBarFade \}\]\}>/)
    assert.match(practiceActionMenuSource, /import \{ Animated, Easing, Image, Pressable, StyleSheet, Text, View \} from 'react-native'/)
    assert.match(practiceActionMenuSource, /import \{ ArtTextFrame \} from '\.\.\/components\/ArtTextFrame'/)
    assert.match(practiceActionMenuSource, /Animated\.timing\(reveal, \{[\s\S]*?duration: 720,[\s\S]*?Easing\.out\(Easing\.cubic\),[\s\S]*?toValue: 1,[\s\S]*?useNativeDriver: true,/)
    assert.match(practiceActionMenuSource, /Animated\.timing\(reveal, \{[\s\S]*?duration: 260,[\s\S]*?Easing\.in\(Easing\.quad\),[\s\S]*?toValue: 0,[\s\S]*?useNativeDriver: true,/)
    assert.match(practiceActionMenuSource, /outputRange: \['0deg', '90deg'\]/)
    assert.match(practiceActionMenuSource, /<Animated\.View pointerEvents="none" style=\{\[styles\.overlayBackground, \{ opacity: reveal \}\]\} \/>/)
    assert.match(practiceActionMenuSource, /const heroOpacity = reveal\.interpolate\(\{[\s\S]*?inputRange: \[0\.12, 0\.42\],[\s\S]*?outputRange: \[0, 1\],/)
    assert.match(practiceActionMenuSource, /const heroTranslateY = reveal\.interpolate\(\{[\s\S]*?inputRange: \[0\.12, 0\.42\],[\s\S]*?outputRange: \[8, 0\],/)
    assert.match(practiceActionMenuSource, /<Animated\.View[\s\S]*?style=\{\[styles\.hero, \{ opacity: heroOpacity, transform: \[\{ translateY: heroTranslateY \}\] \}\]\}/)
    assert.equal(practiceActionMenuSource.includes("outputRange: ['0deg', '45deg']"), false)
    assert.match(practiceActionMenuSource, /const QUICK_ACTION_CENTER_BOTTOM = 18/)
    assert.match(practiceActionMenuSource, /const QUICK_ACTION_ORBIT_BOTTOM = 86/)
    assert.match(practiceActionMenuSource, /const TRIANGLE_BASE_ROW_BOTTOM = 0/)
    assert.equal(practiceActionMenuSource.includes('TRIANGLE_CENTER_BUTTON_BOTTOM'), false)
    assert.match(practiceActionMenuSource, /centerButtonPressed: \{\n    opacity: 0\.82,\n  \}/)
    assert.match(practiceActionMenuSource, /<Animated\.View style=\{\[styles\.centerButton, \{ bottom: QUICK_ACTION_CENTER_BOTTOM, transform: \[\{ translateX: -29 \}, \{ rotate: centerRotate \}\] \}\]\}>/)
    assert.match(practiceActionMenuSource, /centerButton: \{[\s\S]*?height: 58,[\s\S]*?width: 58,/)
    assert.match(practiceActionMenuSource, /overlay: \{\n    \.\.\.StyleSheet\.absoluteFillObject,[\s\S]*?zIndex: 35,/)
    assert.match(practiceActionMenuSource, /overlayBackground: \{\n    \.\.\.StyleSheet\.absoluteFillObject,[\s\S]*?backgroundColor: '#FFFDF0',/)
    assert.match(practiceActionMenuSource, /const ORBIT_ACTION_WIDTH = 64/)
    assert.match(practiceActionMenuSource, /const TRIANGLE_NODE_SPACING = 88/)
    assert.match(practiceActionMenuSource, /const shortcutModes: PracticeMode\[\] = \['test', 'listening', 'follow', 'quickmemory', 'dictation', 'meaning', 'smart', 'radio'\]/)
    assert.match(practiceActionMenuSource, /triangleNode\('test', 4, 0\)/)
    assert.match(practiceActionMenuSource, /triangleNode\('listening', 3, -0\.5\)/)
    assert.match(practiceActionMenuSource, /triangleNode\('follow', 3, 0\.5\)/)
    assert.match(practiceActionMenuSource, /triangleNode\('quickmemory', 2, -1\)/)
    assert.match(practiceActionMenuSource, /triangleNode\('dictation', 2, 0\)/)
    assert.match(practiceActionMenuSource, /triangleNode\('meaning', 2, 1\)/)
    assert.match(practiceActionMenuSource, /triangleNode\('smart', 1, -1\)/)
    assert.match(practiceActionMenuSource, /triangleNode\('radio', 1, 1\)/)
    assert.equal(practiceActionMenuSource.includes("triangleNode('errors'"), false)
    assert.match(practiceActionMenuSource, /test: 'practiceModeTest'/)
    assert.match(practiceActionMenuSource, /listening: 'practiceModeListening'/)
    assert.match(practiceActionMenuSource, /follow: 'practiceModeFollow'/)
    assert.match(practiceActionMenuSource, /quickmemory: 'practiceModeQuickMemory'/)
    assert.match(practiceActionMenuSource, /dictation: 'practiceModeDictation'/)
    assert.match(practiceActionMenuSource, /meaning: 'practiceModeMeaning'/)
    assert.match(practiceActionMenuSource, /smart: 'practiceModeSmart'/)
    assert.match(practiceActionMenuSource, /radio: 'practiceModeRadio'/)
    assert.match(practiceActionMenuSource, /const LEFT_TO_RIGHT_REVEAL_ORDER = new Map\(/)
    assert.match(practiceActionMenuSource, /\.sort\(\(left, right\) => \(left\.translateX === right\.translateX \? left\.bottom - right\.bottom : left\.translateX - right\.translateX\)\)/)
    assert.match(practiceActionMenuSource, /const start = order \* 0\.09/)
    assert.match(practiceActionMenuSource, /const end = start \+ 0\.34/)
    assert.match(practiceActionMenuSource, /outputRange: \[20, 0\]/)
    assert.match(practiceActionMenuSource, /outputRange: \[0\.82, 1\]/)
    assert.match(practiceActionMenuSource, /<Sticker height=\{30\} keyName=\{modeStickerKeys\[mode\]\} width=\{30\} \/>/)
    assert.match(practiceActionMenuSource, /<View style=\{styles\.iconShell\}>[\s\S]*?<Sticker height=\{30\} keyName=\{modeStickerKeys\[mode\]\} width=\{30\} \/>[\s\S]*?<\/View>\s+<Text numberOfLines=\{1\} style=\{styles\.actionLabel\}>/)
    assert.match(practiceActionMenuSource, /<Animated\.View key=\{mode\} style=\{\[styles\.orbitAction, orbitStyle\(mode\), modeRevealStyle\(mode, reveal\)\]\}>/)
    assert.equal(practiceActionMenuSource.includes('actionLabelBottomRow'), false)
    assert.equal(practiceActionMenuSource.includes('orbitActionBottomRow'), false)
    assert.equal(practiceActionMenuSource.includes('const bottomRow'), false)
    assert.match(practiceActionMenuSource, /iconShell: \{\n    alignItems: 'center',\n    height: 46,\n    justifyContent: 'center',\n    width: 46,\n  \}/)
    assert.equal(practiceActionMenuSource.includes("backgroundColor: 'rgba(255, 255, 255, 0.92)'"), false)
    assert.equal(practiceActionMenuSource.includes("borderColor: 'rgba(240, 177, 129, 0.9)'"), false)
    assert.equal(practiceActionMenuSource.includes('borderRadius: 23'), false)
    assert.match(practiceActionMenuSource, /style=\{\[styles\.orbitStage, \{ bottom: QUICK_ACTION_ORBIT_BOTTOM \}\]\}/)
    assert.match(practiceActionMenuSource, /orbitStage: \{\n    height: 430,/)
    assert.match(navigatorStyles, /tabButtonPrimary: \{\n    backgroundColor: 'transparent'/)
    assert.match(navigatorStyles, /tabButtonPressed: \{\n    opacity: 0\.86,\n  \}/)
    assert.equal(navigatorStyles.includes('tabBarHidden'), false)
    assert.match(navigatorStyles, /practiceCenterSurface: \{[\s\S]*?backgroundColor: 'transparent',[\s\S]*?borderColor: 'transparent',[\s\S]*?borderWidth: 0,[\s\S]*?height: 58,[\s\S]*?width: 58,/)
    assert.match(practiceActionMenuSource, /centerButton: \{[\s\S]*?backgroundColor: 'transparent',[\s\S]*?borderColor: 'transparent',[\s\S]*?borderWidth: 0,[\s\S]*?height: 58,[\s\S]*?width: 58,/)
    assert.equal(navigatorStyles.includes('tabButtonPrimaryActive'), false)
    assert.equal(navigatorStyles.includes('tabIconBoxPrimaryOpen'), false)
    assert.equal(navigatorStyles.includes('transform: [{ scale: 0.96 }]'), false)
    assert.equal(navigatorStyles.includes('tabButtonPrimary: {\n    backgroundColor: theme.colors.surfaceElevated'), false)
    assert.equal(navigatorStyles.includes('paddingTop: 8'), false)
    assert.equal(navigatorSource.includes('hitSlop={primary'), false)
    assert.equal(navigatorSource.includes('active ? styles.tabLabelActive : null'), false)
    assert.equal(navigatorSource.includes('<Text style={[styles.tabLabel'), false)
    assert.match(navigatorStyles, /tabBar: \{\n    alignItems: 'center'/)
    assert.match(navigatorStyles, /tabBar: \{[\s\S]*?backgroundColor: 'transparent',[\s\S]*?borderColor: 'transparent',[\s\S]*?borderTopWidth: 0,[\s\S]*?height: 58,[\s\S]*?paddingBottom: 0,[\s\S]*?paddingTop: 0,[\s\S]*?shadowOpacity: 0,[\s\S]*?elevation: 0,/)
    assert.match(navigatorStyles, /tabIconBoxSelected: \{[\s\S]*?backgroundColor: 'transparent',/)
    assert.equal(navigatorStyles.includes("alignItems: 'flex-end'"), false)
    assert.equal(navigatorStyles.includes("overflow: 'visible'"), false)
    assert.equal(navigatorStyles.includes('top: -34'), false)
    assert.equal(navigatorStyles.includes('translateX: -39'), false)
    assert.match(navigatorStyles, /tabButtonPrimary: \{\n    backgroundColor: 'transparent',\n    minHeight: 48,/)
    assert.match(navigatorStyles, /tabIconBoxPrimary: \{\n    height: 58,\n    width: 58,/)
    assert.match(navigatorStyles, /tabDrawnIconPrimary: \{\n    height: 34,\n    width: 42,/)
    assert.match(practiceEntrySource, /const PRACTICE_ENTRY_SHORTCUTS = PRACTICE_GROUPS\.flatMap/)
    assert.match(practiceActionMenuSource, /loadLearningStats/)
    assert.match(practiceActionMenuSource, /peekLearningStats/)
    assert.match(practiceActionMenuSource, /todayMasteredWordsFromStats/)
    assert.match(read('apps/mobile/src/api/learningStatsCache.ts'), /loadLearningStatsCached/)
    assert.match(read('apps/mobile/src/api/learningStatsCache.ts'), /peekLearningStats/)
    assert.match(practiceActionMenuSource, /const displayedTodayMasteredWords = Math\.max\(0, Math\.round\(todayMasteredWords\)\)/)
    assert.match(practiceActionMenuSource, /<Text numberOfLines=\{1\} style=\{\[styles\.ribbonText, styles\.ribbonTextPrefix\]\}>今日掌握<\/Text>/)
    assert.match(practiceActionMenuSource, /<View style=\{styles\.ribbonNumberSlot\}>/)
    assert.match(practiceActionMenuSource, /<Text adjustsFontSizeToFit minimumFontScale=\{0\.72\} numberOfLines=\{1\} style=\{styles\.ribbonNumber\}>[\s\S]*?\{displayedTodayMasteredWords\}[\s\S]*?<\/Text>/)
    assert.match(practiceActionMenuSource, /<Text numberOfLines=\{1\} style=\{\[styles\.ribbonText, styles\.ribbonTextSuffix\]\}>词<\/Text>/)
    assert.match(practiceActionMenuSource, /ribbonNumber: \{[\s\S]*?fontSize: 30,/)
    assert.match(practiceActionMenuSource, /ribbonNumber: \{[\s\S]*?includeFontPadding: false,[\s\S]*?textAlignVertical: 'center',/)
    assert.match(practiceActionMenuSource, /ribbonNumberSlot: \{[\s\S]*?justifyContent: 'center',[\s\S]*?marginHorizontal: 10,[\s\S]*?width: 94,/)
    assert.match(practiceActionMenuSource, /ribbonText: \{[\s\S]*?includeFontPadding: false,[\s\S]*?textAlignVertical: 'center',/)
    assert.match(practiceActionMenuSource, /ribbonTextPrefix: \{[\s\S]*?textAlign: 'right',/)
    assert.equal(practiceActionMenuSource.includes("ribbonTextPrefix: {\\n    textAlign: 'right',\\n    width:"), false)
    assert.match(practiceActionMenuSource, /ribbonTextSuffix: \{[\s\S]*?textAlign: 'left',/)
    assert.equal(practiceActionMenuSource.includes("ribbonTextSuffix: {\\n    textAlign: 'left',\\n    width:"), false)
    assert.match(practiceActionMenuSource, /ribbonTextWrap: \{[\s\S]*?bottom: 0,[\s\S]*?flexDirection: 'row',[\s\S]*?position: 'absolute',[\s\S]*?width: '100%',/)
    assert.match(practiceActionMenuSource, /source=\{practiceHeroTutor\}/)
    assert.match(practiceActionMenuSource, /<ArtTextFrame contentStyle=\{styles\.ribbonTextWrap\} height=\{107\} resizeMode="contain" source=\{practiceStatRibbon\} style=\{styles\.heroRibbon\} width=\{408\}>/)
    assert.match(practiceActionMenuSource, /testID="practice\.quickAction\.modePrompt"/)
    assert.match(practiceActionMenuSource, /<Text style=\{styles\.modePromptText\}>模式选择<\/Text>/)
    assert.equal(practiceActionMenuSource.includes('heroCard'), false)
    assert.equal(practiceActionMenuSource.includes('heroHint'), false)
    assert.equal(practiceActionMenuSource.includes('heroMetricPanel'), false)
    assert.equal(practiceActionMenuSource.includes('选择一个练习模式开始'), false)
    assert.equal(practiceActionMenuSource.includes('ribbonWing'), false)
    assert.equal(practiceActionMenuSource.includes('ribbonBody'), false)
    assert.match(practiceActionMenuSource, /heroScene: \{/)
    assert.match(practiceActionMenuSource, /heroRibbon: \{/)
    assert.match(practiceActionMenuSource, /modePromptBadge: \{/)
    assert.match(practiceActionMenuSource, /heroTutorCentered: \{/)
    assert.match(read('apps/mobile/src/lib/learningStats.ts'), /today_mastered_words/)
    assert.equal(practiceEntrySource.includes('二级面板'), false)
    assert.match(practiceEntrySource, /testID=\{`practice\.modeShortcut\.\$\{item\.key\}`\}/)
    assert.match(practiceEntrySource, /style=\{\(\{ pressed \}\) => \[styles\.modeShortcut, pressed \? styles\.modeShortcutPressed : null\]\}/)
    assert.match(practiceStyles, /modeShortcutRail: \{/)
    assert.match(practiceStyles, /entryTilePressed: \{/)
  })

  it('keeps the mobile practice control surface wired to list, settings, favorite, and pronunciation actions', () => {
    const controlSource = read('apps/mobile/src/screens/PracticeControlSurface.tsx')
    const screenSource = read('apps/mobile/src/screens/PracticeScreen.tsx')
    const dueReviewFlow = read('apps/mobile/e2e/maestro/01-book-chapter-practice.yaml')

    assert.match(screenSource, /<PracticeControlSurface/)
    assert.match(controlSource, /testID="practice\.controlSurface"/)
    assert.match(controlSource, /testID="practice\.control\.wordList"/)
    assert.match(controlSource, /testID="practice\.control\.favorite"/)
    assert.match(controlSource, /setFavorite\(currentWord\.word, nextActive\)/)
    assert.match(controlSource, /testID="practice\.control\.pronunciation"/)
    assert.match(controlSource, /onPlayWord/)
    assert.match(controlSource, /testID="practice\.control\.settings"/)
    assert.match(controlSource, /testID="practice\.settings\.restart"/)
    assert.match(controlSource, /testID=\{`practice\.wordList\.item\.\$\{itemIndex\}`\}/)
    assert.match(dueReviewFlow, /id: practice\.controlSurface/)
    assert.match(dueReviewFlow, /id: practice\.control\.wordList/)
    assert.match(dueReviewFlow, /visible: 练习设置/)
  })

  it('covers the due-review quick-memory chain from queue path through answer persistence payloads', () => {
    const queue = [makeWord('alpha'), makeWord('beta')]
    const path = buildQuickMemoryReviewQueuePath({
      bookId: 'book-a',
      chapterId: '1',
      limit: 10,
      offset: 0,
      withinDays: 3,
    })
    const known = evaluatePracticeAnswer(queue[0], 'quickmemory', 'known')
    const unknown = evaluatePracticeAnswer(queue[1], 'quickmemory', 'unknown')
    const record = buildQuickMemorySyncRecord(queue[1], false, 1_700_000_000_000)
    const snapshot = buildProgressSnapshot({ correctCount: 1, currentIndex: 2, queue, wrongCount: 1 })

    assert.equal(path, '/api/ai/quick-memory/review-queue?limit=10&within_days=3&offset=0&scope=due&book_id=book-a&chapter_id=1')
    assert.equal(known.correct, true)
    assert.equal(unknown.correct, false)
    assert.equal(record.status, 'unknown')
    assert.equal(record.bookId, 'book-a')
    assert.equal(record.chapterId, '1')
    assert.deepEqual(snapshot.answeredWords, ['alpha', 'beta'])
    assert.equal(snapshot.isCompleted, true)
  })

  it('covers the wrong-word recovery chain from filtered queue through retry-round selection', () => {
    const wrongWords = [
      makeWrongWord('alpha', 'recognition'),
      makeWrongWord('beta', 'dictation'),
    ]
    const queue = buildMobileWrongWordsReviewQueue(wrongWords, { dimension: 'dictation' }, [])
    const result = evaluatePracticeAnswer(queue[0], 'dictation', 'wrong spelling')
    const record = buildWrongWordRecord(queue[0], 'dictation')
    const roundResults = updateErrorReviewRoundResults({}, queue[0].word, result.correct)
    const retry = buildNextErrorReviewRoundWords(queue, roundResults)

    assert.deepEqual(queue.map(item => item.word), ['beta'])
    assert.equal(result.correct, false)
    assert.equal(record.mistake_type, 'dictation')
    assert.deepEqual(record.pending_dimensions, ['dictation'])
    assert.deepEqual(roundResults, { beta: false })
    assert.deepEqual(retry.map(item => item.word), ['beta'])
  })
})
