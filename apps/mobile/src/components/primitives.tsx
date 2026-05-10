import React from 'react'
import {
  ActivityIndicator,
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
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.screen}
      keyboardDismissMode="on-drag"
      keyboardShouldPersistTaps="handled"
    >
      {hideHeader ? null : (
        <View style={styles.header}>
          <Text style={styles.eyebrow}>雅思冲刺</Text>
          <Text style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
      )}
      {children}
    </ScrollView>
  )
}

export function Card({ children, style, stickers }: { children: React.ReactNode; style?: StyleProp<ViewStyle>; stickers?: StickerSlot[] }) {
  return (
    <View style={[styles.card, style]}>
      {stickers ? <StickerLayer slots={stickers} /> : null}
      {children}
    </View>
  )
}

export function PrimaryButton({
  disabled,
  label,
  onPress,
  tone = 'primary',
  sticker,
}: {
  disabled?: boolean
  label: string
  onPress: () => void
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
      disabled={disabled}
      onPress={onPress}
      style={[styles.button, toneStyle, disabled ? styles.disabled : null]}
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
  keyboardType,
  multiline,
  onChangeText,
  placeholder,
  secureTextEntry,
  style,
  value,
}: {
  keyboardType?: KeyboardTypeOptions
  multiline?: boolean
  onChangeText: (value: string) => void
  placeholder: string
  secureTextEntry?: boolean
  style?: StyleProp<any>
  value: string
}) {
  return (
    <TextInput
      autoCapitalize="none"
      keyboardType={keyboardType}
      multiline={multiline}
      onChangeText={onChangeText}
      placeholder={placeholder}
      scrollEnabled={false}
      secureTextEntry={secureTextEntry}
      style={[styles.input, multiline ? styles.textarea : null, style]}
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
  return <Text style={styles.heading}>{children}</Text>
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
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 2,
    elevation: 2,
    marginBottom: theme.spacing.md,
    padding: theme.spacing.lg,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 4, width: 0 },
    shadowOpacity: 1,
    shadowRadius: 0,
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
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 2,
    elevation: 2,
    marginBottom: theme.spacing.md,
    marginTop: theme.spacing.sm,
    paddingBottom: theme.spacing.lg,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
    shadowColor: theme.colors.shadow,
    shadowOffset: { height: 4, width: 0 },
    shadowOpacity: 1,
    shadowRadius: 0,
  },
  heading: {
    color: theme.colors.text,
    fontSize: theme.typography.title,
    fontWeight: '800',
    marginBottom: theme.spacing.sm,
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
    backgroundColor: theme.colors.background,
  },
  screen: {
    backgroundColor: theme.colors.background,
    padding: theme.spacing.lg,
    paddingBottom: 160,
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
