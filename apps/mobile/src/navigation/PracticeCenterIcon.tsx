import React from 'react'
import { StyleSheet, View } from 'react-native'

type PracticeCenterIconProps = {
  open?: boolean
}

export function PracticeCenterIcon({ open = false }: PracticeCenterIconProps) {
  return (
    <View style={[styles.mark, open ? styles.markOpen : null]}>
      <View style={[styles.bar, styles.barHorizontal]} />
      <View style={[styles.bar, styles.barVertical]} />
      <View style={styles.dot} />
    </View>
  )
}

const styles = StyleSheet.create({
  bar: {
    backgroundColor: '#E3A915',
    borderColor: 'rgba(111, 74, 56, 0.16)',
    borderRadius: 8,
    borderWidth: 1,
    position: 'absolute',
  },
  barHorizontal: {
    height: 7,
    width: 28,
  },
  barVertical: {
    height: 28,
    width: 7,
  },
  dot: {
    backgroundColor: '#FFE8A7',
    borderRadius: 3,
    height: 6,
    opacity: 0.9,
    position: 'absolute',
    right: 6,
    top: 6,
    width: 6,
  },
  mark: {
    alignItems: 'center',
    height: 34,
    justifyContent: 'center',
    width: 34,
  },
  markOpen: {
    transform: [{ rotate: '45deg' }],
  },
})
