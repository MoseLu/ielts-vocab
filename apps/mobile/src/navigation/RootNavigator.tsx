import React from 'react'
import { ActivityIndicator, Pressable, SafeAreaView, StyleSheet, Text, View } from 'react-native'
import { useSession } from '../state/SessionContext'
import { AIChatScreen } from '../screens/AIChatScreen'
import { BooksScreen } from '../screens/BooksScreen'
import { HomeScreen } from '../screens/HomeScreen'
import { LoginScreen } from '../screens/LoginScreen'
import { PracticeScreen } from '../screens/PracticeScreen'
import { ProfileScreen } from '../screens/ProfileScreen'
import { StatsScreen } from '../screens/StatsScreen'
import { theme } from '../theme'

type TabKey = 'Plan' | 'Books' | 'Practice' | 'Stats' | 'AI' | 'Profile'

const tabs: Array<{
  component: React.ComponentType
  key: TabKey
  label: string
}> = [
  { component: HomeScreen, key: 'Plan', label: '计划' },
  { component: BooksScreen, key: 'Books', label: '词书' },
  { component: PracticeScreen, key: 'Practice', label: '练习' },
  { component: StatsScreen, key: 'Stats', label: '统计' },
  { component: AIChatScreen, key: 'AI', label: 'AI' },
  { component: ProfileScreen, key: 'Profile', label: '我的' },
]

function MainTabs() {
  const [activeTab, setActiveTab] = React.useState<TabKey>('Plan')
  const activeItem = tabs.find(item => item.key === activeTab) ?? tabs[0]
  const ActiveScreen = activeItem.component

  return (
    <SafeAreaView style={styles.shell}>
      <View style={styles.content}>
        <ActiveScreen />
      </View>
      <View style={styles.tabBar}>
        {tabs.map(item => {
          const active = item.key === activeTab
          return (
            <Pressable
              accessibilityRole="button"
              key={item.key}
              onPress={() => setActiveTab(item.key)}
              style={[styles.tabButton, active ? styles.tabButtonActive : null]}
            >
              <Text style={[styles.tabLabel, active ? styles.tabLabelActive : null]}>{item.label}</Text>
            </Pressable>
          )
        })}
      </View>
    </SafeAreaView>
  )
}

export function RootNavigator() {
  const { isAuthenticated, isLoading } = useSession()
  if (isLoading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color={theme.colors.primary} />
      </View>
    )
  }
  return isAuthenticated ? <MainTabs /> : <LoginScreen />
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
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
  tabBar: {
    backgroundColor: theme.colors.card,
    borderColor: theme.colors.border,
    borderTopWidth: 1,
    flexDirection: 'row',
    paddingHorizontal: theme.spacing.xs,
    paddingVertical: theme.spacing.xs,
  },
  tabButton: {
    alignItems: 'center',
    borderRadius: theme.radius.control,
    flex: 1,
    minHeight: 44,
    justifyContent: 'center',
  },
  tabButtonActive: {
    backgroundColor: theme.colors.primarySoft,
  },
  tabLabel: {
    color: theme.colors.muted,
    fontSize: 12,
    fontWeight: '700',
  },
  tabLabelActive: {
    color: theme.colors.primary,
  },
})
