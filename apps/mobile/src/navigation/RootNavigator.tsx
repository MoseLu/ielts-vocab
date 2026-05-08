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
import { ActivityIndicator, BackHandler, Pressable, SafeAreaView, StatusBar, StyleSheet, Text, View } from 'react-native'
import { useSession } from '../state/SessionContext'
import { AIChatScreen } from '../screens/AIChatScreen'
import { BooksScreen } from '../screens/BooksScreen'
import { CustomBookScreen } from '../screens/CustomBookScreen'
import { ErrorsScreen } from '../screens/ErrorsScreen'
import { ExamsScreen } from '../screens/ExamsScreen'
import { HomeScreen } from '../screens/HomeScreen'
import { JournalScreen } from '../screens/JournalScreen'
import { LoginScreen } from '../screens/LoginScreen'
import { PracticeScreen } from '../screens/PracticeScreen'
import { ProfileFeedbackScreen, ProfileScreen, ProfileSecurityScreen, ProfileSettingsScreen } from '../screens/ProfileScreen'
import { SearchScreen } from '../screens/SearchScreen'
import { StatsScreen } from '../screens/StatsScreen'
import { theme } from '../theme'
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
}

type TabIconProps = {
  Icon: LucideIcon
  primary: boolean
  selected: boolean
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
  { component: BooksScreen, Icon: BookOpen, key: 'books', label: '词书' },
  { component: CustomBookScreen, headerTitle: '自定义词书', Icon: BookOpen, key: 'customBook', label: '自定义词书' },
  { component: PracticeScreen, Icon: SquarePen, key: 'practice', label: '练习' },
  { component: ErrorsScreen, headerTitle: '错词本', Icon: SquarePen, key: 'errors', label: '错词' },
  { component: StatsScreen, headerTitle: '学习统计', Icon: BarChart3, key: 'stats', label: '统计' },
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
const tabs = tabKeys
  .map(key => screens.find(item => item.key === key))
  .filter((item): item is (typeof screens)[number] => Boolean(item))

function isTabScreen(screen: ScreenKey) {
  return tabKeys.includes(screen)
}

function sameRoute(left: RouteEntry, right: RouteEntry) {
  return left.screen === right.screen && JSON.stringify(left.options ?? {}) === JSON.stringify(right.options ?? {})
}

function buildHeaderActions(screen: ScreenKey, navigate: Navigate): HeaderAction[] {
  const actions: HeaderAction[] = []
  if (screen !== 'search') {
    actions.push({ Icon: Search, label: '全局查词', onPress: () => navigate('search') })
  }
  if (screen !== 'ai') {
    actions.push({ Icon: Bot, label: 'AI 助手', onPress: () => navigate('ai') })
  }
  if (screen === 'profile') {
    actions.push({ Icon: Settings, label: '设置', onPress: () => navigate('profileSettings') })
  }
  return actions
}

function TabIcon({ Icon, primary, selected }: TabIconProps) {
  return (
    <View style={[styles.tabIconBox, primary ? styles.tabIconBoxPrimary : null, selected ? styles.tabIconBoxSelected : null]}>
      <Icon
        color={selected ? theme.colors.textInverse : primary ? theme.colors.accentDark : theme.colors.muted}
        fill={selected ? 'rgba(255, 255, 255, 0.2)' : 'none'}
        size={primary ? 24 : 22}
        strokeWidth={selected || primary ? 2.6 : 2.1}
      />
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
  const navigate = React.useCallback<Navigate>((screen, nextOptions) => {
    dispatch({
      type: 'navigate',
      entry: { screen, options: nextOptions },
    })
  }, [])
  const activeItem = screens.find(item => item.key === routeState.current.screen) ?? screens[0]
  const ActiveScreen = activeItem.component
  const headerActions = buildHeaderActions(routeState.current.screen, navigate)
  const headerTitle = activeItem.headerTitle ?? activeItem.label
  const showTabs = isTabScreen(routeState.current.screen)
  const showShellHeader = routeState.current.screen !== 'search'
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
    const subscription = BackHandler.addEventListener('hardwareBackPress', () => {
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
  }, [goBack, navigate, routeState.current.screen, routeState.history.length])

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
      <View style={styles.content}>
        <ActiveScreen goBack={goBack} navigate={navigate} options={routeState.current.options} />
      </View>
      {showTabs ? (
        <View style={styles.tabBar}>
          {tabs.map(item => {
            const active = item.key === routeState.current.screen
            const primary = item.key === 'practice'
            return (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: active }}
                key={item.key}
                onPress={() => navigate(item.key)}
                style={[styles.tabButton, primary ? styles.tabButtonPrimary : null]}
              >
                <TabIcon Icon={item.Icon} primary={primary} selected={active} />
                <Text style={[styles.tabLabel, primary ? styles.tabLabelPrimary : null, active ? styles.tabLabelActive : null]}>
                  {item.label}
                </Text>
              </Pressable>
            )
          })}
        </View>
      ) : null}
    </SafeAreaView>
  )
}

export function RootNavigator() {
  const { isAuthenticated, isHydrating } = useSession()
  if (isHydrating) {
    return (
      <>
        <StatusBar backgroundColor={theme.colors.background} barStyle="dark-content" />
        <View style={styles.loading}>
          <ActivityIndicator color={theme.colors.primary} />
        </View>
      </>
    )
  }
  return (
    <>
      <StatusBar backgroundColor={theme.colors.background} barStyle="dark-content" />
      {isAuthenticated ? <MainTabs /> : <LoginScreen />}
    </>
  )
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
  },
  header: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderBottomColor: theme.colors.border,
    borderBottomWidth: 1,
    minHeight: 58,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.xs,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 4, width: 0 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  headerActions: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: theme.spacing.xs,
    minWidth: 36,
  },
  headerButton: {
    alignItems: 'center',
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
  headerSpacer: {
    height: 36,
    width: 36,
  },
  loading: {
    alignItems: 'center',
    backgroundColor: theme.colors.background,
    flex: 1,
    justifyContent: 'center',
  },
  shell: {
    backgroundColor: theme.colors.background,
    flex: 1,
  },
  stackHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  stackHeaderTitle: {
    color: theme.colors.text,
    flex: 1,
    fontSize: 20,
    fontWeight: '800',
    textAlign: 'center',
  },
  tabBar: {
    backgroundColor: '#F7CAD6',
    borderColor: '#E8B3C3',
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: theme.spacing.xs,
    paddingHorizontal: theme.spacing.sm,
    paddingBottom: 10,
    paddingTop: 8,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: -4, width: 0 },
    shadowOpacity: 0.07,
    shadowRadius: 12,
    elevation: 8,
  },
  tabButton: {
    alignItems: 'center',
    borderRadius: theme.radius.control,
    flex: 1,
    gap: 1,
    justifyContent: 'center',
    minHeight: 48,
    paddingVertical: 2,
  },
  tabButtonPrimary: {
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: '#FFFFFF',
    borderWidth: 2,
    marginTop: -18,
    minHeight: 68,
    shadowColor: '#B86D83',
    shadowOffset: { height: 5, width: 0 },
    shadowOpacity: 0.18,
    shadowRadius: 9,
    elevation: 6,
  },
  tabIconBox: {
    alignItems: 'center',
    borderRadius: theme.radius.card,
    height: 28,
    justifyContent: 'center',
    width: 28,
  },
  tabIconBoxPrimary: {
    backgroundColor: '#FFF8ED',
    borderColor: '#5A3A26',
    borderRadius: 22,
    borderWidth: 2,
    height: 42,
    width: 42,
  },
  tabIconBoxSelected: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primaryDark,
    borderWidth: 1,
    shadowColor: theme.colors.primaryDark,
    shadowOffset: { height: 2, width: 0 },
    shadowOpacity: 0.16,
    shadowRadius: 4,
    elevation: 2,
  },
  tabHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  tabHeaderCopy: {
    flex: 1,
    paddingRight: theme.spacing.md,
  },
  tabHeaderTitle: {
    color: theme.colors.text,
    fontSize: 20,
    fontWeight: '800',
  },
  tabLabel: {
    color: theme.colors.muted,
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 16,
  },
  tabLabelPrimary: {
    color: theme.colors.accentDark,
  },
  tabLabelActive: {
    color: theme.colors.primaryDark,
    fontWeight: '800',
  },
})
