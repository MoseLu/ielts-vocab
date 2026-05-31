import React, { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native'
import { Sticker, type StickerKey } from './stickers'
import { theme } from '../theme'

type CompanionCatArtProps = {
  size?: number
  variant?: 'celebrate' | 'idle' | 'listening' | 'reading' | 'speaking' | 'worried'
}

type AnimatedCatBadgeProps = {
  caption: string
  label: string
  style?: StyleProp<ViewStyle>
}

type ScrollNoteProps = {
  caption: string
  title: string
}

const catStickerByVariant: Record<NonNullable<CompanionCatArtProps['variant']>, StickerKey> = {
  celebrate: 'catTutorCelebrate',
  idle: 'catTutorIdle',
  listening: 'catTutorListening',
  reading: 'catTutorReading',
  speaking: 'catTutorSpeaking',
  worried: 'catTutorWorried',
}

export function CompanionCatArt({ size = 78, variant = 'idle' }: CompanionCatArtProps) {
  return <Sticker height={size} keyName={catStickerByVariant[variant]} width={size} />
}

export function AnimatedCatBadge({ caption, label, style }: AnimatedCatBadgeProps) {
  const bob = useRef(new Animated.Value(0)).current

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(bob, { duration: 900, easing: Easing.inOut(Easing.quad), toValue: 1, useNativeDriver: true }),
        Animated.timing(bob, { duration: 900, easing: Easing.inOut(Easing.quad), toValue: 0, useNativeDriver: true }),
      ]),
    )
    loop.start()
    return () => loop.stop()
  }, [bob])

  const translateY = bob.interpolate({ inputRange: [0, 1], outputRange: [0, -5] })

  return (
    <View style={[styles.badge, style]}>
      <Animated.View style={{ transform: [{ translateY }] }}>
        <CompanionCatArt size={72} variant="reading" />
      </Animated.View>
      <Text style={styles.badgeLabel}>{label}</Text>
      <Text style={styles.badgeCaption}>{caption}</Text>
    </View>
  )
}

export function ScrollNote({ caption, title }: ScrollNoteProps) {
  return (
    <View style={styles.scrollNote}>
      <View style={styles.scrollRoll} />
      <View style={styles.scrollBody}>
        <Text style={styles.scrollTitle}>{title}</Text>
        <Text style={styles.scrollCaption}>{caption}</Text>
      </View>
      <View style={styles.scrollRoll} />
    </View>
  )
}

const styles = StyleSheet.create({
  badge: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.card,
    borderWidth: 1,
    padding: theme.spacing.sm,
    width: 112,
  },
  badgeCaption: {
    color: theme.colors.muted,
    fontSize: 11,
    fontWeight: '800',
    lineHeight: 15,
    marginTop: 2,
    textAlign: 'center',
  },
  badgeLabel: {
    color: theme.colors.primaryDark,
    fontSize: theme.typography.caption,
    fontWeight: '900',
    marginTop: -2,
  },
  scrollBody: {
    backgroundColor: '#FFF8ED',
    borderColor: '#F4CF97',
    borderWidth: 1,
    borderLeftWidth: 0,
    borderRightWidth: 0,
    flex: 1,
    minHeight: 76,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
  },
  scrollCaption: {
    color: theme.colors.muted,
    fontSize: theme.typography.caption,
    fontWeight: '700',
    lineHeight: 18,
    marginTop: 2,
  },
  scrollNote: {
    alignItems: 'stretch',
    flexDirection: 'row',
    marginBottom: theme.spacing.md,
  },
  scrollRoll: {
    backgroundColor: '#FFD89E',
    borderColor: '#E8B45F',
    borderRadius: theme.radius.pill,
    borderWidth: 1,
    width: 16,
  },
  scrollTitle: {
    color: theme.colors.accentDark,
    fontSize: theme.typography.label,
    fontWeight: '900',
  },
})
