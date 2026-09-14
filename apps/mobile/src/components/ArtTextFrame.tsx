import React from 'react'
import {
  Animated,
  Image,
  StyleSheet,
  View,
  type ImageSourcePropType,
  type ImageStyle,
  type StyleProp,
  type ViewStyle,
} from 'react-native'
import { Sticker, type StickerKey } from './stickers'
import { theme } from '../theme'

type ArtFrameInsets = {
  bottom?: number
  left?: number
  right?: number
  top?: number
}

type ArtTextFrameProps = {
  children: React.ReactNode
  contentInsets?: ArtFrameInsets
  contentStyle?: StyleProp<any>
  height: number
  resizeMode?: 'contain' | 'cover' | 'stretch'
  source?: ImageSourcePropType
  sticker?: StickerKey
  style?: StyleProp<ViewStyle>
  testID?: string
  width: number
}

function contentInsetStyle(insets?: ArtFrameInsets): ViewStyle {
  return {
    bottom: insets?.bottom ?? 0,
    left: insets?.left ?? 0,
    right: insets?.right ?? 0,
    top: insets?.top ?? 0,
  }
}

export function ArtTextFrame({
  children,
  contentInsets,
  contentStyle,
  height,
  resizeMode = 'stretch',
  source,
  sticker,
  style,
  testID,
  width,
}: ArtTextFrameProps) {
  return (
    <View style={[styles.frame, { height, width }, style]} testID={testID}>
      {sticker ? (
        <Sticker
          height={height}
          keyName={sticker}
          resizeMode={resizeMode === 'cover' ? 'stretch' : resizeMode}
          style={styles.art as StyleProp<ImageStyle>}
          width={width}
        />
      ) : source ? (
        <Image
          accessibilityElementsHidden
          accessible={false}
          importantForAccessibility="no-hide-descendants"
          resizeMode={resizeMode}
          source={source}
          style={[styles.art, { height, width }]}
        />
      ) : (
        <View
          accessibilityElementsHidden
          accessible={false}
          importantForAccessibility="no-hide-descendants"
          style={styles.fallbackArt}
        />
      )}
      <Animated.View style={[styles.content, contentInsetStyle(contentInsets), contentStyle]}>
        {children}
      </Animated.View>
    </View>
  )
}

const styles = StyleSheet.create({
  art: {
    left: 0,
    position: 'absolute',
    top: 0,
  },
  content: {
    position: 'absolute',
  },
  fallbackArt: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(255, 251, 241, 0.78)',
    borderColor: 'rgba(116, 72, 36, 0.22)',
    borderRadius: theme.radius.card,
    borderWidth: StyleSheet.hairlineWidth,
  },
  frame: {
    position: 'relative',
  },
})
