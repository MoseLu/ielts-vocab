import React from 'react'
import {
  ActivityIndicator,
  ImageBackground,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type KeyboardTypeOptions,
  type StyleProp,
  type ViewStyle,
} from 'react-native'
import { StickerLayer, type StickerSlot, type StickerKey, Sticker } from './stickers'
import { theme } from '../theme'

const visualSkin = {
  screenPaper: require('../assets/stickers/ui-screen-paper-bg.png'),
} as const

export function ScreenScroll({
  children,
  hideHeader = false,
  title,
  subtitle,
}: {
  children: React.ReactNode
  hideHeader?: boolean
  title: string
  subtitle?: string
}) {
  return (
    <ImageBackground
      resizeMode="cover"
      source={visualSkin.screenPaper}
      style={styles.screenBackdrop}
    >
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.screen}
        keyboardDismissMode="on-drag"
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {hideHeader ? null : (
          <View style={styles.header}>
            <View style={styles.surfaceGlow} />
            <Text style={styles.eyebrow}>雅思冲刺</Text>
            <Text style={styles.title}>{title}</Text>
            {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
          </View>
        )}
        {children}
      </ScrollView>
    </ImageBackground>
  )
}

export function Card({
  children,
  size = 'large',
  style,
  stickers,
}: {
  children: React.ReactNode
  size?: 'large' | 'small'
  style?: StyleProp<ViewStyle>
  stickers?: StickerSlot[]
}) {
  return (
    <View style={[styles.card, size === 'large' ? styles.cardLarge : null, style, styles.nativeSurface]}>
      <View style={styles.surfaceGlow} />
      {stickers ? <StickerLayer slots={stickers} /> : null}
      {children}
    </View>
  )
}

export function PrimaryButton({
  accessibilityLabel,
  disabled,
  label,
  onPress,
  testID,
  tone = 'primary',
  sticker,
}: {
  accessibilityLabel?: string
  disabled?: boolean
  label: string
  onPress: () => void
  testID?: string
  tone?: 'primary' | 'danger' | 'neutral' | 'accent'
  sticker?: StickerKey
}) {
  const toneStyle =
    tone === 'danger'
      ? styles.danger
      : tone === 'neutral'
        ? styles.neutral
        : tone === 'accent'
          ? styles.accent
          : null
  return (
    <Pressable
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={[styles.button, toneStyle, disabled ? styles.disabled : null]}
      testID={testID}
    >
      <Text style={[styles.buttonText, tone === 'neutral' ? styles.darkButtonText : null]}>
        {label}
      </Text>
      {sticker ? (
        <View style={styles.buttonStickerWrap}>
          <Sticker height={56} keyName={sticker} width={56} />
        </View>
      ) : null}
    </Pressable>
  )
}

export function Field({
  accessibilityLabel,
  keyboardType,
  multiline,
  onChangeText,
  placeholder,
  secureTextEntry,
  style,
  testID,
  value,
}: {
  accessibilityLabel?: string
  keyboardType?: KeyboardTypeOptions
  multiline?: boolean
  onChangeText: (value: string) => void
  placeholder: string
  secureTextEntry?: boolean
  style?: StyleProp<any>
  testID?: string
  value: string
}) {
  return (
    <TextInput
      accessibilityLabel={accessibilityLabel ?? placeholder}
      autoCapitalize="none"
      keyboardType={keyboardType}
      multiline={multiline}
      onChangeText={onChangeText}
      placeholder={placeholder}
      scrollEnabled={false}
      secureTextEntry={secureTextEntry}
      style={[styles.input, multiline ? styles.textarea : null, style]}
      testID={testID}
      value={value}
    />
  )
}

export function StatusText({ error, loading }: { error?: string; loading?: boolean }) {
  if (loading) return <ActivityIndicator color={theme.colors.primary} style={styles.status} />
  if (error) {
    const message = error.includes('Network request failed') ? '网络连接失败，请检查服务或网络后重试' : error
    return (
      <View style={styles.errorBox}>
        <Text style={styles.error}>{message}</Text>
      </View>
    )
  }
  return null
}

export function Meta({ children }: { children: React.ReactNode }) {
  return <Text style={styles.meta}>{children}</Text>
}

export function Heading({ children }: { children: React.ReactNode }) {
  return (
    <View style={styles.headingFrame}>
      <View style={styles.headingAccent} />
      <Text style={styles.heading}>{children}</Text>
    </View>
  )
}

export function Body({ children }: { children: React.ReactNode }) {
  return <Text style={styles.body}>{children}</Text>
}

export function Pill({ label }: { label: string }) {
  return (
    <View style={styles.pill}>
      <Text style={styles.pillText}>{label}</Text>
    </View>
  )
}

export function Row({ children }: { children: React.ReactNode }) {
  return <View style={styles.row}>{children}</View>
}

const styles = StyleSheet.create({
  accent: {
    backgroundColor: theme.colors.accent,
  },
  body: {
    color: theme.colors.text,
    fontSize: theme.typography.body,
    lineHeight: 23,
  },
  button: {
    alignItems: 'center',
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.pill,
    borderWidth: 2,
    elevation: 2,
    justifyContent: 'center',
    minHeight: 48,
    marginTop: theme.spacing.sm,
    paddingHorizontal: theme.spacing.lg,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 4, width: 0 },
    shadowOpacity: 1,
    shadowRadius: 0,
  },
  buttonStickerWrap: {
    bottom: -8,
    position: 'absolute',
    right: -8,
    transform: [{ rotate: '10deg' }],
    zIndex: 10,
  },
  buttonText: {
    color: theme.colors.textInverse,
    fontSize: theme.typography.label,
    fontWeight: '700',
  },
  card: {
    backgroundColor: 'rgba(255, 251, 241, 0.82)',
    borderColor: 'rgba(116, 72, 36, 0.22)',
    borderRadius: theme.radius.card,
    borderWidth: StyleSheet.hairlineWidth,
    elevation: 2,
    marginBottom: theme.spacing.md,
    minHeight: 92,
    overflow: 'hidden',
    paddingBottom: theme.spacing.lg,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 5, width: 0 },
    shadowOpacity: 0.16,
    shadowRadius: 12,
  },
  cardLarge: {
    minHeight: 128,
  },
  danger: {
    backgroundColor: theme.colors.danger,
  },
  disabled: {
    opacity: 0.55,
  },
  darkButtonText: {
    color: theme.colors.text,
  },
  error: {
    color: theme.colors.danger,
    fontWeight: '700',
  },
  errorBox: {
    backgroundColor: theme.colors.dangerSoft,
    borderColor: theme.colors.danger,
    borderWidth: 1,
    borderRadius: theme.radius.card,
    marginBottom: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
  },
  eyebrow: {
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.primarySoft,
    borderRadius: theme.radius.pill,
    color: theme.colors.primaryDark,
    fontSize: theme.typography.caption,
    fontWeight: '800',
    marginBottom: theme.spacing.xs,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
  },
  header: {
    backgroundColor: 'rgba(255, 251, 241, 0.86)',
    borderColor: 'rgba(116, 72, 36, 0.22)',
    borderRadius: theme.radius.card,
    borderWidth: StyleSheet.hairlineWidth,
    elevation: 2,
    marginBottom: theme.spacing.md,
    marginTop: theme.spacing.sm,
    minHeight: 132,
    overflow: 'hidden',
    paddingBottom: theme.spacing.lg,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 5, width: 0 },
    shadowOpacity: 0.14,
    shadowRadius: 12,
  },
  heading: {
    color: theme.colors.text,
    fontSize: theme.typography.title,
    fontWeight: '900',
    includeFontPadding: false,
    lineHeight: 24,
    textAlignVertical: 'center',
  },
  headingFrame: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255, 244, 219, 0.86)',
    borderColor: 'rgba(211, 134, 45, 0.42)',
    borderRadius: theme.radius.pill,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    gap: theme.spacing.xs,
    justifyContent: 'center',
    marginBottom: theme.spacing.sm,
    minHeight: 36,
    minWidth: 128,
    overflow: 'hidden',
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 2, width: 0 },
    shadowOpacity: 0.12,
    shadowRadius: 5,
  },
  headingAccent: {
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radius.pill,
    height: 8,
    width: 8,
  },
  input: {
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.pill,
    borderWidth: 2,
    color: theme.colors.text,
    fontSize: theme.typography.body,
    marginBottom: theme.spacing.sm,
    minHeight: 48,
    paddingHorizontal: theme.spacing.md,
  },
  meta: {
    color: theme.colors.muted,
    fontSize: theme.typography.label,
    lineHeight: 20,
  },
  neutral: {
    backgroundColor: theme.colors.surfaceInset,
  },
  pill: {
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.primarySoft,
    borderRadius: theme.radius.pill,
    marginRight: theme.spacing.xs,
    marginTop: theme.spacing.xs,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
  },
  pillText: {
    color: theme.colors.primaryDark,
    fontSize: theme.typography.caption,
    fontWeight: '700',
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
  },
  scroll: {
    backgroundColor: 'transparent',
    flex: 1,
  },
  screen: {
    padding: theme.spacing.lg,
    paddingBottom: 160,
  },
  screenBackdrop: {
    flex: 1,
  },
  nativeSurface: {
    borderWidth: StyleSheet.hairlineWidth,
  },
  surfaceGlow: {
    backgroundColor: 'rgba(255, 255, 255, 0.42)',
    borderRadius: 120,
    height: 48,
    left: 14,
    position: 'absolute',
    right: 14,
    top: 8,
  },
  status: {
    marginBottom: theme.spacing.md,
  },
  subtitle: {
    color: theme.colors.muted,
    fontSize: theme.typography.body,
    lineHeight: 22,
    maxWidth: 320,
  },
  textarea: {
    borderRadius: theme.radius.card,
    minHeight: 92,
    paddingTop: theme.spacing.sm,
    textAlignVertical: 'top',
  },
  title: {
    color: theme.colors.text,
    fontSize: theme.typography.heading,
    fontWeight: '800',
    marginBottom: theme.spacing.sm,
  },
})
