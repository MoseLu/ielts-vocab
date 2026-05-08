import React, { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet } from 'react-native'
import Svg, { Circle, Path } from 'react-native-svg'
import { theme } from '../theme'

type OrangeLoadingMarkProps = {
  active?: boolean
  size?: number
}

export function OrangeLoadingMark({ active = false, size = 34 }: OrangeLoadingMarkProps) {
  const spin = useRef(new Animated.Value(0)).current

  useEffect(() => {
    if (!active) return undefined
    const loop = Animated.loop(
      Animated.timing(spin, {
        duration: 900,
        easing: Easing.linear,
        toValue: 1,
        useNativeDriver: true,
      }),
    )
    loop.start()
    return () => loop.stop()
  }, [active, spin])

  const rotate = spin.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] })

  return (
    <Animated.View style={[styles.mark, { height: size, transform: [{ rotate }], width: size }]}>
      <Svg height={size} viewBox="0 0 64 64" width={size}>
        <Circle cx="32" cy="35" fill={theme.colors.accent} r="22" stroke="#5A2E1B" strokeWidth="4" />
        <Path d="M20 24c10-9 25-6 32 6-12-6-23-4-34 5z" fill="#FFC46B" />
        <Circle cx="23" cy="43" fill="#FFCD88" opacity="0.74" r="3" />
        <Circle cx="43" cy="33" fill="#E96E1F" opacity="0.42" r="2.5" />
        <Path d="M37 12c7-8 17-8 23-2-4 11-14 14-24 9z" fill="#8BBE52" stroke="#5A2E1B" strokeWidth="3" />
        <Path d="M42 16c4-3 9-4 14-4" stroke="#5D8336" strokeLinecap="round" strokeWidth="2.5" />
      </Svg>
    </Animated.View>
  )
}

const styles = StyleSheet.create({
  mark: {
    alignItems: 'center',
    justifyContent: 'center',
  },
})
