import React from 'react'
import { StyleSheet, View } from 'react-native'
import { Sticker, type StickerKey } from './stickers'
import { theme } from '../theme'

export type PracticeModeArtKind = 'ebbinghaus' | 'errors' | 'follow' | 'regular' | 'speaking'

type Props = {
  kind: PracticeModeArtKind
  size?: number
}

const stickerByKind: Record<PracticeModeArtKind, StickerKey> = {
  ebbinghaus: 'reviewClock',
  errors: 'wrongWordSticky',
  follow: 'recordingMic',
  regular: 'vocabCardStack',
  speaking: 'catTutorSpeaking',
}

export function PracticeModeArt({ kind, size = 68 }: Props) {
  return (
    <View style={[styles.frame, { borderRadius: Math.max(18, size * 0.3), height: size, width: size }]}>
      <Sticker height={size * 0.82} keyName={stickerByKind[kind]} width={size * 0.82} />
    </View>
  )
}

const styles = StyleSheet.create({
  frame: {
    alignItems: 'center',
    backgroundColor: theme.colors.surfaceElevated,
    borderColor: theme.colors.border,
    borderWidth: 1,
    justifyContent: 'center',
  },
})
