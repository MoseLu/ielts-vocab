import React from 'react'
import {
  BarChart3,
  BookOpen,
  Bot,
  ChevronLeft,
  Home,
  LockKeyhole,
  MessageCircle,
  Search,
  Settings,
  SquarePen,
  User,
  type LucideIcon,
} from 'lucide-react-native'
import {
  ActivityIndicator,
  Animated,
  BackHandler,
  Easing,
  Image,
  Pressable,
  SafeAreaView,
  StatusBar,
  Text,
  View,
  type ImageSourcePropType,
} from 'react-native'
import type { PracticeMode } from '@ielts-vocab/app-core'
import { useSession } from '../state/SessionContext'
import { AIChatScreen } from '../screens/AIChatScreen'
import { BooksScreen } from '../screens/BooksScreen'
import { CustomBookScreen } from '../screens/CustomBookScreen'
import { ErrorsScreen } from '../screens/ErrorsScreen'
import { ExamsScreen } from '../screens/ExamsScreen'
import { HomePlanScreen, HomeScreen } from '../screens/HomeScreen'
import { JournalScreen } from '../screens/JournalScreen'
import { LoginScreen } from '../screens/LoginScreen'
import { PracticeScreen } from '../screens/PracticeScreen'
import { ProfileFeedbackScreen, ProfileScreen, ProfileSecurityScreen, ProfileSettingsScreen } from '../screens/ProfileScreen'
import { SearchScreen } from '../screens/SearchScreen'
import { StatsDetailScreen, StatsScreen } from '../screens/StatsScreen'
import { theme } from '../theme'
import { PracticeActionMenu } from './PracticeActionMenu'
import { PracticeCenterIcon } from './PracticeCenterIcon'
import { styles } from './RootNavigator.styles'
import type { Navigate, NavigateOptions, ScreenKey } from './types'

type RouteEntry = {
  options?: NavigateOptions
  screen: ScreenKey
}

type RouteState = {
  current: RouteEntry
  history: RouteEntry[]
}

type HeaderAction = {
  Icon: LucideIcon
  label: string
  onPress: () => void
  testID: string
}

type TabIconProps = {
  Icon: LucideIcon
  primary: boolean
  selected: boolean
  screen: ScreenKey
}

type RouteAction =
  | { entry: RouteEntry; type: 'navigate' }
  | { type: 'back' }

const screens: Array<{
  component: React.ComponentType<{ goBack?: () => void; navigate: Navigate; options?: NavigateOptions }>
  headerTitle?: string
  Icon: LucideIcon
  key: ScreenKey
  label: string
}> = [
  { component: HomeScreen, headerTitle: '雅思冲刺', Icon: Home, key: 'home', label: '首页' },
  { component: HomePlanScreen, headerTitle: '今日计划', Icon: SquarePen, key: 'homePlan', label: '今日计划' },
  { component: BooksScreen, Icon: BookOpen, key: 'books', label: '词书' },
  { component: CustomBookScreen, headerTitle: '自定义词书', Icon: BookOpen, key: 'customBook', label: '自定义词书' },
  { component: PracticeScreen, Icon: SquarePen, key: 'practice', label: '练习' },
  { component: ErrorsScreen, headerTitle: '错词本', Icon: SquarePen, key: 'errors', label: '错词' },
  { component: StatsScreen, headerTitle: '学习统计', Icon: BarChart3, key: 'stats', label: '统计' },
  { component: StatsDetailScreen, headerTitle: '统计详情', Icon: BarChart3, key: 'statsDetail', label: '统计详情' },
  { component: ExamsScreen, Icon: SquarePen, key: 'exams', label: '真题' },
  { component: JournalScreen, headerTitle: '学习日志', Icon: SquarePen, key: 'journal', label: '日志' },
  { component: AIChatScreen, headerTitle: 'AI 助手', Icon: SquarePen, key: 'ai', label: 'AI' },
  { component: SearchScreen, headerTitle: '全局查词', Icon: SquarePen, key: 'search', label: '查词' },
  { component: ProfileScreen, Icon: User, key: 'profile', label: '我的' },
  { component: ProfileSettingsScreen, Icon: Settings, key: 'profileSettings', label: '设置' },
  { component: ProfileSecurityScreen, Icon: LockKeyhole, key: 'profileSecurity', label: '账号安全' },
  { component: ProfileFeedbackScreen, Icon: MessageCircle, key: 'profileFeedback', label: '意见反馈' },
]

const tabKeys: ScreenKey[] = ['home', 'books', 'practice', 'stats', 'profile']
const rootTabKeys: ScreenKey[] = ['home', 'books', 'stats', 'profile']
const tabs = tabKeys
  .map(key => screens.find(item => item.key === key))
  .filter((item): item is (typeof screens)[number] => Boolean(item))
const tabArtSources: Partial<Record<ScreenKey, ImageSourcePropType>> = {
  books: require('../assets/stickers/tab-books-drawn.png'),
  home: require('../assets/stickers/tab-home-drawn.png'),
  practice: require('../assets/stickers/tab-practice-edit-loop.png'),
  profile: require('../assets/stickers/tab-profile-drawn.png'),
  stats: require('../assets/stickers/tab-stats-drawn.png'),
}

function isTabScreen(screen: ScreenKey) {
  return rootTabKeys.includes(screen)
}

function sameRoute(left: RouteEntry, right: RouteEntry) {
  return left.screen === right.screen && JSON.stringify(left.options ?? {}) === JSON.stringify(right.options ?? {})
}

function buildHeaderActions(screen: ScreenKey, navigate: Navigate): HeaderAction[] {
  const actions: HeaderAction[] = []
  if (screen !== 'search') {
    actions.push({ Icon: Search, label: '全局查词', onPress: () => navigate('search'), testID: 'header.search' })
  }
  if (screen !== 'ai') {
    actions.push({ Icon: Bot, label: 'AI 助手', onPress: () => navigate('ai'), testID: 'header.ai' })
  }
  if (screen === 'profile') {
    actions.push({ Icon: Settings, label: '设置', onPress: () => navigate('profileSettings'), testID: 'header.settings' })
  }
  return actions
}

function TabIcon({ Icon, primary, screen, selected }: TabIconProps) {
  const artSource = tabArtSources[screen]
  return (
    <View style={[styles.tabIconBox, primary ? styles.tabIconBoxPrimary : null, selected ? styles.tabIconBoxSelected : null]}>
      {primary ? (
        <View style={styles.practiceCenterSurface}>
          <PracticeCenterIcon />
        </View>
      ) : artSource ? (
        <Image resizeMode="contain" source={artSource} style={[styles.tabDrawnIcon, primary ? styles.tabDrawnIconPrimary : null]} />
      ) : (
        <Icon
          color={selected ? theme.colors.textInverse : primary ? theme.colors.accentDark : theme.colors.muted}
          fill={selected ? 'rgba(255, 255, 255, 0.2)' : 'none'}
          size={primary ? 24 : 22}
          strokeWidth={selected || primary ? 2.6 : 2.1}
        />
      )}
    </View>
  )
}

function routeReducer(state: RouteState, action: RouteAction): RouteState {
  if (action.type === 'back') {
    if (!state.history.length) return state
    const nextHistory = state.history.slice(0, -1)
    const current = state.history[state.history.length - 1]
    return { current, history: nextHistory }
  }

  if (sameRoute(state.current, action.entry)) {
    return state
  }

  if (isTabScreen(action.entry.screen)) {
    return {
      current: action.entry,
      history: [],
    }
  }

  return {
    current: action.entry,
    history: [...state.history, state.current],
  }
}

function MainTabs() {
  const [routeState, dispatch] = React.useReducer(routeReducer, {
    current: { screen: 'home' },
    history: [],
  })
  const [practiceMenuOpen, setPracticeMenuOpen] = React.useState(false)
  const tabBarFade = React.useRef(new Animated.Value(1)).current
  const navigate = React.useCallback<Navigate>((screen, nextOptions) => {
    setPracticeMenuOpen(false)
    dispatch({
      type: 'navigate',
      entry: { screen, options: nextOptions },
    })
  }, [])
  const openPractice = React.useCallback(() => {
    setPracticeMenuOpen(current => !current)
  }, [])
  const openPracticeShortcut = React.useCallback((mode: PracticeMode) => {
    setPracticeMenuOpen(false)
    navigate('practice', { mode })
  }, [navigate])
  const activeItem = screens.find(item => item.key === routeState.current.screen) ?? screens[0]
  const ActiveScreen = activeItem.component
  const headerActions = buildHeaderActions(routeState.current.screen, navigate)
  const headerTitle = activeItem.headerTitle ?? activeItem.label
  const showTabs = isTabScreen(routeState.current.screen)
  const showShellHeader = routeState.current.screen !== 'search' && routeState.current.screen !== 'home'
  const showBack = !showTabs
  const goBack = React.useCallback(() => {
    dispatch({ type: 'back' })
  }, [])
  const handleHeaderBack = React.useCallback(() => {
    if (routeState.history.length) {
      goBack()
      return
    }
    navigate('home')
  }, [goBack, navigate, routeState.history.length])

  React.useEffect(() => {
    Animated.timing(tabBarFade, {
      duration: practiceMenuOpen ? 280 : 180,
      easing: practiceMenuOpen ? Easing.out(Easing.cubic) : Easing.in(Easing.quad),
      toValue: practiceMenuOpen ? 0 : 1,
      useNativeDriver: true,
    }).start()
  }, [practiceMenuOpen, tabBarFade])

  React.useEffect(() => {
    const subscription = BackHandler.addEventListener('hardwareBackPress', () => {
      if (practiceMenuOpen) {
        setPracticeMenuOpen(false)
        return true
      }
      if (routeState.history.length) {
        goBack()
        return true
      }
      if (routeState.current.screen !== 'home' && isTabScreen(routeState.current.screen)) {
        navigate('home')
        return true
      }
      return false
    })
    return () => subscription.remove()
  }, [goBack, navigate, practiceMenuOpen, routeState.current.screen, routeState.history.length])

  return (
    <SafeAreaView style={styles.shell}>
      {showShellHeader ? (
        <View style={[styles.header, showBack ? styles.stackHeader : styles.tabHeader]}>
          {showBack ? (
            <>
              <Pressable accessibilityLabel="返回" accessibilityRole="button" onPress={handleHeaderBack} style={styles.headerButton}>
                <ChevronLeft color={theme.colors.text} size={23} strokeWidth={2.3} />
              </Pressable>
              <Text numberOfLines={1} style={styles.stackHeaderTitle}>
                {headerTitle}
              </Text>
              <View style={styles.headerActions}>
                {headerActions.length ? (
                  headerActions.map(action => {
                    const ActionIcon = action.Icon
                    return (
                      <Pressable
                        accessibilityLabel={action.label}
                        accessibilityRole="button"
                        key={action.label}
                        onPress={action.onPress}
                        style={styles.headerButton}
                        testID={action.testID}
                      >
                        <ActionIcon color={theme.colors.text} size={20} strokeWidth={2.2} />
                      </Pressable>
                    )
                  })
                ) : (
                  <View style={styles.headerSpacer} />
                )}
              </View>
            </>
          ) : (
            <>
              <View style={styles.tabHeaderCopy}>
                <Text numberOfLines={1} style={styles.tabHeaderTitle}>
                  {headerTitle}
                </Text>
              </View>
              <View style={styles.headerActions}>
                {headerActions.map(action => {
                  const ActionIcon = action.Icon
                  return (
                    <Pressable
                      accessibilityLabel={action.label}
                      accessibilityRole="button"
                      key={action.label}
                      onPress={action.onPress}
                      style={styles.headerButton}
                      testID={action.testID}
                    >
                      <ActionIcon color={theme.colors.text} size={20} strokeWidth={2.2} />
                    </Pressable>
                  )
                })}
              </View>
            </>
          )}
        </View>
      ) : null}
      <View style={styles.content} testID={`screen.${routeState.current.screen}`}>
        <ActiveScreen goBack={goBack} navigate={navigate} options={routeState.current.options} />
      </View>
      {showTabs ? (
        <Animated.View pointerEvents={practiceMenuOpen ? 'none' : 'auto'} style={[styles.tabBar, { opacity: tabBarFade }]}>
          {tabs.map(item => {
            const primary = item.key === 'practice'
            const active = item.key === routeState.current.screen
            return (
              <Pressable
                accessibilityLabel={`底部导航-${item.label}`}
                accessibilityRole="button"
                accessibilityState={{ selected: active, expanded: primary ? practiceMenuOpen : undefined }}
                key={item.key}
                onPress={primary ? openPractice : () => navigate(item.key)}
                style={({ pressed }) => [
                  styles.tabButton,
                  primary ? styles.tabButtonPrimary : null,
                  pressed ? styles.tabButtonPressed : null,
                ]}
                testID={`tab.${item.key}`}
              >
                <TabIcon Icon={item.Icon} primary={primary} screen={item.key} selected={active} />
              </Pressable>
            )
          })}
        </Animated.View>
      ) : null}
      {showTabs && practiceMenuOpen ? (
        <PracticeActionMenu
          onDismiss={() => setPracticeMenuOpen(false)}
          onSelect={openPracticeShortcut}
        />
      ) : null}
    </SafeAreaView>
  )
}

export function RootNavigator() {
  const { isAuthenticated, isHydrating } = useSession()
  if (isHydrating) {
    return (
      <>
        <StatusBar backgroundColor="transparent" barStyle="dark-content" translucent />
        <View style={styles.loading}>
          <ActivityIndicator color={theme.colors.primary} />
        </View>
      </>
    )
  }
  return (
    <>
      <StatusBar backgroundColor="transparent" barStyle="dark-content" translucent />
      {isAuthenticated ? <MainTabs /> : <LoginScreen />}
    </>
  )
}
