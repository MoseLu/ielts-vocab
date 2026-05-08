import React, { useEffect, useMemo, useState } from 'react'
import {
  BarChart3,
  Bell,
  BookOpen,
  ChevronRight,
  ClipboardList,
  Info,
  LockKeyhole,
  Mail,
  MessageCircle,
  NotebookPen,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  SquarePen,
  Trash2,
  User,
  Wifi,
  type LucideIcon,
} from 'lucide-react-native'
import { Pressable, ScrollView, Text, TextInput, View, type StyleProp, type ViewStyle } from 'react-native'
import { FeatureWishSchema, parseArray, type FeatureWish } from '@ielts-vocab/app-core'
import { mobileApiClient } from '../api/mobileApi'
import { StatusText } from '../components/primitives'
import { DecoratedEmptyState } from '../components/stickers'
import type { Navigate } from '../navigation/types'
import { useSession } from '../state/SessionContext'
import { theme } from '../theme'
import { styles } from './ProfileScreen.styles'

type IconTileProps = {
  Icon: LucideIcon
  color: string
  label: string
  onPress: () => void
  tone: string
}

type SettingRowProps = {
  Icon: LucideIcon
  label: string
  onPress?: () => void
  value?: string
}

const mutedValue = '未开启'

function initialFromName(name: string) {
  return name.trim().slice(0, 1).toUpperCase() || 'I'
}

function readableStatus(status?: string | null) {
  if (!status || status === 'open') return '待评估'
  if (status === 'planned') return '已排期'
  if (status === 'done' || status === 'closed') return '已完成'
  return status
}

function SurfaceCard({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.surfaceCard, style]}>{children}</View>
}

function IconTile({ Icon, color, label, onPress, tone }: IconTileProps) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.iconTile}>
      <View style={[styles.iconTileMark, { backgroundColor: tone }]}>
        <Icon color={color} size={25} strokeWidth={2.4} />
      </View>
      <Text numberOfLines={1} style={styles.iconTileLabel}>
        {label}
      </Text>
    </Pressable>
  )
}

function SettingRow({ Icon, label, onPress, value }: SettingRowProps) {
  return (
    <Pressable accessibilityRole="button" disabled={!onPress} onPress={onPress} style={styles.settingRow}>
      <View style={styles.settingLeft}>
        <Icon color={theme.colors.text} size={23} strokeWidth={2.1} />
        <Text style={styles.settingLabel}>{label}</Text>
      </View>
      <View style={styles.settingRight}>
        {value ? (
          <Text numberOfLines={1} style={styles.settingValue}>
            {value}
          </Text>
        ) : null}
        <ChevronRight color={theme.colors.textTertiary} size={21} strokeWidth={2.1} />
      </View>
    </Pressable>
  )
}

export function ProfileScreen({ navigate }: { navigate: Navigate }) {
  const { user } = useSession()
  const displayName = user?.username ?? '未登录'
  const initial = useMemo(() => initialFromName(displayName), [displayName])

  return (
    <ScrollView
      contentContainerStyle={styles.screen}
      keyboardDismissMode="on-drag"
      keyboardShouldPersistTaps="handled"
      style={styles.scroll}
    >
      <View style={styles.identityBlock}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initial}</Text>
        </View>
        <View style={styles.identityCopy}>
          <Text numberOfLines={1} style={styles.username}>
            {displayName}
          </Text>
          <Text numberOfLines={1} style={styles.userMeta}>
            {user?.email || '邮箱未绑定'}
          </Text>
        </View>
        <Pressable accessibilityRole="button" onPress={() => navigate('profileSettings')} style={styles.identityLink}>
          <ChevronRight color={theme.colors.textTertiary} size={24} strokeWidth={2.2} />
        </Pressable>
      </View>

      <View style={styles.benefitStrip}>
        <View style={styles.benefitCell}>
          <Text style={styles.benefitTitle}>今日学习</Text>
          <Text style={styles.benefitMeta}>计划同步</Text>
        </View>
        <View style={styles.benefitDivider} />
        <View style={styles.benefitCell}>
          <Text style={styles.benefitTitle}>账号安全</Text>
          <Text style={styles.benefitMeta}>{user?.email ? '邮箱已绑定' : '待绑定'}</Text>
        </View>
        <View style={styles.benefitDivider} />
        <View style={styles.benefitCell}>
          <Text style={styles.benefitTitle}>设置入口</Text>
          <Text style={styles.benefitMeta}>二级页面</Text>
        </View>
      </View>

      <SurfaceCard>
        <View style={styles.quickGrid}>
          <IconTile Icon={ClipboardList} color={theme.colors.accent} label="收藏" onPress={() => navigate('books')} tone={theme.colors.accentSoft} />
          <IconTile Icon={NotebookPen} color={theme.colors.info} label="记录" onPress={() => navigate('journal')} tone={theme.colors.infoSoft} />
          <IconTile Icon={Settings} color={theme.colors.rose} label="设置" onPress={() => navigate('profileSettings')} tone={theme.colors.roseSoft} />
          <IconTile Icon={BarChart3} color={theme.colors.emerald} label="统计" onPress={() => navigate('stats')} tone={theme.colors.emeraldSoft} />
        </View>
      </SurfaceCard>

      <SurfaceCard>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>学习入口</Text>
          <Pressable accessibilityRole="button" onPress={() => navigate('search')} style={styles.moreLink}>
            <Text style={styles.moreText}>查词</Text>
            <ChevronRight color={theme.colors.textTertiary} size={18} strokeWidth={2.1} />
          </Pressable>
        </View>
        <View style={styles.learningRow}>
          <IconTile Icon={BookOpen} color={theme.colors.accent} label="词书" onPress={() => navigate('books')} tone={theme.colors.accentSoft} />
          <IconTile Icon={SquarePen} color={theme.colors.info} label="练习" onPress={() => navigate('practice')} tone={theme.colors.infoSoft} />
          <IconTile Icon={Search} color={theme.colors.emerald} label="查词" onPress={() => navigate('search')} tone={theme.colors.emeraldSoft} />
          <IconTile Icon={NotebookPen} color={theme.colors.rose} label="日志" onPress={() => navigate('journal')} tone={theme.colors.roseSoft} />
        </View>
      </SurfaceCard>
    </ScrollView>
  )
}

export function ProfileSettingsScreen({ navigate }: { goBack?: () => void; navigate: Navigate }) {
  const { logout, user } = useSession()
  const displayName = user?.username ?? '未登录'

  return (
    <ScrollView
      contentContainerStyle={styles.settingsScreen}
      keyboardDismissMode="on-drag"
      keyboardShouldPersistTaps="handled"
      style={styles.scroll}
    >
      <SurfaceCard style={styles.settingGroup}>
        <SettingRow Icon={User} label="个人信息" value={displayName} />
        <SettingRow Icon={Mail} label="邮箱绑定" value={user?.email ? '已绑定' : '未绑定'} />
        <SettingRow Icon={LockKeyhole} label="账号安全" value="找回 / 绑定" onPress={() => navigate('profileSecurity')} />
      </SurfaceCard>

      <SurfaceCard style={styles.settingGroup}>
        <SettingRow Icon={ShieldCheck} label="隐私设置" value={mutedValue} />
        <SettingRow Icon={Bell} label="消息通知" value="系统默认" />
        <SettingRow Icon={Wifi} label="通用设置" value="在线优先" />
        <SettingRow Icon={Trash2} label="清理缓存" value="轻量缓存" />
      </SurfaceCard>

      <SurfaceCard style={styles.settingGroup}>
        <SettingRow Icon={Info} label="关于雅思冲刺" value="当前已是最新版本" />
        <SettingRow Icon={MessageCircle} label="意见反馈" onPress={() => navigate('profileFeedback')} />
      </SurfaceCard>

      <Pressable accessibilityRole="button" onPress={() => void logout()} style={styles.logoutButton}>
        <Text style={styles.logoutText}>退出登录</Text>
      </Pressable>
    </ScrollView>
  )
}

export function ProfileSecurityScreen({ navigate }: { goBack?: () => void; navigate: Navigate }) {
  const { user } = useSession()
  const [email, setEmail] = useState(user?.email ?? '')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function bindEmail() {
    setError('')
    setNotice('')
    const nextEmail = email.trim()
    const nextCode = code.trim()
    if (!nextEmail) {
      setError('请先输入邮箱')
      return
    }
    const path = nextCode ? '/api/auth/bind-email' : '/api/auth/send-code'
    await mobileApiClient.json(path, {
      method: 'POST',
      body: JSON.stringify(nextCode ? { email: nextEmail, code: nextCode } : { email: nextEmail }),
    })
    setNotice(nextCode ? '邮箱已绑定' : '验证码已发送')
  }

  return (
    <ScrollView
      contentContainerStyle={styles.settingsScreen}
      keyboardDismissMode="on-drag"
      keyboardShouldPersistTaps="handled"
      style={styles.scroll}
    >
      <SurfaceCard>
        <Text style={styles.sectionTitle}>账号找回</Text>
        <Text style={styles.sectionMeta}>绑定邮箱后可用于密码找回和学习通知。</Text>
        <StatusText error={error} />
        {notice ? <Text style={styles.noticeText}>{notice}</Text> : null}
        <TextInput
          autoCapitalize="none"
          keyboardType="email-address"
          onChangeText={setEmail}
          placeholder="邮箱"
          placeholderTextColor={theme.colors.textTertiary}
          style={styles.input}
          value={email}
        />
        <TextInput
          autoCapitalize="none"
          onChangeText={setCode}
          placeholder="验证码，留空则发送验证码"
          placeholderTextColor={theme.colors.textTertiary}
          style={styles.input}
          value={code}
        />
        <Pressable accessibilityRole="button" onPress={() => void bindEmail().catch(err => setError(err.message))} style={styles.primaryButton}>
          <Mail color={theme.colors.textInverse} size={18} strokeWidth={2.4} />
          <Text style={styles.primaryButtonText}>{code.trim() ? '绑定邮箱' : '发送验证码'}</Text>
        </Pressable>
      </SurfaceCard>
    </ScrollView>
  )
}

export function ProfileFeedbackScreen({ navigate }: { goBack?: () => void; navigate: Navigate }) {
  const [wishes, setWishes] = useState<FeatureWish[]>([])
  const [wishTitle, setWishTitle] = useState('')
  const [wishDescription, setWishDescription] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  function loadWishes() {
    mobileApiClient
      .json<{ items?: unknown[]; wishes?: unknown[] }>('/api/feature-wishes')
      .then(payload => setWishes(parseArray(FeatureWishSchema, payload.items ?? payload.wishes)))
      .catch(() => undefined)
  }

  useEffect(loadWishes, [])

  async function createWish() {
    setError('')
    setNotice('')
    const title = wishTitle.trim()
    const description = wishDescription.trim()
    if (!title) {
      setError('请填写反馈标题')
      return
    }
    await mobileApiClient.json('/api/feature-wishes', {
      method: 'POST',
      body: JSON.stringify({ title, description }),
    })
    setWishTitle('')
    setWishDescription('')
    setNotice('反馈已提交')
    loadWishes()
  }

  return (
    <ScrollView
      contentContainerStyle={styles.settingsScreen}
      keyboardDismissMode="on-drag"
      keyboardShouldPersistTaps="handled"
      style={styles.scroll}
    >
      <SurfaceCard>
        <Text style={styles.sectionTitle}>问题 / 愿望</Text>
        <Text style={styles.sectionMeta}>把你希望补上的功能、体验问题或者用起来不顺的地方写在这里。</Text>
        <StatusText error={error} />
        {notice ? <Text style={styles.noticeText}>{notice}</Text> : null}
        <TextInput
          onChangeText={setWishTitle}
          placeholder="标题"
          placeholderTextColor={theme.colors.textTertiary}
          style={styles.input}
          value={wishTitle}
        />
        <TextInput
          multiline
          onChangeText={setWishDescription}
          placeholder="描述你遇到的问题或想要的功能"
          placeholderTextColor={theme.colors.textTertiary}
          scrollEnabled={false}
          style={[styles.input, styles.textarea]}
          textAlignVertical="top"
          value={wishDescription}
        />
        <Pressable accessibilityRole="button" onPress={() => void createWish().catch(err => setError(err.message))} style={styles.secondaryButton}>
          <Sparkles color={theme.colors.accentDark} size={18} strokeWidth={2.2} />
          <Text style={styles.secondaryButtonText}>提交反馈</Text>
        </Pressable>
      </SurfaceCard>

      <SurfaceCard>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>愿望池</Text>
          <Text style={styles.sectionMeta}>{wishes.length} 条</Text>
        </View>
        {wishes.length ? (
          wishes.slice(0, 4).map(wish => (
            <View key={wish.id} style={styles.wishRow}>
              <View style={styles.wishMark}>
                <MessageCircle color={theme.colors.accent} size={18} strokeWidth={2.2} />
              </View>
              <View style={styles.wishCopy}>
                <Text numberOfLines={1} style={styles.wishTitle}>
                  {wish.title}
                </Text>
                <Text numberOfLines={2} style={styles.wishMeta}>
                  {readableStatus(wish.status)} · {wish.votes} 票{wish.description ? ` · ${wish.description}` : ''}
                </Text>
              </View>
            </View>
          ))
        ) : (
          <DecoratedEmptyState
            description="提交第一个愿望后，这里会展示进展和票数。"
            sticker="catTutorReading"
            title="还没有提交过反馈"
          />
        )}
      </SurfaceCard>
    </ScrollView>
  )
}
