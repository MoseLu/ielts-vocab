import React from 'react'
import {
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
  type ImageStyle,
  type StyleProp,
  type ViewStyle,
} from 'react-native'
import { theme } from '../../theme'
import { stickerDefaults, type StickerKey, type StickerSlot } from './catalog'
import { stickerSources } from './sources'

type StickerProps = {
  accessibilityLabel?: string
  decorative?: boolean
  height: number
  keyName: StickerKey
  style?: StyleProp<ImageStyle>
  width: number
}

type StickerLayerProps = {
  slots: StickerSlot[]
  style?: StyleProp<ViewStyle>
}

type DecoratedEmptyStateProps = {
  actionLabel?: string
  description: string
  onAction?: () => void
  sticker: StickerKey
  style?: StyleProp<ViewStyle>
  title: string
}

function slotStyle(slot: StickerSlot): ViewStyle {
  return {
    bottom: slot.bottom,
    height: slot.height,
    left: slot.left,
    opacity: slot.opacity,
    position: 'absolute',
    right: slot.right,
    top: slot.top,
    transform: slot.rotateDeg ? [{ rotate: `${slot.rotateDeg}deg` }] : undefined,
    width: slot.width,
    zIndex: slot.zIndex,
  }
}

export function Sticker({
  accessibilityLabel,
  decorative = stickerDefaults.decorative,
  height,
  keyName,
  style,
  width,
}: StickerProps) {
  const source = stickerSources[keyName]
  const accessibilityProps = decorative
    ? { accessibilityElementsHidden: true, accessible: false, importantForAccessibility: 'no-hide-descendants' as const }
    : { accessibilityLabel, accessible: true }

  if (!source) {
    return (
      <View {...accessibilityProps} style={[styles.fallback, { height, width }, style as StyleProp<ViewStyle>]}>
        <View style={styles.fallbackDot} />
      </View>
    )
  }

  return (
    <Image
      {...accessibilityProps}
      resizeMode="contain"
      source={source}
      style={[{ height, width }, style]}
    />
  )
}

export function StickerLayer({ slots, style }: StickerLayerProps) {
  return (
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, style]}>
      {slots.map((slot, index) => (
        <Sticker
          height={slot.height}
          key={`${slot.key}-${index}`}
          keyName={slot.key}
          style={slotStyle(slot) as StyleProp<ImageStyle>}
          width={slot.width}
        />
      ))}
    </View>
  )
}

export function DecoratedEmptyState({
  actionLabel,
  description,
  onAction,
  sticker,
  style,
  title,
}: DecoratedEmptyStateProps) {
  return (
    <View style={[styles.emptyState, style]}>
      <Sticker height={112} keyName={sticker} width={132} />
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyText}>{description}</Text>
      {actionLabel && onAction ? (
        <Pressable accessibilityRole="button" onPress={onAction} style={styles.emptyAction}>
          <Text style={styles.emptyActionText}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  emptyAction: {
    alignItems: 'center',
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.control,
    justifyContent: 'center',
    marginTop: theme.spacing.md,
    minHeight: 42,
    paddingHorizontal: theme.spacing.lg,
  },
  emptyActionText: {
    color: theme.colors.textInverse,
    fontSize: theme.typography.label,
    fontWeight: '900',
  },
  emptyState: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.borderStrong,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    marginBottom: theme.spacing.md,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.xl,
  },
  emptyText: {
    color: theme.colors.muted,
    fontSize: theme.typography.label,
    lineHeight: 22,
    textAlign: 'center',
  },
  emptyTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.title,
    fontWeight: '900',
    marginBottom: theme.spacing.xs,
    marginTop: theme.spacing.sm,
    textAlign: 'center',
  },
  fallback: {
    alignItems: 'center',
    backgroundColor: theme.colors.primarySoft,
    borderColor: theme.colors.primary,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    justifyContent: 'center',
  },
  fallbackDot: {
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radius.pill,
    height: 18,
    width: 18,
  },
})
